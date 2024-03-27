"""Functions for performing matching locally."""

import os

from pprl import config
from pprl.embedder.embedder import Embedder


def build_local_file_paths(party: str) -> tuple[str, str]:
    """
    Construct the paths for the input and output datasets for a party.

    Parameters
    ----------
    party : str
        Name of the party.

    Returns
    -------
    inpath : str
        Location of the party data.
    outpath : str
        Location to put the party results.
    """

    stem = config.DIR_DATA_INTERIM
    inpath = os.path.join(stem, f"{party}-data.json")
    outpath = os.path.join(stem, f"{party}-output.json")

    return inpath, outpath


def load_embedder() -> Embedder:
    """
    Load an embedder from a pickle in the local data directory.

    Returns
    -------
    embedder : Embedder
        Reformed embedder instance.
    """

    path = os.path.join(config.DIR_DATA_INTERIM, "embedder.pkl")
    embedder = Embedder.from_pickle(path=path)

    return embedder
