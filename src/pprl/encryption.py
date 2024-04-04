"""Tools for performing envelope encryption on GCP."""

import json

import pandas as pd
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from google.cloud import kms


def encrypt_data(data: pd.DataFrame, key: None | bytes = None) -> tuple[bytes, bytes]:
    """
    Encrypt a data frame.

    Parameters
    ----------
    data : pd.DataFrame
        Dataframe to encrypt.
    key : bytes, optional
        Fernet key to encrypt data frame. If not specified, create one.

    Returns
    -------
    encrypted : bytes
        Encrypted data frame.
    key : bytes
        Fernet key used to encrypt data frame.
    """

    if key is None:
        key = Fernet.generate_key()

    fernet = Fernet(key)
    payload = data.to_json().encode("utf-8")
    encrypted = fernet.encrypt(payload)

    return encrypted, key


def decrypt_data(encrypted: bytes, key: bytes) -> pd.DataFrame:
    """
    Decrypt a data frame with the provided key.

    Parameters
    ----------
    encrypted : bytes
        Data to be decrypted.
    key : bytes
        Key used to encrypt the data.

    Returns
    -------
    data : pd.DataFrame
        Decrypted data frame.
    """

    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted)
    data = pd.DataFrame(json.loads(decrypted))

    return data


def _build_key_version_path(
    party: str, location: str, version: int | str, client: kms.KeyManagementServiceClient
) -> str:
    """
    Build a full key version path for retrieval from KMS.

    Parameters
    ----------
    party : str
        Name of the party whose key to retrieve.
    location : str
        Location of the keyring on which the key lives.
    version : int | str
        Version of the key to retrieve.
    client : google.cloud.kms.KeyManagementServiceClient
        Connection to KMS.

    Returns
    -------
    path : str
        Key version path on KMS.
    """

    keyring, key = f"{party}-akek-kr", f"{party}-akek"
    path = client.crypto_key_version_path(party, location, keyring, key, str(version))

    return path


def _get_public_key(party: str, location: str, version: int | str, **kwargs: dict) -> bytes:
    """
    Get the public key from the GCP Key Management Service (KMS).

    Parameters
    ----------
    party : str
        Name of the party.
    location : str
        Location of the keyring on which the key lives.
    version : int | str
        Key version to use.
    **kwargs : dict
        Keyword arguments to pass when creating an instance of
        `google.cloud.kms.KeyManagementServiceClient`.

    Returns
    -------
    key : str
        The public key object in PEM string format.
    """

    client = kms.KeyManagementServiceClient(**kwargs)
    key_version_path = _build_key_version_path(party, location, version, client)
    public_key = client.get_public_key(request={"name": key_version_path})
    key = public_key.pem.encode("utf-8")

    return key


def encrypt_dek(
    dek: bytes, party: str, location: str = "global", version: int | str = 1, **kwargs
) -> bytes:
    """
    Encrypt the data encryption key.

    We encrypt the data encryption key using the public key portion of
    an asymmetric key retrieved from the GCP Key Management Service.

    Parameters
    ----------
    dek : bytes
        Data encryption key to be encrypted.
    party : str
        Name of the party.
    location : str
        Location of the keyring on which the key lives.
    version : int | str
        Version of the asymmetric key to get from GCP. Default is 1.
    **kwargs : dict
        Keyword arguments to pass when creating an instance of
        `google.cloud.kms.KeyManagementServiceClient`.

    Returns
    -------
    encrypted : bytes
        Encrypted data encryption key.
    """

    # Extract and parse the public key as a PEM-encoded RSA key
    pem = _get_public_key(party, location, version, **kwargs)
    rsa = serialization.load_pem_public_key(pem, default_backend())

    # Construct the padding, which differs based on key choice
    sha = hashes.SHA256()
    mgf = padding.MGF1(algorithm=sha)
    pad = padding.OAEP(mgf=mgf, algorithm=sha, label=None)

    encrypted = rsa.encrypt(dek, pad)

    return encrypted


def decrypt_dek(
    encrypted: bytes, party: str, location: str = "global", version: int | str = 1, **kwargs
) -> bytes:
    """
    Decrypt a data encryption key using an asymmetric key held on KMS.

    Owing to the nature of the encryption key set-up of pprl this
    function is only really to be used in the GCP Confidential Space set
    up by the linkage administrator.

    Parameters
    ----------
    encrypted : bytes
        Key to be decrypted.
    party : str
        Name of the party whose key we are decrypting.
    location : str
        Location of the keyring on which the key lives.
    version : int | str
        Version of the asymmetric key to get from GCP. Default is 1.
    **kwargs : dict
        Keyword arguments to pass when creating an instance of
        `google.cloud.kms.KeyManagementServiceClient`.

    Returns
    -------
    dek : bytes
        Decrypted data encryption key.
    """

    client = kms.KeyManagementServiceClient(**kwargs)
    key_version_path = _build_key_version_path(party, location, version, client)
    response = client.asymmetric_decrypt(
        request={"name": key_version_path, "ciphertext": encrypted}
    )

    return response.plaintext
