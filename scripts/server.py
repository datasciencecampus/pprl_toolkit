"""Script for running linkage on a server or locally."""

import logging
import os

import google.cloud.logging
import pandas as pd

from pprl import config
from pprl.matching import cloud, local, perform_matching


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
    version_1 : str
        Version of the key encryption key for the first party.
    version_2 : str
        Version of the key encryption key for the second party.
    """

    environ = config.load_environment(path)

    operator = environ.get("WORKLOAD_OPERATOR_PROJECT")
    party_1 = environ.get("PARTY_1_PROJECT")
    party_2 = environ.get("PARTY_2_PROJECT")
    location = environ.get("PROJECT_LOCATION", "global")
    version_1 = environ.get("PARTY_1_KEY_VERSION", 1)
    version_2 = environ.get("PARTY_2_KEY_VERSION", 1)

    return operator, party_1, party_2, location, version_1, version_2


def main():
    """Perform the matching process and save the results."""

    if int(os.getenv("PRODUCTION", 0)) == 1:
        logger = google.cloud.logging.Client()
        logger.setup_logging()
        logging.info("Logging set up.")

        operator, party_1, party_2, location, version_1, version_2 = load_environment_variables(
            ".env"
        )
        parties = (party_1, party_2)

        logging.info("Downloading embedder...")
        embedder = cloud.download_embedder(parties, operator)

        logging.info("Preparing assets...")
        data_1, dek_1 = prepare_party_assets(party_1, operator, location, version_1)
        data_2, dek_2 = prepare_party_assets(party_2, operator, location, version_2)

        logging.info("Performing matching...")
        outputs = perform_matching(data_1, data_2, embedder)

        logging.info("Uploading results...")
        for party, output, dek in zip(parties, outputs, (dek_1, dek_2)):
            logging.info(f"Uploading results for {party}...")
            cloud.upload_party_results(output, dek, party, operator)

    else:
        logging.basicConfig(encoding="utf-8", level=logging.INFO)

        logging.info("Setting up environment and file paths...")
        operator, party_1, party_2, *_ = load_environment_variables()
        inpath_1, outpath_1 = build_local_file_paths(party_1)
        inpath_2, outpath_2 = build_local_file_paths(party_2)

        logging.info("Loading files...")
        embedder = load_embedder()
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
