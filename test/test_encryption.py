"""Unit tests for the `encryption` module."""

import pandas as pd
import pytest

from pprl import encryption


@pytest.mark.parametrize(
    "input_df",
    [
        (
            pd.DataFrame(
                dict(
                    ints=[1, 4, 5, 1273873],
                    bools=[True, False, False, True],
                    strings=["a", "bchc", "12djd", "]p8s|"],
                )
            )
        ),
        (pd.DataFrame(dict())),
        (pd.DataFrame(dict(mixed=[1, True, "my_string", 1.43434]))),
    ],
)
def test_encrypt_decrypt_data(input_df):
    """Make sure the dataframe is unchanged by the encryption process.

    We ignore the index here.
    """

    payload, data_enc_key = encryption.encrypt_data(input_df)
    decrypted_dataframe = encryption.decrypt_data(payload, data_enc_key)
    assert input_df.equals(decrypted_dataframe.reset_index(drop=True))
