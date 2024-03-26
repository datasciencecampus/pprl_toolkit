"""Unit tests for the server utilities module."""

import pandas as pd
import pytest

from pprl.utils.server_utils import add_private_index


# Adding row index to check for bug to do with use of .loc instead of .iloc
@pytest.mark.parametrize(
    "df1,df2,match,colname,expected",
    [
        (
            pd.DataFrame(dict(x=list("abcd")), index=["ann", "oying", "ind", "ex"]),
            pd.DataFrame(dict(y=list("abcd")), index=["an", "oth", "ero", "ne"]),
            ([0, 2], [0, 2]),
            "private_index",
            ["aa", "cc"],
        ),
    ],
)
def test_add_private_index(df1, df2, match, colname, expected):
    """Test adding a private index works with move to `.iloc`."""
    out1, out2 = add_private_index(df1=df1, df2=df2, match=match, colname=colname)
    result = out1.merge(out2, on=colname).loc[:, ["x", "y"]].agg("".join, axis=1).to_list()

    assert result == expected


@pytest.mark.parametrize(
    "df1,df2,match",
    [
        (
            pd.DataFrame(dict(x=list("abcd")), index=["ann", "oying", "ind", "ex"]),
            pd.DataFrame(dict(y=list("abcd")), index=["an", "oth", "ero", "ne"]),
            ([0, 2], [0, 2]),
        ),
    ],
)
def test_add_private_index_complete(df1, df2, match):
    """Check that the private indexes are all integers (no missing)."""
    out1, out2 = add_private_index(df1=df1, df2=df2, match=match)

    assert all(isinstance(i, int) for i in out1.private_index)
    assert all(isinstance(i, int) for i in out2.private_index)
