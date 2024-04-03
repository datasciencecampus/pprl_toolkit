"""Module for the Bloom filter encoder."""

import hashlib


class BloomFilterEncoder:
    """Encoder of tokens and features via hashing and a Bloom filter.

    The process for creating a cryptographically secure Bloom filter
    encoding of a set of tokens is as follows:

    1. Compute the hash digest for your tokens
    2. Convert the digest bytes into integers
    3. Map the integer to a bloom filter vector (modulo the length of the vector)

    Parameters
    ----------
    size: int
        Size of the Bloom filter. Defaults to 1024
    num_hashes: int
        Number of hashes to perform. Defaults to two.
    offset: int
        Offset for Bloom filter indices to allow for masking. Defaults
        to zero.
    salt: str, optional
        Cryptographic salt appended to tokens prior to hashing.

    Attributes
    ----------
    hash_function: func
        Hashing function (`hashlib.sha256`).
    """

    def __init__(
        self, size: int = 1024, num_hashes: int = 2, offset: int = 0, salt: str | None = None
    ) -> None:
        self.size = size
        self.num_hashes = num_hashes
        self.offset = offset
        self.salt = salt or ""

        self.hash_function = hashlib.sha256

    def bloom_filter_vector_collision_fraction(
        self, feature: list[str]
    ) -> tuple[list[int], float]:
        """Convert a feature vector and return its collision fraction.

        The index vector uses an optional offset for masking.

        Parameters
        ----------
        feature: list
            List of features to be processed.

        Returns
        -------
        vector_idxs: list
            Index values used to create the Bloom filter vector.
        collision_fraction: float
            Proportion of repeated indices.

        Examples
        --------
        >>> bfe = BloomFilterEncoder()
        >>> bfe.bloom_filter_vector_collision_fraction(["a","b","c"])
        ([334, 1013, 192, 381, 18, 720], 0.0)
        """
        vec_idx: list = []

        for gram in feature:
            for i in range(self.num_hashes):
                utf_string_with_salt = (str(gram) + str(i) + str(self.salt)).encode("UTF-8")
                digest = self.hash_function(utf_string_with_salt).digest()
                digest_as_int = (int.from_bytes(digest, "little") % self.size) + self.offset
                vec_idx.append(digest_as_int)

        vec_idx_deduped = [*set(vec_idx)]
        collision_fraction = 1 - len(vec_idx_deduped) / len(vec_idx)

        return vec_idx_deduped, collision_fraction

    def bloom_filter_vector(self, feature: list[str]) -> list[int]:
        """Convert a feature vector into indices for a Bloom vector.

        The index vector uses an optional offset for masking.

        Parameters
        ----------
        feature: list
            List of features to be converted.

        Returns
        -------
        vector_idxs: list
            Index values used to create the Bloom filter vector.

        Examples
        --------
        >>> bfe = BloomFilterEncoder()
        >>> bfe.bloom_filter_vector(["a","b","c"])
        [334, 1013, 192, 381, 18, 720]
        """
        vec_idx_deduped, _ = self.bloom_filter_vector_collision_fraction(feature)

        return vec_idx_deduped
