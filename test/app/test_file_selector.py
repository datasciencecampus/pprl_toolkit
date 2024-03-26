"""Unit tests for the file selector part of the app."""

import io

import pytest


@pytest.mark.skip(reason="Test client not working in CI build")
def test_file_selector(client):
    """Tests to make sure the upload file page is returned correctly."""

    response = client.get("/")
    assert b"<h2>Upload File</h2>" in response.data


@pytest.mark.skip(reason="Test client not working in CI build")
def test_upload_file_text(client):
    """Check the user is informed if they upload the wrong file type."""

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(b"some_text"), "test.txt")},
        content_type="multipart/form-data",
    )
    assert b"Upload a csv file." in response.data


@pytest.mark.skip(reason="Test client not working in CI build")
def test_upload_file_csv(client):
    """Check the column selector comes up after uploading a CSV."""

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(b"some_text"), "test.csv")},
        content_type="multipart/form-data",
    )
    assert b"<h2>Choose Salt</h2>" in response.data


@pytest.mark.skip(reason="Test client not working in CI build")
def test_upload_file_csv_columns(client):
    """Check the form format in the column selector page."""

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(b"column1,column2,mycolumn3"), "test.csv")},
        content_type="multipart/form-data",
    )
    assert b'<label for="column1">column1: </label>' in response.data
    assert b'<label for="column2">column2: </label>' in response.data
    assert b'<label for="mycolumn3">mycolumn3: </label>' in response.data
    assert b'<select id="column1" name="column1">' in response.data
    assert b'<option value="drop_column">Drop Column</option>' in response.data
    assert b'<option value="name">Name Column</option>' in response.data
    assert b'<option value="dob">Date of Birth Column</option>' in response.data
    assert b'<option value="sex">Sex Column</option>' in response.data
    assert b'<option value="keep_column">Keep Raw Column</option>' in response.data


@pytest.mark.skip(reason="Test client not working in CI build")
def test_process_csv_and_upload_download_json(csv_client):
    """Check a JSON file is served when downloading a file locally."""

    response = csv_client.post(
        "/get_results",
        data={
            "submit_button": "Download file locally",
            "column1": "drop_column",
            "column2": "drop_column",
            "salt": "cat",
        },
        content_type="multipart/form-data",
    )
    assert response.data == b'{"bf_indices":{}}'


@pytest.mark.skip(reason="Test client not working in CI build")
def test_process_csv_and_upload_incorrect_credentials(no_party_client):
    """Check the right page is served when uploading w/o config."""

    response = no_party_client.post(
        "/get_results",
        data={
            "submit_button": "Upload file to GCP  ",
            "column1": "drop_column",
            "column2": "drop_column",
            "salt": "cat",
        },
        content_type="multipart/form-data",
    )
    assert b"Google Cloud Platform credentials not configured correctly." in response.data


@pytest.mark.skip(reason="no way of currently testing this")
def test_process_csv_and_upload_exception(party1_client):
    """Check the right page is served when uploading w/ an exception."""

    response = party1_client.post(
        "/get_results",
        data={
            "submit_button": "Upload file to GCP  ",
            "column1": "drop_column",
            "column2": "drop_column",
            "salt": "cat",
        },
        content_type="multipart/form-data",
    )
    assert b"Permission denied to upload to GCP bucket or it does not exist." in response.data


@pytest.mark.skip(reason="no way of currently testing this")
def test_failed_result_check_no_buckets(no_party_client):
    """Check the right page is served when the bucket is not found."""

    response = no_party_client.post("/get_result_check")
    assert b"Permission denied downloading from GCP bucket or it does not exist." in response.data


@pytest.mark.skip(reason="no way of currently testing this")
def test_passed_result_check_no_buckets(no_party_client):
    """Check the right page is served downloading w/ an exception."""

    response = no_party_client.post("/download_results")
    assert b"Permission denied downloading from GCP bucket or it does not exist." in response.data
