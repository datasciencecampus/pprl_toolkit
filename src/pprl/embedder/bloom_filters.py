"""Module for the Bloom filter encoder."""

import hashlib


class BloomFilterEncoder:
    """Encoder of tokens and features via hashing and a Bloom filter.

    The process for creating a cryptographically secure Bloom filter
    encoding of a set of tokens is as follows:

    1. Compute the hash digest for your tokens
    2. Convert the digest bytes into integers
    3. Map the integer to a bloom filter vector (modulo `b`, where `b`
       represents the length of the vector)

    Parameters
    ----------
    size: int
        Size of the Bloom filter.
    num_hashes: int
        Number of hashes to perform. Defaults to three.
    offset: int
        Offset for Bloom filter indices to allow for masking. Defaults
        to one.
    salt: str, optional
        Cryptographic salt appended to tokens prior to hashing.

    Attributes
    ----------
    hash_function: func
        Hashing function (`hashlib.sha1`).
    """

    def __init__(
        self, size: int, num_hashes: int = 3, offset: int = 1, salt: str | None = None
    ) -> None:
        self.size = size - 1
        self.num_hashes = num_hashes
        self.offset = offset
        self.salt = salt or ""

        self.hash_function = hashlib.sha1

    def bloom_filter_vector_collision_fraction(self, feature: list) -> tuple[list, float]:
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
        """
        feature_int_repr = self.feature_to_big_int_repr(feature)
        vec_idx = self.big_int_to_vec(feature_int_repr, offset=self.offset)
        vec_idx_deduped = [*set(vec_idx)]
        collision_fraction = 1 - len(vec_idx_deduped) / len(vec_idx)

        return vec_idx_deduped, collision_fraction

    def bloom_filter_vector(self, feature: list) -> list[int]:
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
        """
        feature_int_repr = self.feature_to_big_int_repr(feature)
        vec_idx = self.big_int_to_vec(feature_int_repr, offset=self.offset)
        vec_idx_deduped = [*set(vec_idx)]

        return vec_idx_deduped

    def big_int_to_vec(self, feature_ints: list, offset: int = 1) -> list[int]:
        """Convert an integer vector into indices for a Bloom vector.

        This conversion inserts 1 at the location derived from the
        integer vector, which is an integer representation of a
        deterministic hash value, modulo to the size of the Bloom
        filter.

        Parameters
        ----------
        feature_ints: list
            List of integer values representing the feature.
        offset: int
            An offset to indices to allow for masking. Defaults to one.

        Returns
        -------
        vector_idxs: list
            List of integers representing an index on the Bloom filter.
        """
        return list(map(lambda x: x % self.size + offset, feature_ints))

    def feature_to_big_int_repr(self, feature: list) -> list[int]:
        """Convert a feature vector into an integer vector.

        This conversion first generates a hash digest for each member of
        the feature vector and then converts them to an integer.

        Parameters
        ----------
        feature: list
            List of features to be processed.

        Returns
        -------
        feature_ints: list
            List of features as integers.
        """
        feature_int_repr: list = []
        # hash function will create a 256-bit integer
        # under the random oracle model this integer will be deterministic
        # depending on the token passed to
        # the hash function

        for gram in feature:
            for i in range(self.num_hashes):
                utf_string_with_salt = (str(gram) + str(i) + str(self.salt)).encode("UTF-8")
                digest = self.hash_function(utf_string_with_salt).digest()
                # integer value uses little endianness for amd64 architecture
                int_repr = int.from_bytes(digest, "little")
                feature_int_repr.append(int_repr)

        return feature_int_repr
