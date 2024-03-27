"""Party-side Flask app for embedding, encrypting and uploading data."""

from datetime import datetime, timezone

import flask
import pandas as pd
from google.cloud import storage
from recordlinkage.datasets import load_febrl4

from pprl import config, encryption

from . import utils

app = flask.Flask(__name__, template_folder="templates")

app.config["feature_funcs"] = {
    "Name": "name",
    "Date": "dob",
    "Sex": "sex",
    "Miscellaneous": "misc_features",
    "Shingled": "misc_shingled_features",
}


@app.route("/")
def home():
    """View the home page where users choose a configuration file."""

    environ = config.load_environment()
    parties = (environ.get("PARTY_1_PROJECT"), environ.get("PARTY_2_PROJECT"))
    app.config["env"] = environ
    app.config["parties"] = parties

    return flask.render_template("home.html", parties=parties)


@app.route("/", methods=["POST"])
def home_post():
    """Load the config, connect to GCP, and go to choosing data."""

    party = flask.request.form["party"]
    app.config["party"] = party
    app.config["store"] = storage.Client(party)

    return flask.redirect(flask.url_for("choose_data"))


@app.route("/choose")
def choose_data():
    """View the data selection page."""

    return flask.render_template("choose-data.html")


@app.route("/choose", methods=["POST"])
def choose_data_post():
    """Load in the dataset and go on to process the columns."""

    request = flask.request
    if request.form["radio_input"] == "local_file":
        file = request.files["file"]
        if utils.check_is_csv(file.filename):
            data = pd.read_csv(file, dtype=str).fillna("")
        else:
            return flask.render_template(
                "choose-data.html", message="Please choose a CSV file to upload."
            )

    if "FEBRL" in (inp := request.form["radio_input"]):
        febrl_a, febrl_b = load_febrl4()
        data = febrl_a if inp.endswith("a") else febrl_b

    app.config["unprocessed_data"] = data

    return flask.redirect(flask.url_for("process_data"))


@app.route("/process")
def process_data():
    """View the column processing page."""

    return flask.render_template(
        "process-data.html",
        columns=app.config.get("unprocessed_data").columns,
        column_types=app.config.get("feature_funcs"),
    )


@app.route("/process", methods=["POST"])
def process_data_post():
    """Process the data, then download or upload to GCP as needed."""

    drop, keep, spec = utils.assign_columns(flask.request.form, app.config.get("feature_funcs"))
    salt = flask.request.form["salt"]

    data = utils.convert_dataframe_to_bf(
        app.config.get("unprocessed_data").drop(drop, axis=1), spec, keep, salt
    )
    app.config["processed_data"] = data.drop("bf_norms", axis=1)

    if "download" in flask.request.form:
        return utils.download_files(data, embedder=None, party=app.config["party"])

    if "upload" in flask.request.form:
        return upload_to_gcp(data, embedder=None)


@app.route("/upload")
def upload_to_gcp(data, embedder):
    """Encrypt and upload the data to GCP, then wait for results."""

    app.config["submission_time"] = datetime.now(timezone.utc)
    party = app.config.get("party")
    environ = app.config.get("env")

    location = environ.get("PROJECT_LOCATION", "global")

    party_num = next(i + 1 for i, part in app.config["parties"] if party == part)
    version = environ.get(f"PARTY_{party_num}_KEY_VERSION", 1)

    data_encrypted, dek = encryption.encrypt_data(data)
    dek_encrypted = encryption.encrypt_dek(dek, party, location, version)
    app.config["dek"] = dek

    store = app.config.get("store")
    bucket = store.get_bucket(f"{party}-bucket")

    bucket.blob("encrypted_data").upload_from_string(data_encrypted)
    bucket.blob("encrypted_dek").upload_from_string(dek_encrypted)

    return flask.redirect(flask.url_for("check_results"))


@app.route("/results")
def check_results():
    """View the results holding page."""

    return flask.render_template("check-results.html")


@app.route("/results", methods=["POST"])
def check_results_post():
    """Check for updated results on GCP. Redirect when they're ready."""

    party = app.config.get("party")
    store = app.config.get("store")
    bucket = store.get_bucket(f"{party}-bucket")

    blob = bucket.blob("encrypted_output")
    if blob.exists():
        blob = bucket.get_blob("encrypted_output")
        if blob.updated > app.config.get("submission_time"):
            encrypted = blob.download_as_string()
            app.config["embedder"] = bucket.blob("embedder.pkl").download_as_string()
            app.config["processed_data"] = encryption.decrypt_data(
                encrypted, app.config.get("dek")
            )

            return flask.redirect(flask.url_for("download_results"))

    now = datetime.now(timezone.utc)
    message = f"Results not available. Last checked at: {now.strftime('%H:%M:%S')}."

    return flask.render_template("check-results.html", message=message)


@app.route("/download-results")
def download_results():
    """View the results downloader page."""

    return flask.render_template("download-results.html")


@app.route("/download-results", methods=["POST"])
def download_results_post():
    """Download the results as a ZIP archive."""

    return utils.download_files(
        app.config["processed_data"],
        app.config["embedder"],
        app.config["party"],
        archive="results",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
