"""Script for administrators to run linkage on a server or locally."""

import json
import logging
import os

import google.cloud.logging
import numpy as np
import pandas as pd
from google.auth import identity_pool
from google.cloud import storage

from pprl import config, encryption
from pprl.embedder.embedder import EmbeddedDataFrame, Embedder
from pprl.utils.server_utils import add_private_index

## CLOUD FUNCTIONS


def create_impersonation_credentials(party: str, operator: str) -> identity_pool.Credentials:
    """
    Create credentials from an identity pool for impersonating a party.

    Parameters
    ----------
    party : str
        Name of the party to impersonate.
    operator : str
        Name of the workload operator.

    Returns
    -------
    credentials : google.auth.identity_pool.Credentials
        Credentials created using the party attestation verifier.
    """

    store = storage.Client()
    bucket = store.get_bucket(f"{operator}-attestation-bucket")
    string = bucket.get_blob(f"{party}-attestation-credentials.json").download_as_string()
    info = json.loads(string)

    credentials = identity_pool.Credentials.from_info(
        info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )

    return credentials


def download_embedder(parties: list[str], operator: str) -> Embedder:
    """
    Download and initiate the embedder from those on GCP.

    Parameters
    ----------
    parties : list[str]
        List of data-owning party names.
    operator : str
        Name of the workload operator.

    Returns
    -------
    embedder : Embedder
        Reformed embedder instance.
    """

    embedders = []
    for party in parties:
        logging.info(f"Retrieving embedder pickle for {party}...")

        credentials = create_impersonation_credentials(party, operator)

        store = storage.Client(party, credentials=credentials)
        bucket = store.get_bucket(f"{party}-bucket")
        pickled = bucket.get_blob("embedder.pkl").download_as_string()

        logging.info("Creating embedder from pickle...")
        embedder = Embedder.from_pickle(pickled=pickled)

        embedders.append(embedder)

        logging.info("Embedder recreated.")

    logging.info("Comparing the embedders...")
    embedder, embedder_2 = embedders
    if embedder.checksum != embedder_2.checksum:
        logging.error("Embedders do not match.")

    return embedder


def download_party_assets(store: storage.Client, party: str) -> tuple[bytes, bytes]:
    """
    Download the encrypted data and DEK for a party from GCP.

    Parameters
    ----------
    store : google.cloud.storage.Client
        GCP storage client using identity pool credentials.
    party : str
        Name of the party.

    Returns
    -------
    data_encrypted : bytes
        Encrypted data frame for linkage.
    dek_encrypted : bytes
        Encrypted data encryption key (used to encrypt the data).
    """

    bucket = store.get_bucket(f"{party}-bucket")
    data_encrypted = bucket.get_blob("encrypted_data").download_as_string()
    dek_encrypted = bucket.get_blob("encrypted_dek").download_as_string()

    return data_encrypted, dek_encrypted


def prepare_party_assets(
    party: str, operator: str, location: str, version: int | str
) -> tuple[pd.DataFrame, bytes]:
    """
    Download and decrypt the assets for a party from GCP.

    To enable these steps, we must first impersonate the party service
    account via the workload identity pool we created during project
    set-up.

    Parameters
    ----------
    party : str
        Name of the party.
    operator : str
        Name of the workload operator.
    location : str
        Location of the party's workload identity pool and keyring on
        GCP.
    version : int | str
        Key version to retrieve for party asymmetric key encryption key.

    Returns
    -------
    data : pandas.DataFrame
        Decrypted data frame for linkage.
    dek : bytes
        Decrypted data encryption key.
    """

    credentials = create_impersonation_credentials(party, operator)
    store = storage.Client(party, credentials=credentials)

    logging.info(f"Loading assets for {party}...")
    data_encrypted, dek_encrypted = download_party_assets(store, party)

    logging.info(f"Decrypting DEK for {party}...")
    dek = encryption.decrypt_dek(dek_encrypted, party, location, version, credentials=credentials)

    logging.info(f"Decrypting data for {party}...")
    data = encryption.decrypt_data(data_encrypted, dek)

    return data, dek


def upload_party_results(output: pd.DataFrame, dek: bytes, party: str, operator: str) -> None:
    """
    Encrypt and upload a party's results to GCP.

    Like `prepare_party_assets`, we must first impersonate the party
    service account to access their storage bucket.

    Parameters
    ----------
    output : pandas.DataFrame
        Party's output from the matching.
    dek : bytes
        Data encryption key.
    party : str
        Name of the party whose results are being processed.
    operator : str
        Name of the workload operator.
    """

    logging.info(f"Encrypting results for {party}...")
    encrypted, _ = encryption.encrypt_data(output, dek)

    credentials = create_impersonation_credentials(party, operator)
    store = storage.Client(credentials=credentials)
    bucket = store.get_bucket(f"{party}-bucket")

    logging.info(f"Uploading encrypted results for {party}...")
    bucket.blob("encrypted_output").upload_from_string(encrypted)


## LOCAL FUNCTIONS


def build_local_file_paths(party: str) -> tuple[str, str]:
    """
    Construct the paths for the input and output datasets for a party.

    Parameters
    ----------
    party : str
        Name of the party.

    Returns
    -------
    inpath : str
        Location of the party data.
    outpath : str
        Location to put the party results.
    """

    stem = config.DIR_DATA_INTERIM
    inpath = os.path.join(stem, f"{party}-data.json")
    outpath = os.path.join(stem, f"{party}-output.json")

    return inpath, outpath


