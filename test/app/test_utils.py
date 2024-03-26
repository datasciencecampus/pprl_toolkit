"""Unit tests for the Flask app utility functions."""

import pytest

from pprl.app import utils


@pytest.mark.parametrize(
    "input_filename, expected_output",
    [
        ("file1.csv", True),
        ("D:path/folder1/folder2/myfile.csv", True),
        ("file.CsV", True),
        ("file.txt", False),
        ("D:path/folder1/file.TxT", False),
        ("file1csv", False),
        ("other.py", False),
        (".csv", False),
    ],
)
def test_check_is_csv(input_filename, expected_output):
    """Check the CSV checker works as it should."""
    assert utils.check_is_csv(input_filename) is expected_output


@pytest.mark.parametrize(
    "form, expected_drop_columns, expected_other_columns, expected_colspec",
    [
        (
            {
                "salt": "my_salt",
                "upload": "Upload to GCP",
                "download": "Download file locally",
                "column4": "drop",
                "column5": "Name",
                "column6": "keep",
            },
            ["column4"],
            ["column6"],
            {"column5": "name"},
        ),
        ({}, [], [], {}),
    ],
)
def test_assign_columns(form, expected_drop_columns, expected_other_columns, expected_colspec):
    """Test to make sure the correct columns are assigned correctly."""

    feature_funcs = {
        "Name": "name",
        "Date": "dob",
        "Sex": "sex",
        "Miscellaneous": "misc_features",
        "Shingled": "misc_shingled_features",
    }

    drop_columns, other_columns, colspec = utils.assign_columns(form, feature_funcs)
    assert drop_columns == expected_drop_columns
    assert other_columns == expected_other_columns
    assert colspec == expected_colspec
