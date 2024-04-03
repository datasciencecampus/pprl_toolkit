"""Classes and functions for handling embedding objects."""

import hashlib
import itertools as it
from typing import Iterable

import dill
import numpy as np
import numpy.ma as ma
import pandas as pd
from scipy.optimize import linear_sum_assignment

from pprl.embedder.bloom_filters import BloomFilterEncoder


class EmbeddedDataFrame(pd.DataFrame):
    """A data frame with a reference to an `Embedder` object.

    An `EmbeddedDataFrame` (EDF) instance wraps together a
    `pandas.DataFrame` with a reference to a `pprl.embedder.Embedder`
    object. An EDF also has a mandatory `bf_indices` column, describing
    the Bloom filter indices used for linkage.

    The EDF instance can also calculate `bf_norms` and `thresholds`
    columns which are used in the `Embedder.compare()` method to
    compute `pprl.embedder.SimilarityArray` instances.

    Parameters
    ----------
    data: numpy.ndarray, Iterable, dict, or pandas.DataFrame
        Data to which to attach the embedder. Must include a
        `bf_indices` column with `list` data type.
    embedder: pprl.embedder.Embedder
        A compatible embedder object for the Bloom filter columns in
        `data`.
    update_norms: bool
        Whether to update the Bloom filter norms on creation. Defaults
        to `False`.
    update_thresholds: bool
        Whether to update the similarity thresholds on creation.
        Defaults to `True`.
    *args: Iterable
        Additional positional arguments to pass to `pandas.DataFrame`
        along with `data`.
    **kwargs: dict
        Additional keyword arguments to pass to `pandas.DataFrame` along
        with `data`.

    Attributes
    ----------
    embedder_checksum: str
        Hexadecimal string digest from `self.embedder`.

    Notes
    -----
    An EDF instance is usually created from an existing `Embedder`
    object by calling the `embedder.embed()` method. It can also be
    initialised using an embedder and a `pandas.DataFrame` that already
    has a `bf_indices` column via `EmbeddedDataFrame(df, embedder)`.

    If using the second method it is up to the user to ensure that the
    `Embedder` instance is compatible with the `bf_indices` column
    (as well as `bf_norms` and `thresholds`, if present) in the data
    frame. If in doubt, call `edf.update_norms()` and
    `edf.update_thresholds()` to refresh them.
    """

    def __init__(
        self,
        data: np.ndarray | Iterable | dict | pd.DataFrame,
        embedder: "Embedder",
        update_norms: bool = True,
        update_thresholds: bool = False,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(data, *args, **kwargs)
        self.embedder = embedder
        self.embedder_checksum = embedder.checksum

        # Check key columns exist
        assert isinstance(self.embedder, Embedder), "Valid Embedder must be provided"
        assert "bf_indices" in self.columns, "bf_indices column missing"

        # Initialise bf_norms
        if update_norms:
            self.update_norms()
        if update_thresholds:
            self.update_thresholds()

    def to_bloom_matrix(self) -> np.ndarray:
        """Convert Bloom filter indices into a binary matrix.

        The matrix has a row for each row in the EDF. The number of
        columns is equal to `self.embedder.bf_size + self.embedder.offset`.
        This representation is used in the `Embedder.compare()` method.

        Returns
        -------
        X: np.ndarray
            Binary array of size `(len(self), self.bf_size + 1)`.
        """
        assert self.embedder_checksum == self.embedder.checksum, "Checksum mismatch"

        bf_length = self.embedder.bf_size + self.embedder.offset
        N = len(self)
        X = np.zeros((N, bf_length))
        for i in range(N):
            X[i, self["bf_indices"].iloc[i]] = 1.0

        return X

    def update_thresholds(self) -> "EmbeddedDataFrame":
        """Generate matching thresholds for each row of the data.

        The threshold is the minimum similarity score that will be
        matched. It is found by getting the pairwise similarities
        between each row and the other rows in the same EDF, and taking
        the maximum of these.

        Attributes
        ----------
        data.thresholds: numpy.ndarray
            Column for maximum similarity of each row within the EDF.
        """
        assert self.embedder_checksum == self.embedder.checksum, "Checksum mismatch"

        similarities = self.embedder.compare(self, self, require_thresholds=False)
        np.fill_diagonal(similarities, -np.Inf)

        self["thresholds"] = np.max(similarities, 1)

        return self

    def _calculate_norm(self, bf_indices: list[int]) -> float:
        """Given a list of bf_indices, calculate the vector norm wrt scm_matrix."""
        return np.sqrt(np.sum(self.embedder.scm_matrix[np.ix_(bf_indices, bf_indices)]))

    def update_norms(self) -> "EmbeddedDataFrame":
        """Generate vector norms (wrt. `self.embedder`) for each row.

        The vector norm is used to scale the (Soft) Cosine similarity
        scores.

        Attributes
        ----------
        data.bf_norms: list
            Column of vector norms for each row in the EDF.
        """
        assert self.embedder_checksum == self.embedder.checksum, "Checksum mismatch"

        self["bf_norms"] = list(map(self._calculate_norm, self["bf_indices"]))

        return self


class SimilarityArray(np.ndarray):
    """Augmented NumPy array of similarity scores with extra attributes.

    Parameters
    ----------
    input_array: numpy.ndarray, Iterable
        Original array of similarity score data.
    thresholds: tuple, optional
        2-tuple of similarity score thresholds for each axis. These
        thresholds can be used as an outside option when generating a
        matching.
    embedder_checksum: str, optional
        Hexadecimal string digest of a `pprl.embedder.Embedder` object.

    Notes
    -----
    `SimilarityArray` objects are usually initialised from an instance
    of `pprl.embedder.Embedder` via the `embedder.compare()` method.
    """

    def __new__(
        cls,
        input_array: Iterable | np.ndarray,
        thresholds: None | tuple = None,
        embedder_checksum: None | str = None,
    ) -> "SimilarityArray":
        """Create the array, adding on the thresholds and hex digest."""
        obj = np.asarray(input_array).view(cls)
        obj.thresholds = thresholds
        obj.embedder_checksum = embedder_checksum

        return obj

    def __array_finalize__(self, obj) -> None:
        if obj is not None:
            self.thresholds = getattr(obj, "thresholds", None)
            self.embedder_checksum = getattr(obj, "embedder_checksum", None)

    def match(
        self,
        abs_cutoff: int | float = 0,
        rel_cutoff: int | float = 0,
        hungarian: bool = True,
        require_thresholds: bool = True,
    ) -> tuple[list[int], list[int]]:
        """Compute a matching.

        Given an array of similarity scores, compute a matching of its
        elements, using the Hungarian algorithm by default. If the
        `SimilarityArray` has thresholds, masking is used to ensure they
        are respected. An `abs_cutoff` (global minimum similarity score)
        can also be supplied.

        Parameters
        ----------
        abs_cutoff : int or float, optional
            A lower cutoff for the similarity score. No pairs with
            similarity below the absolute cutoff will be matched. By
            default, this is 0.
        rel_cutoff : int or float, optional
            A margin above the row/column-specific threshold. Raises all
            thresholds by a constant. By default, this is 0.
        hungarian: bool, optional
            Whether to compute the unique matching using the Hungarian
            algorithm, filtered using `thresholds` and `abs_cutoff`.
            Default is `True`. If `False`, just return all pairs above
            the threshold.
        require_thresholds: bool, optional
            If `True` (default), the matching will fail if `thresholds`
            is not present and valid. Must be explicitly set to `False`
            to allow matching without similarity thresholds.

        Returns
        -------
        match: tuple[list[int], list[int]]
            2-tuple of indexes containing row and column indices of
            matched pairs eg. `([0, 1, ...], [0, 1, ...])`.

        Notes
        -----
        If `hungarian=False`, the matching returns all pairs with
        similarity score above the `abs_cutoff`, respecting `thresholds`
        if present. This method does not guarantee no duplicates.
        """
        S = ma.array(self.copy())

        if require_thresholds:
            if isinstance(self.thresholds, tuple):
                S[S < S.thresholds[0][:, None] + rel_cutoff] = ma.masked
                S[S < S.thresholds[1] + rel_cutoff] = ma.masked
            else:
                raise ValueError("Thresholds are required for matching")

        S[S < abs_cutoff] = ma.masked

        match = ma.where(S >= abs_cutoff)  # ma.where(S) would also work

        if hungarian:
            # Compute linear assignment (Hungarian match)
            hungarian_match = linear_sum_assignment(S, maximize=True)
            hungarian_mask = ~S.mask[hungarian_match]
            match = tuple([x[hungarian_mask] for x in hungarian_match])

        return match


class Embedder:
    """Class for embedding a dataset.

    Each instance of the `Embedder` class represents an embedding space
    on personal data features. An `Embedder` instance is defined by
    three things:

    1. A set of Bloom filter parameters
    2. A set of feature factory functions
    3. An embedding matrix that corresponds to the above

    Parameters
    ----------
    feature_factory: dict[str, func]
        Mapping from dataset columns to feature generation functions.
    ff_args: dict[dict], optional
        Mapping from dataset columns to keyword arguments for their
        respective feature generation functions.
    bf_size: int
        Size of the Bloom filter. Default is 1024.
    num_hashes: int
        Number of hashes to perform. Default is two.
    offset: int
        Offset for Bloom filter to enable masking. Default is zero.
    salt: str, optional
        Cryptographic salt added to tokens from the data before hashing.

    Attributes
    ----------
    scm_matrix: np.ndarray
        Soft Cosine Measure matrix. Initialised as an identity matrix of
        size `bf_size + offset`.
    freq_matr_matched: np.ndarray
        Matched frequency matrix for computing `scm_matrix`. Initialised
        as an identity matrix of size `bf_size + offset`.
    freq_matr_unmatched: np.ndarray
        Unmatched frequency matrix for computing `scm_matrix`.
        Initialised as an identity matrix of size `bf_size + offset`.
    checksum: str
        Hexadecimal string digest of the feature factory, SCM matrix,
        and other embedding parameters. Used to check an embedder is
        compatible with an `EmbeddedDataFrame`.

    Notes
    -----
    When an instance is initialised in code, the embedding matrix is
    initialised as an identity matrix; the matrix can then be trained
    using a pair of datasets with known match status and the trained
    `Embedder` instance pickled to file. The pre-trained `Embedder`
    instance can then be reinitialised from the pickle file.

    Both the untrained and trained instances provide `embed()` and
    `compare()` methods. Comparing datasets using an untrained
    `Embedder` instance is equivalent to calculating Cosine similarities
    on ordinary Bloom filters. Comparing datasets using a pre-trained
    `Embedder` calculates the Soft Cosine Measure between Bloom filters.
    The Soft Cosine Measure embedding matrix is trained using an
    experimental method.
    """

    def __init__(
        self,
        feature_factory: dict,
        ff_args: dict[str, dict] | None = None,
        bf_size: int = 1024,
        num_hashes: int = 2,
        offset: int = 0,
        salt: str | None = None,
    ) -> None:
        # Get embedding from model
        # Get other attributes from model
        self.feature_factory = feature_factory
        if ff_args is not None:
            self.ff_args = ff_args
        else:
            self.ff_args = {}
        self.num_hashes = num_hashes
        self.bf_size = bf_size
        self.offset = offset
        self.salt = salt or ""

        # Initialise Soft Cosine Measure matrices
        # These are large-ish (for bf_size=1024, each will take up 4MB)
        self.scm_matrix = self._initmatrix()
        self.freq_matr_matched = self._initmatrix()
        self.freq_matr_unmatched = self._initmatrix()

        self.checksum = self._compute_checksum()

    def _initmatrix(self) -> np.ndarray:
        return np.eye((self.bf_size + self.offset), dtype=np.float32)

    def _compute_checksum(self) -> str:
        res = hashlib.md5()

        # bytes from feature_factory
        for k, v in self.feature_factory.items():
            res.update(k.encode("utf-8"))
            res.update(dill.dumps(v))

        # bytes from SCM matrix
        res.update(str(self.scm_matrix).encode("utf-8"))

        # bytes from params
        params_bytes = str([self.bf_size, self.num_hashes, self.offset]).encode("utf-8")
        res.update(params_bytes)

        return res.hexdigest()

    def embed(
        self,
        df: pd.DataFrame,
        colspec: dict,
        update_norms: bool = True,
        update_thresholds: bool = False,
    ) -> EmbeddedDataFrame:
        """Encode data columns into features from Bloom embedding.

        Parameters
        ----------
        df : pd.DataFrame
            Data frame to be embedded.
        colspec : dict
            Dictionary mapping columns in `df` to feature factory
            functions.
        update_norms : bool, optional
            Whether to calculate vector norms for SCM and add to EDF.
            `False` by default.
        update_thresholds : bool, optional
            Whether to calculate similarity thresholds and add to EDF.
            Used as an outside option in matching. `False` by default.

        Returns
        -------
        EmbeddedDataFrame
            An embedded data frame with its embedder.
        """
        df_features = df[colspec.keys()].copy()

        # create features from each column
        for column in colspec:
            column_type = colspec[column]

            feature_factory_kw = self.feature_factory[column_type]
            if column_type in self.ff_args:
                df_features[column] = feature_factory_kw(
                    df_features[column], **self.ff_args[column_type]
                )
            else:
                df_features[column] = feature_factory_kw(df_features[column])

        # concat the features to a single column
        df_features.columns = [i + "_features" for i in df_features.columns]
        df_features["all_features"] = df_features.values.tolist()
        df_features["all_features"] = df_features["all_features"].apply(
            lambda x: list(set(it.chain.from_iterable(x)))
        )
        df = pd.concat([df, df_features], axis=1)

        # create bloom filter indices
        bfencoder = BloomFilterEncoder(self.bf_size, self.num_hashes, self.offset, self.salt)

        df["bf_indices"] = df_features["all_features"].apply(
            lambda x: bfencoder.bloom_filter_vector(x)
        )

        return EmbeddedDataFrame(
            df, embedder=self, update_norms=update_norms, update_thresholds=update_thresholds
        )

    def compare(
        self,
        edf1: EmbeddedDataFrame,
        edf2: EmbeddedDataFrame,
        require_thresholds: bool = True,
    ) -> SimilarityArray:
        """Calculate a `SimilarityArray` on two EDFs.

        Given two EDFs, calculate all pairwise Soft Cosine Similarities
        between rows.

        Parameters
        ----------
        edf1 : EmbeddedDataFrame
            An EDF instance with N rows. Must have `thresholds` column
            unless `require_thresholds=False`.
        edf2 : EmbeddedDataFrame
            An EDF instance with M rows. Must have `thresholds` column
            unless `require_thresholds=False`.
        require_thresholds: bool, optional
            If `True` (default), the comparison will fail if thresholds
            are not present. Must be explicitly set to `False` to allow
            comparison without thresholds.

        Returns
        -------
        SimilarityArray
            An N by M array containing the similarity matrix of pairwise
            Soft Cosine similarities between rows of `edf1` and `edf2`.

        Raises
        ------
        ValueError
            If `require_thresholds` is `True` and both EDFs don't have a
            `thresholds` column.
        """
        assert (
            edf1.embedder_checksum == self.checksum and edf2.embedder_checksum == self.checksum
        ), "Both EmbeddedDFs must refer to the same Embedder instance"

        if "bf_norms" not in edf1.columns:
            edf1.update_norms()
        if "bf_norms" not in edf2.columns:
            edf2.update_norms()

        X1 = edf1.to_bloom_matrix()
        X2 = edf2.to_bloom_matrix()
        A = edf1.embedder.scm_matrix
        diag_norm1 = np.diag(1 / np.array(edf1.bf_norms))
        diag_norm2 = np.diag(1 / np.array(edf2.bf_norms))

        res = diag_norm1 @ X1 @ A @ X2.T @ diag_norm2

        if "thresholds" in edf1.columns and "thresholds" in edf2.columns:
            thresholds = (edf1["thresholds"].to_numpy(), edf2["thresholds"].to_numpy())
        elif require_thresholds:
            raise ValueError("Thresholds required for comparison")
        else:
            thresholds = None

        return SimilarityArray(res, thresholds=thresholds, embedder_checksum=self.checksum)

    def _joint_freq_matrix(
        self,
        x: list[list] | pd.Series,
        y: list[list] | pd.Series,
        prob: bool = False,
    ) -> np.ndarray:
        assert len(x) == len(y), "x and y lengths must match"
        N = len(x)
        bfsize = self.bf_size + self.offset

        coordinates = ([], [])
        # Loop through the cross-product of every index in x[n] and every index in y[n]
        # for n in 1:len(x)
        for i, j in it.chain.from_iterable(map(it.product, x, y)):
            coordinates[0].append(i)
            coordinates[1].append(j)

        S = np.zeros((bfsize, bfsize), np.float32)
        np.add.at(S, coordinates, 1.0)

        # Make it symmetric
        S = (S + S.T) / 2
        if prob:
            S = S / N

        return S

    def train(
        self,
        edf1: EmbeddedDataFrame,
        edf2: EmbeddedDataFrame,
        update: bool = True,
        learning_rate: float = 1.0,
        eps: float = 0.01,
        random_state: None | np.random.RandomState = None,
    ) -> None:
        """Fit Soft Cosine Measure matrix to two matched datasets.

        This function updates the `scm_matrix` attribute in-place along
        with its constituent matrices, `freq_matr_matched` and
        `freq_matr_unmatched`.

        Provide two datasets of pre-matched data. If `update=True`, the
        training is cumulative, so that `train()` can be called more
        than once, updating the same matrices each time by adding new
        frequency tables. Otherwise, all three matrices are
        reinitialised prior to training.

        Parameters
        ----------
        edf1: EmbeddedDataFrame
            An embedded dataset.
        edf2: EmbeddedDataFrame
            An Embedded dataset of known matches in the same order as
            `edf1`.
        update: bool
            Whether to update the existing SCM matrix, or overwrite it.
            Defaults to `True`.
        eps: float
            Small non-negative constant to avoid `-Inf` in log of
            frequencies. Default is one.
        learning_rate: float
            Scaling factor to dampen matrix updates. Must be in the
            interval `(0, 1]`. Default is 0.01.
        random_state: RandomState, optional
            Random state to pass to dataset jumbler. Defaults to `None`.

        Attributes
        ----------
        scm_matrix: np.ndarray
            Soft Cosine Measure matrix that is fitted cumulatively or
            afresh.
        """
        # Check the dimensions are the same
        x = edf1.bf_indices
        y = edf2.bf_indices
        assert len(x) == len(
            y
        ), "Must have same length (this will be relaxed in future iterations)"
        assert eps >= 0.0, "Negative eps not allowed"
        assert learning_rate > 0.0 and learning_rate <= 1.0

        y_jumbled = pd.Series(y).sample(frac=1, random_state=random_state).to_list()

        # Calculate joint probability matrix for matches
        freq_matr_matched = self._joint_freq_matrix(x, y)

        # Calculate joint probability matrix for random non-matches
        freq_matr_unmatched = self._joint_freq_matrix(x, y_jumbled)

        if update:
            self.freq_matr_matched += learning_rate * freq_matr_matched
            self.freq_matr_unmatched += learning_rate * freq_matr_unmatched
        else:
            self.freq_matr_matched = self._initmatrix() + learning_rate * freq_matr_matched
            self.freq_matr_unmatched = self._initmatrix() + learning_rate * freq_matr_unmatched

        # Log the ratio
        scm_matrix = np.log(self.freq_matr_matched + eps) - np.log(self.freq_matr_unmatched + eps)

        # Ensure matrix is positive definite for positive norm
        # This also ensures that the diagonal is non-negative
        scm_matrix = nearest_pos_semi_definite(scm_matrix, eps=1e-6)
        self.scm_matrix = scm_matrix
        self._compute_checksum()

    def to_pickle(self, path: None | str = None) -> None | bytes:
        """Save Embedder instance to pickle file.

        Parameters
        ----------
        path : str, optional
            File path at which to save the pickled embedder. If not
            specified, the pickled bytes string is returned.

        Returns
        -------
        pickled : bytes or None
            If `path` is not specified, the pickled string comes back.
            Otherwise, nothing is returned.
        """

        if path is None:
            return dill.dumps(self)

        with open(path, "wb") as f:
            dill.dump(self, f)

    @classmethod
    def from_pickle(
        cls, path: None | str = None, pickled: None | str | bytes = None
    ) -> "Embedder":
        """Initialise Embedder instance from pickle file.

        Parameters
        ----------
        path : str, optional
            File path from which to load the pickled embedder.
        pickled : bytes, optional
            Byte-string containing the pickled embedder.

        Raises
        ------
        ValueError
            If not exactly one of `path` and `pickled` are specified.

        Returns
        -------
        embedder : Embedder
            The reformed instance of the `Embedder` class.
        """

        neither = path is None and pickled is None
        both = path is not None and pickled is not None
        if neither or both:
            raise ValueError("Exactly one of `path` and `pickled` must be specified.")

        if isinstance(path, str):
            with open(path, "rb") as f:
                embedder = dill.load(f)

        if isinstance(pickled, (str, bytes)):
            embedder = dill.loads(pickled)

        assert (
            embedder.checksum == embedder._compute_checksum()
        ), "Checksum on loaded Embedder instance doesn't match saved checksum."

        return embedder


def nearest_pos_semi_definite(X: np.ndarray, eps: float = 0.0) -> np.ndarray:
    """Calculate nearest positive semi-definite version of a matrix.

    This function achieves this by setting all negative eigenvalues of
    the matrix to zero, or a small positive value to give a positive
    definite matrix.

    Graciously taken from this StackOverflow
    [post](https://stackoverflow.com/questions/43238173/python-convert-matrix-to-positive-semi-definite)

    Parameters
    ----------
    X: np.ndarray
        Matrix-like array.
    eps: float
        Use a small positive constant to give a positive definite
        matrix. Default is 0 to give a positive semi-definite matrix.

    Returns
    -------
    np.ndarray
        A positive (semi-)definite matrix.
    """
    C = (X + X.T) / 2
    eigval, eigvec = np.linalg.eig(C)
    eigval[eigval < 0] = eps

    return np.real(eigvec.dot(np.diag(eigval)).dot(eigvec.T))
