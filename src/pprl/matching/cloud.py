"""Functions for performing matching in the cloud."""

import json
import logging

import pandas as pd
from google.auth import identity_pool
from google.cloud import storage

from pprl import encryption
from pprl.embedder.embedder import Embedder


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
