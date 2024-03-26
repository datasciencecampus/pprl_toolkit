"""Functions for handling PPRL configuration."""

import inspect
import os
from pathlib import Path

import dotenv

import pprl


def _find_directory(kind: str, what: str | None = None) -> Path:
    """
    Find a directory in the root of the `pprl` installation.

    Parameters
    ----------
    kind : str
        The category of directory to find. Typically `data` or `log`.
    what : str, optional
        The name of the directory in `kind` to find. If not specified,
        then `kind` is treated as the name of the directory.

    Returns
    -------
    where : pathlib.Path
        Path object to the directory.
    """

    where = Path(inspect.getfile(pprl)).parent.parent.parent / kind

    if what is not None:
        where /= what

    return where


def load_environment(path: None | str = None) -> dict[str, None | str]:
    """
    Load the configuration file as a dictionary.

    Parameters
    ----------
    path : str, optional
        Location of the configuration file to load. If not specified,
        try to load the configuration file from the root of the `pprl`
        installation called `.env`.

    Returns
    -------
    config : collections.OrderedDict
        Mapping of the key-value pairs in the configuration file.
    """

    if path is None:
        path = os.path.join(PPRL_ROOT, ".env")

    return dotenv.dotenv_values(path)


PPRL_ROOT = _find_directory("")
DIR_DATA_RAW = _find_directory("data", "raw")
DIR_DATA_INTERIM = _find_directory("data", "interim")
DIR_DATA_PROCESSED = _find_directory("data", "processed")
DIR_LOGS = _find_directory("log")
