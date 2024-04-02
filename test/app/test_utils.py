"""Unit tests for the Flask app utility functions."""

import pandas as pd
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


def test_convert_dataframe_to_bf():
    """Test convert_dataframe_to_bf.

    Tests the following properties: Returns Pandas DataFrame, dataframe length,
    column names.
    """

    dataframe_values = dict(
        id_column=["1", "2", 3],
        name_column=["name1", "name2", "name3"],
        dob_column=["01/08/1996", "Mar 2000", 2005],
        sex_column=["M", "F", "Other"],
        house_number=[6, 1, 7],
        postcode=["P12 7UP", "LW12, 6PL", "H12 9I6"],
        other_column=[1, 8, 9],
    )
    input_dataframe = pd.DataFrame(dataframe_values)

    colspec = dict(
        name_column="name",
        dob_column="dob",
        sex_column="sex",
        house_number="misc_features",
        postcode="misc_shingled_features",
    )

    other_columns = ["id_column"]

    output_dataframe = utils.convert_dataframe_to_bf(
        input_dataframe, colspec, other_columns, salt="my_salt"
    )

    assert isinstance(output_dataframe, pd.DataFrame)
    assert len(output_dataframe) == 3
    assert set(output_dataframe.columns) == set(
        ["id_column", "bf_indices", "bf_norms", "thresholds"]
    )


def test_convert_dataframe_to_bf_other_columns_none():
    """Test convert_dataframe_to_bf.

    Tests when the other_columns keyword arguement is set to None.
    """

    dataframe_values = dict(
        id_column=["1", "2", 3],
        name_column=["name1", "name2", "name3"],
    )
    input_dataframe = pd.DataFrame(dataframe_values)

    colspec = dict(
        name_column="name",
    )

    output_dataframe = utils.convert_dataframe_to_bf(input_dataframe, colspec, salt="my_salt")

    assert isinstance(output_dataframe, pd.DataFrame)
    assert len(output_dataframe) == 3
    assert set(output_dataframe.columns) == set(["bf_indices", "bf_norms", "thresholds"])
