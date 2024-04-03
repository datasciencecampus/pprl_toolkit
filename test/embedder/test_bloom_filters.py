"""Unit tests for the bloom_filters module."""

from hypothesis import given
from hypothesis import strategies as st

from pprl.embedder.bloom_filters import BloomFilterEncoder


@given(
    st.lists(st.integers() | st.floats() | st.text(min_size=1), min_size=1, max_size=40),
    st.integers(min_value=2, max_value=100),
    st.integers(min_value=1, max_value=5),
    st.integers(min_value=0, max_value=50),
    st.text(),
)
def test_bloom_filter_vector_collision_fraction(feature, size, num_hashes, offset, salt):
    """Test BloomFilterEncoder.bloom_filter_vector_collision_fraction.

    Tests the following properties for vec_idx_deduped: list[0 < int < size].
    Tests the following properties for collision_fraction: >= 0, <= 1.
    """
    bfencoder = BloomFilterEncoder(size=size, num_hashes=num_hashes, offset=offset, salt=salt)
    vec_idx_deduped, collision_fraction = bfencoder.bloom_filter_vector_collision_fraction(feature)

    assert all(isinstance(element, int) for element in vec_idx_deduped)
    assert all(element <= (size + offset - 1) for element in vec_idx_deduped)
    assert all(element >= offset for element in vec_idx_deduped)

    assert collision_fraction <= 1
    assert collision_fraction >= 0
