"""Utility functions for the party-side app."""

import os
import zipfile
from io import BytesIO

import dill
import flask
import pandas as pd

from pprl.embedder import features
from pprl.embedder.embedder import EmbeddedDataFrame, Embedder


def check_is_csv(path: str) -> bool:
    """
    Determine whether a file has the `csv` extension.

    Parameters
    ----------
    path : str
        Path to the file.

    Returns
    -------
    is_csv : bool
        Whether the file name follows the pattern `{name}.csv` or not.
    """

    *parts, extension = os.path.basename(path).split(os.path.extsep)

    return bool(parts) and any(part for part in parts) and extension.lower() == "csv"


def assign_columns(form: dict, feature_funcs: dict) -> tuple[list, list, dict]:
    """
    Assign columns from a form to collections.

    All columns belong to one of three collections: columns to drop,
    raw columns to keep, or a column feature factory specification.

    Parameters
    ----------
    form : dict
        Form from our column chooser page.
    feature_funcs : dict
        Mapping between column types and feature functions.

    Returns
    -------
    drop : list[str]
        List of columns to drop.
    keep : list[str]
        List of columns to keep in their raw format.
    spec : dict[str, func]
        Mapping between column names and feature functions.
    """

    drop, keep, spec = [], [], {}
    for column, value in form.items():
        if value == "drop":
            drop.append(column)
        elif value == "keep":
            keep.append(column)
        elif column in ("salt", "upload", "download"):
            continue
        else:
            spec[column] = feature_funcs[value]

    return drop, keep, spec


def download_files(
    dataframe: EmbeddedDataFrame, embedder: Embedder, party: str, archive: str = "archive"
) -> flask.Response:
    """
    Serialize, compress, and send a data frame with its embedder.

    Parameters
    ----------
    dataframe : EmbeddedDataFrame
        Data frame to be downloaded.
    embedder : Embedder
        Embedder used to embed `dataframe`.
    party : str
        Name of the party.
    archive : str
        Name of the archive. Default is `"archive"`.

    Returns
    -------
    response : flask.Response
        Response containing a ZIP archive with the data frame and
        its embedder.
    """

    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        with z.open("data.csv", "w") as f:
            dataframe.to_csv(f, index=False)
        with z.open("embedder.pkl", "w") as f:
            dill.dump(embedder, f)

    stream.seek(0)
    name = ".".join((party, archive, "zip"))

    return flask.send_file(stream, as_attachment=True, download_name=name)


def convert_dataframe_to_bf(
    df: pd.DataFrame, colspec: dict, other_columns: None | list = None, salt: str = ""
) -> pd.DataFrame:
    """Convert a dataframe of features to a bloom filter.

    Convert the columns to features based on the colspec. The features
    are then combined and converted to Bloom filter indices with the
    Bloom filter norm also calculated.

    Parameters
    ----------
    df: pandas.DataFrame
        Data frame of features.
    colspec: dict[str, str]
        Dictionary designating columns in the data frame as particular
        feature types to be processed as appropriate.
    other_columns: list[str]
        Columns to be returned as they appear in the data in addition to
        `bf_indices` and `bf_norms`.
    salt: str
        Cryptographic salt to add to tokens before hashing.

    Returns
    -------
    output: pandas.DataFrame
        Data frame of bloom-filtered data.
    """
    if other_columns is None:
        other_columns = []

    output_columns = other_columns + ["bf_indices", "bf_norms", "thresholds"]
    NUMHASHES = 2
    OFFSET = 1
    NGRAMS = [1, 2, 3, 4]
    FFARGS = {"name": {"ngram_length": NGRAMS, "use_gen_skip_grams": True}}
    BFSIZE = 2**10

    column_types_dict = {
        "name": features.gen_name_features,
        "dob": features.gen_dateofbirth_features,
        "sex": features.gen_sex_features,
        "misc_features": features.gen_misc_features,
        "misc_shingled_features": features.gen_misc_shingled_features,
    }

    embedder = Embedder(
        feature_factory=column_types_dict,
        ff_args=FFARGS,
        bf_size=BFSIZE,
        num_hashes=NUMHASHES,
        offset=OFFSET,
        salt=salt,
    )

    df_bloom_filter = embedder.embed(df, colspec, update_norms=True, update_thresholds=True)
    output = df_bloom_filter[output_columns]

    return output
