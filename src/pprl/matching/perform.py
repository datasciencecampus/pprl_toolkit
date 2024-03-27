"""Functions for performing the matching itself."""

import logging
import secrets

import numpy as np
import pandas as pd

from pprl.embedder.embedder import EmbeddedDataFrame, Embedder


def add_private_index(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    match: tuple[np.ndarray, np.ndarray],
    size_assumed: int = 10_000,
    colname: str = "private_index",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add anonymous match index to input datasets.

    The match index assigns indices to both matched and unmatched
    records, so that they are indistinguishable. It doesn't leak
    any info about the other dataset.

    add_private_index only works with unique one-to-one matches. This is
    because there is no way to match many-to-one without leaking information
    about the successful matches.

    Parameters
    ----------
    df1 : pd.DataFrame
        A dataset.
    df2 : pd.DataFrame
        Another dataset.
    match : tuple[np.ndarray, np.ndarray]
        A pair of matched indices, with no repeated indices.
    size_assumed : int
        The assumed maximum size of each dataset. Default is 10,000.
    colname: str
        A column name for the new index. By default `"private_index"`.

    Returns
    -------
    df1, df2: pd.DataFrame
        The same as input data, with private matching index added.
    """
    assert (
        colname not in df1.columns and colname not in df2.columns
    ), "The chosen colname for the private index is already in use."

    assert len(match[0]) == len(np.unique(match[0])) and len(match[1]) == len(
        np.unique(match[1])
    ), "add_private_index can't handle repeated match indices (many-to-one matches)"
    # Generate a private matching index
    inner_join_size = len(match[0])
    outer_join_size = len(df1) + len(df2) - inner_join_size
    rng = np.random.default_rng(secrets.randbits(128))
    # Sampling from a fixed range to avoid information leakage
    private_index = rng.permutation(range(size_assumed, 3 * size_assumed))[:outer_join_size]

    # Assign the private_index to both datasets
    # Initialise as zero
    out1 = df1.copy()
    out2 = df2.copy()
    out1[colname] = 0
    out2[colname] = 0

    # Assign the inner join first
    out1.iloc[list(match[0]), out1.columns.get_loc(colname)] = private_index[:inner_join_size]
    out2.iloc[list(match[1]), out2.columns.get_loc(colname)] = private_index[:inner_join_size]

    # Then assign the left and right remainders
    data1_size = len(out1)
    out1.iloc[out1[colname] == 0, out1.columns.get_loc(colname)] = private_index[
        inner_join_size:data1_size
    ]
    out2.iloc[out2[colname] == 0, out2.columns.get_loc(colname)] = private_index[
        data1_size:outer_join_size
    ]

    return out1, out2


def calculate_performance(
    data_1: pd.DataFrame, data_2: pd.DataFrame, match: tuple[list, list]
) -> None:
    """
    Calculate the performance of the match by counting the positives.

    Performance metrics are sent to the logger.

    Parameters
    ----------
    data_1 : pandas.DataFrame
        Data frame for `PARTY1`.
    data_2 : pandas.DataFrame
        Data frame for `PARTY2`.
    match : tuple
        Tuple of indices of matched pairs between the data frames.
    """

    data_1_sorted = data_1.iloc[list(match[0]), :]
    data_2_sorted = data_2.iloc[list(match[1]), :]
    tps = sum(map(np.equal, data_1_sorted["true_id"], data_2_sorted["true_id"]))
    fps = len(match[0]) - tps

    logging.info(f"True positives {tps}; false positives {fps}")


def perform_matching(
    data_1: pd.DataFrame, data_2: pd.DataFrame, embedder: Embedder
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Initiate the data, get similarities, and match the rows.

    Parameters
    ----------
    data_1 : pandas.DataFrame
        Data frame for `PARTY1`.
    data_2 : pandas.DataFrame
        Data frame for `PARTY2`.
    embedder : Embedder
        Instance used to embed both data frames.

    Returns
    -------
    output_1 : pandas.DataFrame
        Output for `PARTY1`.
    output_2 : pandas.DataFrame
        Output for `PARTY2`.
    """

    logging.info("Initialising data with norms and thresholds...")
    edf_1 = EmbeddedDataFrame(data_1, embedder, update_norms=True, update_thresholds=True)
    edf_2 = EmbeddedDataFrame(data_2, embedder, update_norms=True, update_thresholds=True)

    logging.info("Calculating similarities...")
    similarities = embedder.compare(edf_1, edf_2)
    match = similarities.match()

    logging.info("Matching completed!")

    # size_assumed must be > data size
    output_1, output_2 = add_private_index(data_1, data_2, match, size_assumed=10_000)

    # If the true index is provided, print performance
    if "true_id" in data_1.columns and "true_id" in data_2.columns:
        calculate_performance(data_1, data_2, match)

    return output_1, output_2