def load_embedder() -> Embedder:
    """
    Load an embedder from a pickle in the local data directory.

    Returns
    -------
    embedder : Embedder
        Reformed embedder instance.
    """

    path = os.path.join(config.DIR_DATA_INTERIM, "embedder.pkl")
    embedder = Embedder.from_pickle(path=path)

    return embedder


## SHARED FUNCTIONS


def calculate_performance(
    data_1: pd.DataFrame, data_2: pd.DataFrame, match: tuple[list, list]
) -> None:
    """
    Calculate the performance of the match by counting the positives.

    Performance metrics are sent to the logger.

    Parameters
    ----------
    data_1 : pandas.DataFrame
        Data frame for `PARTY1`.
    data_2 : pandas.DataFrame
        Data frame for `PARTY2`.
    match : tuple
        Tuple of indices of matched pairs between the data frames.
    """

    data_1_sorted = data_1.iloc[list(match[0]), :]
    data_2_sorted = data_2.iloc[list(match[1]), :]
    tps = sum(map(np.equal, data_1_sorted["true_id"], data_2_sorted["true_id"]))
    fps = len(match[0]) - tps

    logging.info(f"True positives {tps}; false positives {fps}")


def perform_matching(
    data_1: pd.DataFrame, data_2: pd.DataFrame, embedder: Embedder
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Initiate the data, get similarities, and match the rows.

    Parameters
    ----------
    data_1 : pandas.DataFrame
        Data frame for `PARTY1`.
    data_2 : pandas.DataFrame
        Data frame for `PARTY2`.
    embedder : Embedder
        Instance used to embed both data frames.

    Returns
    -------
    output_1 : pandas.DataFrame
        Output for `PARTY1`.
    output_2 : pandas.DataFrame
        Output for `PARTY2`.
    """

    logging.info("Initialising data with norms and thresholds...")
    edf_1 = EmbeddedDataFrame(data_1, embedder, update_norms=True, update_thresholds=True)
    edf_2 = EmbeddedDataFrame(data_2, embedder, update_norms=True, update_thresholds=True)

    logging.info("Calculating similarities...")
    similarities = embedder.compare(edf_1, edf_2)
    match = similarities.match()

    logging.info("Matching completed!")

    # size_assumed must be > data size
    output_1, output_2 = add_private_index(data_1, data_2, match, size_assumed=10_000)

    # If the true index is provided, print performance
    if "true_id" in data_1.columns and "true_id" in data_2.columns:
        calculate_performance(data_1, data_2, match)

    return output_1, output_2


def load_environment_variables(path: None | str = None) -> tuple[str, str, str, str, str]:
    """
    Load the environment and pull out the core pieces.

    Parameters
    ----------
    path : str, optional
        Path to environment file. If running locally, no need to provide
        anything.

    Returns
    -------
    operator : str
        Name of the workload operator.
    party_1 : str
        Name of the first party.
    party_2 : str
        Name of the second party.
    location : str
        Location of the workload identity pools and keyrings.
    version : str
        Version of the key encryption keys.
    """

    environ = config.load_environment(path)

    operator = environ.get("WORKLOAD_OPERATOR_PROJECT")
    party_1 = environ.get("PARTY_1_PROJECT")
    party_2 = environ.get("PARTY_2_PROJECT")
    location = environ.get("PROJECT_LOCATION", "global")
    version = environ.get("PROJECT_KEY_VERSION", 1)

    return operator, party_1, party_2, location, version


def main():
    """Perform the matching process and save the results."""

    if int(os.getenv("PRODUCTION", 0)) == 1:
        logger = google.cloud.logging.Client()
        logger.setup_logging()
        logging.info("Logging set up.")

        operator, party_1, party_2, location, version = load_environment_variables(".env")
        parties = (party_1, party_2)

        logging.info("Downloading embedder...")
        embedder = download_embedder(parties, operator)

        logging.info("Preparing assets...")
        data_1, dek_1 = prepare_party_assets(party_1, operator, location, version)
        data_2, dek_2 = prepare_party_assets(party_2, operator, location, version)

        logging.info("Performing matching...")
        outputs = perform_matching(data_1, data_2, embedder)

        logging.info("Uploading results...")
        for party, output, dek in zip(parties, outputs, (dek_1, dek_2)):
            logging.info(f"Uploading results for {party}...")
            upload_party_results(output, dek, party, operator)

    else:
        # Set up local logging and storage
        logging.basicConfig(encoding="utf-8", level=logging.INFO)

        operator, party_1, party_2, location, version = load_environment_variables()
        inpath_1, outpath_1 = build_local_file_paths(party_1)
        inpath_2, outpath_2 = build_local_file_paths(party_2)
        embedder = load_embedder()

        # Loading local files
        logging.info("Loading files...")
        data_1 = pd.read_json(inpath_1)
        data_2 = pd.read_json(inpath_2)

        logging.info("Performing matching...")
        output_1, output_2 = perform_matching(data_1, data_2, embedder)

        logging.info("Saving results...")
        output_1.to_json(outpath_1)
        output_2.to_json(outpath_2)

    logging.info("Done!")


if __name__ == "__main__":
    main()
