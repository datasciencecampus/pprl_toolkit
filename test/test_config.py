"""Unit tests for the `config` module."""

import os
import string
from pathlib import Path
from unittest import mock

from hypothesis import given
from hypothesis import strategies as st

import pprl
from pprl import config

st_text = st.text(alphabet=string.ascii_lowercase, min_size=1)


@given(st_text, st.one_of((st.just(None), st_text)))
def test_find_directory(kind, what):
    """Test that a directory can be found correctly."""

    root = Path("/path/to/a/test/module")
    with mock.patch("pprl.config.inspect.getfile") as get:
        get.return_value = root / "where" / "stuff" / "lives"
        directory = config._find_directory(kind, what)

    assert isinstance(directory, Path)

    if what is None:
        assert directory.stem == kind
        assert directory.parent == root
    else:
        assert directory.stem == what
        assert directory.parent == root / kind

    get.assert_called_once_with(pprl)


@given(st_text)
def test_load_environment_with_filename(filename):
    """Test the config loader works with a file name."""

    with (
        mock.patch("pprl.config.dotenv.dotenv_values") as values,
        mock.patch("pprl.config.os.path.join") as join,
    ):
        values.return_value = "foo"
        result = config.load_environment(filename)

    assert result == "foo"

    values.assert_called_once_with(filename)
    join.assert_not_called()


def test_load_environment_default():
    """Test the config loader works without a file name."""

    with mock.patch("pprl.config.dotenv.dotenv_values") as values:
        values.return_value = "foo"
        result = config.load_environment()

    assert result == "foo"

    values.assert_called_once_with(os.path.join(config.PPRL_ROOT, ".env"))
