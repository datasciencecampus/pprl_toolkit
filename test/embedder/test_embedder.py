"""Unit tests for the embedder module."""

import unittest.mock as mock

import numpy as np
import pandas as pd
from hypothesis import HealthCheck, given, settings

from pprl import EmbeddedDataFrame, Embedder
from pprl.embedder import features as feat

from .strategies import st_matrix_and_indices, st_posdef_matrices


def alt_calculate_norm(scm_matrix, bf_indices):
    """Calculate the norm of a bloom filter wrt scm_matrix.

    An alternative method, used in testing.
    """
    bf_binary_vector = np.zeros(len(scm_matrix))
    bf_binary_vector[bf_indices] = 1.0
    return np.sqrt(bf_binary_vector.T @ scm_matrix @ bf_binary_vector)


@given(st_matrix_and_indices())
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_calculate_norm(matrix_and_indices):
    """Test EmbeddedDataFrame._calculate_norm.

    Tests the following properties: scalar, finite, non-negative
    equal to sqrt(x.T @ scm_matrix @ x)
    """
    scm_matrix, bf_indices = matrix_and_indices

    # Mock EmbeddedDataFrame
    self_mock = mock.Mock()
    self_mock.embedder.scm_matrix = scm_matrix

    result = EmbeddedDataFrame._calculate_norm(self_mock, bf_indices)

    expected = alt_calculate_norm(scm_matrix, bf_indices)

    assert np.isfinite(result)
    assert isinstance(result, float)
    assert result >= 0
    assert np.allclose(result, expected)


@given(st_posdef_matrices(bf_size=10))
def test_update_norms(posdef_matrix):
    """Test EmbeddedDataFrame.update_norms.

    Tests the following properties: Returns EmbeddedDataFrame, column names,
    idempotent
    """
    nrows = len(posdef_matrix)
    df = pd.DataFrame(
        dict(idx=[x for x in range(nrows)], bf_indices=[list(range(i)) for i in range(nrows)])
    )
    embedder_mock = mock.Mock(Embedder)
    embedder_mock.scm_matrix = posdef_matrix
    embedder_mock.checksum = "1234"
    edf = EmbeddedDataFrame(df, embedder_mock, update_norms=False)
    columns0 = list(edf.columns)
    _ = edf.update_norms()
    columns1 = list(edf.columns)
    bf_norms1 = list(edf["bf_norms"])
    edf.update_norms()
    columns2 = list(edf.columns)
    bf_norms2 = list(edf["bf_norms"])

    assert isinstance(_, EmbeddedDataFrame)
    assert set(columns1).difference(columns0) == {"bf_norms"}
    assert columns1 == columns2
    assert bf_norms1 == bf_norms2


def test_embed_colspec():
    """Check that only the name column in the colspec is processed."""

    df = pd.DataFrame(
        dict(
            column1=["datum_1"],
            column2=["datum_2"],
        )
    )

    embedder = Embedder(
        feature_factory={
            "name": feat.gen_name_features,
            "dob": feat.gen_dateofbirth_features,
            "sex": feat.gen_sex_features,
        },
        ff_args={"name": {}},
        num_hashes=2,
    )

    colspec = dict(column2="name")
    embed_df = embedder.embed(df, colspec)
    assert set(embed_df.columns) == set(
        ["column1", "column2", "column2_features", "all_features", "bf_indices", "bf_norms"]
    )


def test_embed_name_sex_features():
    """Check the name and sex features are processed correctly."""

    df = pd.DataFrame(
        dict(
            column1=["doris smith"],
            column2=["F"],
        )
    )

    ground_truth_df = pd.DataFrame(
        dict(
            column1_features=[
                ["_d", "do", "or", "ri", "is", "s_", "_s", "sm", "mi", "it", "th", "h_"]
            ],
            column2_features=[["sex<f>"]],
        )
    )

    colspec = dict(column1="name", column2="sex")

    embedder = Embedder(
        feature_factory={
            "name": feat.gen_name_features,
            "sex": feat.gen_sex_features,
        },
        ff_args={"name": {"ngram_length": [2]}},
        num_hashes=2,
    )

    embed_df = embedder.embed(df, colspec)
    assert embed_df[["column1_features", "column2_features"]].equals(
        ground_truth_df[["column1_features", "column2_features"]]
    )


def test_embed_dob_features():
    """Check a birth date is separated out correctly."""

    df = pd.DataFrame(
        dict(
            column1=["01/3/2012"],
        )
    )

    ground_truth = set(["day<01>", "month<03>", "year<2012>"])

    colspec = dict(column1="dob")

    embedder = Embedder(
        feature_factory={
            "dob": feat.gen_dateofbirth_features,
        },
        ff_args={"dob": {}},
        num_hashes=2,
    )

    embed_df = embedder.embed(df, colspec)
    assert ground_truth == set(embed_df["column1_features"][0])


def test_embed_all_features():
    """Check the all_features columns is created correctly."""

    df = pd.DataFrame(
        dict(
            column1=["doris smith"],
            column2=["jxr"],
        )
    )

    ground_truth = set(
        ["_d", "do", "or", "ri", "is", "s_", "_s", "sm", "mi", "it", "th", "h_", "sex<j>"]
    )

    colspec = dict(column1="name", column2="sex")

    embedder = Embedder(
        feature_factory={
            "name": feat.gen_name_features,
            "sex": feat.gen_sex_features,
        },
        ff_args={"name": {"ngram_length": [2]}, "sex": {}},
        num_hashes=2,
    )

    embed_df = embedder.embed(df, colspec)
    assert ground_truth == set(embed_df["all_features"][0])


def test_SimilarityArray_match():
    """Test for expected output with small dataset and no iteration."""
    df1 = pd.DataFrame(dict(name=["Bob", "Sally", "Samina", "John"]))
    df1.index = df1.name
    df2 = pd.DataFrame(dict(name=["Saly", "Rob", "Jon", "Ade"]))
    df2.index = df2.name
    colspec = dict(name="name")

    embedder = Embedder(
        feature_factory=dict(name=feat.gen_name_features),
        ff_args=dict(name=dict(ngram_length=[2])),
        bf_size=1024,
        num_hashes=1,
    )
    em1 = embedder.embed(df1, colspec, update_norms=True, update_thresholds=True)
    em2 = embedder.embed(df2, colspec, update_norms=True, update_thresholds=True)
    comp = embedder.compare(em1, em2)

    matching = comp.match(abs_cutoff=0.2, hungarian=True)

    ground_truth = (
        np.array([0, 1, 3], dtype=np.int64),
        np.array([1, 0, 2], dtype=np.int64),
    )

    np.testing.assert_equal(matching, ground_truth)
