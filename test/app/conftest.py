"""Test configuration."""

import pandas as pd
import pytest

from pprl.app import app


@pytest.fixture()
def client():
    """Create a test client."""
    return app.test_client()


@pytest.fixture()
def csv_client():
    """Create a test client with a CSV attached."""
    app.config["unprocessed_dataframe"] = pd.DataFrame(dict(column1=[], column2=[]))
    app.config["filename"] = "my_file.csv"
    return app.test_client()


@pytest.fixture()
def no_party_client():
    """Create a test client with a CSV but no party number."""
    app.config["unprocessed_dataframe"] = pd.DataFrame(dict(column1=[], column2=[]))
    app.config["party_number"] = None
    return app.test_client()


@pytest.fixture()
def party1_client():
    """Create a test client with a CSV and party number 1."""
    app.config["unprocessed_dataframe"] = pd.DataFrame(dict(column1=[], column2=[]))
    app.config["party_number"] = 1
    return app.test_client()
