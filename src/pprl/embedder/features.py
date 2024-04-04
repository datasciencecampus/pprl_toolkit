"""Feature generation functions for various column types."""

import re
from typing import Generator, Hashable

import pandas as pd
from metaphone import doublemetaphone


def split_string_underscore(string: str) -> list[str]:
    """Split and underwrap a string at typical punctuation marks.

    Currently, we split at any combination of spaces, dashes, dots,
    commas, or underscores.

    Examples
    --------
    >>> strings = ("dave  william johnson", "Francesca__Hogan-O'Malley")
    >>> for string in strings:
    ...     print(split_string_underscore(string))
    ["_dave_", "_william_", "_johnson_"]
    ["_Francesca_", "_Hogan_", "_O'Malley_"]

    Parameters
    ----------
    string: str
        String to split.

    Returns
    -------
    split: list[str]
        List of the split and wrapped tokens.
    """
    words = re.split(r"[\s\+\-\_\,\.]+", string)
    split = [f"_{word}_" for word in words if word]

    return split


def gen_ngram(split_tokens: list, ngram_length: list) -> Generator[str, None, None]:
    """Generate n-grams from a set of tokens.

    This is a generator function that contains a series of n-grams the
    size of the sliding window.

    Parameters
    ----------
    split_tokens: list
        All the split-up tokens from which to form n-grams.
    ngram_length: list
        Desired lengths of n-grams. For examples, `ngram_length=[2, 3]`
        would generate all 2-grams and 3-grams.

    Returns
    -------
    ngram : str
        The next n-gram in the sequence.
    """
    for n in ngram_length:
        for token in split_tokens:
            chr_length = len(token)
            for i in range(chr_length - n + 1):
                ngram = token[i : i + n]
                if ngram != "_":
                    yield ngram


def gen_skip_grams(split_tokens: list) -> Generator[str, None, None]:
    """Generate skip 2-grams from a set of tokens.

    This function is a generator that contains a series of skip 2-grams.

    Examples
    --------
    >>> string = "dave james"
    >>> tokens = split_string_underscore(string)
    >>> skips = list(gen_skip_grams(tokens))
    >>> print(skips)
    ["_a", "dv", "ae", "v_", "_a", "jm", "ae", "ms", "e_"]


    Parameters
    ----------
    split_tokens: list
        All the split-up tokens from which to form skip 2-grams.

    Returns
    -------
    skip: str
        The next skip 2-gram in the sequence.
    """
    for token in split_tokens:
        chr_length = len(token)
        for i in range(chr_length - 2):
            yield token[i] + token[i + 2]


def gen_double_metaphone(string: str) -> Generator[str, None, None]:
    """Generate the double methaphones of a string.

    This function is a generator containing all the possible, non-empty
    double metaphones of a given string, separated by spaces. This
    function uses the `metaphone.doublemetaphone()` function under the
    hood, ignoring any empty strings. See their
    [repository](https://github.com/oubiwann/metaphone) for details.

    Parameters
    ----------
    string: str
        String from which to derive double metaphones.

    Returns
    -------
    metaphone: str
        The next double metaphone in the sequence.
    """
    for token in string.split():
        double_metaphone = doublemetaphone(token)
        for metaphone in double_metaphone:
            if metaphone != "":
                yield metaphone


def gen_features(
    string: str,
    ngram_length: list = [2, 3],
    use_gen_ngram: bool = True,
    use_gen_skip_grams: bool = False,
    use_double_metaphone: bool = False,
) -> Generator[str, None, None]:
    """Generate string features of various types.

    This function is a generator capable of producing n-grams, skip
    2-grams, and double metaphones from a single string. These outputs
    are referred to as features.

    Parameters
    ----------
    string: str
        Base string from which to generate features.
    ngram_length: list
        Lengths of n-grams to make. Ignored if `use_gen_ngram=False`.
    use_gen_ngram: bool
        Whether to create n-grams. Default is `True`.
    use_gen_skip_grams: bool
        Whether to create skip 2-grams. Default is `False`.
    use_double_metaphone: bool
        Whether to create double metaphones. Default is `False`.

    Returns
    -------
    feature: str
        The next feature in the sequence.
    """
    lower = string.lower()
    split_tokens = split_string_underscore(lower)

    if use_gen_ngram is True:
        yield from gen_ngram(split_tokens, ngram_length=ngram_length)
    if use_gen_skip_grams is True:
        yield from gen_skip_grams(split_tokens)
    if use_double_metaphone is True:
        yield from gen_double_metaphone(lower)


def gen_name_features(
    names: pd.Series,
    ngram_length: list[int] = [2, 3],
    use_gen_ngram: bool = True,
    use_gen_skip_grams: bool = False,
    use_double_metaphone: bool = False,
) -> pd.Series:
    """Generate a features series for a series of names.

    Effectively, this function is a call to `pd.Series.apply()` using
    our `gen_features()` string feature generator function.

    Parameters
    ----------
    names: pd.Series
        Series of names.
    ngram_length: list
        Lengths of n-grams to make. Ignored if `use_gen_ngram=False`.
    use_gen_ngram: bool
        Whether to create n-grams. Default is `True`.
    use_gen_skip_grams: bool
        Whether to create skip 2-grams. Default is `False`.
    use_double_metaphone: bool
        Whether to create double metaphones. Default is `False`.

    Returns
    -------
    pd.Series
        Series containing lists of features.
    """
    features = (
        names.copy()
        .fillna("")
        .apply(
            lambda name: list(
                gen_features(
                    name,
                    ngram_length,
                    use_gen_ngram,
                    use_gen_skip_grams,
                    use_double_metaphone,
                )
            )
        )
    )

    return features


def gen_sex_features(sexes: pd.Series) -> pd.Series:
    """Generate labelled sex features from a series of sexes.

    Features take the form `["sex<option>"]` or `[""]` for missing data.

    Parameters
    ----------
    sexes: pd.Series
        Series of sex data.

    Returns
    -------
    pd.Series
        Series containing lists of sex features.
    """
    assert not any(
        isinstance(sex, list) for sex in sexes
    ), "Elements of `sexes` should not be lists"

    sexes = (
        sexes.copy()
        .str.casefold()  # make everything lowercase
        .str[0]  # take the first character
        .replace(
            r"(^.*$)",  # match the whole string (in a group)
            r"sex<\1>",  # wrap the string in 'sex<>'
            regex=True,
        )
        .fillna("")
        .apply(lambda sex: [sex])
    )

    return sexes


def gen_dateofbirth_features(
    dob: pd.Series,
    dayfirst: bool = True,
    yearfirst: bool = False,
    default: list[str] = ["day<01>", "month<01>", "year<2050>"],
) -> pd.Series:
    """Generate labelled date features from a series of dates of birth.

    Features take the form `["day<dd>", "month<mm>", "year<YYYY>"]`.
    Note that this feature generator can be used for any sort of date
    data, not just dates of birth.

    Parameters
    ----------
    dob: pd.Series
        Series of dates of birth.
    dayfirst: bool
        Whether the day comes first in the DOBs. Passed to
        `pd.to_datetime()` and defaults to `True`.
    yearfirst: bool
        Whether the year comes first in the DOBs. Passed to
        `pd.to_datetime()` and defaults to `False`.
    default: list
        Default date to fill in missing data in feature (list) form.
        Default is the feature form of `2050-01-01`.

    Returns
    -------
    pd.Series
        Series containing lists of date features.
    """
    datetimes = pd.to_datetime(dob, errors="coerce", dayfirst=dayfirst, yearfirst=yearfirst)

    features = (
        datetimes.dt.strftime("day<%d>_month<%m>_year<%Y>")
        .str.split("_")
        .fillna("")
        .apply(lambda date: default if date == "" else date)
    )

    return features


def gen_misc_features(field: pd.Series, label: None | str | Hashable = None) -> pd.Series:
    """Generate miscellaneous categorical features for a series.

    Useful for keeping raw columns in the linkage data. All features
    use a label and take the form `["label<option>"]` except for missing
    data, which are coded as `""`.

    Parameters
    ----------
    field: pd.Series
        Series from which to generate our features.
    label: str, optional
        Label for the series. By default, the name of the series is
        used if available. Otherwise, if not specified, `misc` is used.

    Returns
    -------
    pd.Series
        Series containing lists of miscellaneous features.
    """
    label = label or field.name or "misc"

    _field = (
        field.copy()
        .fillna("no_data")
        .astype("str")
        .str.casefold()  # make everything lowercase
        .replace(
            r"(^.*$)",  # match the whole string in a group
            rf"{label}<\1>",  # markup the string with label
            regex=True,
        )
    )
    _field_list = _field.apply(lambda x: [x])
    _field_list.loc[_field == f"{label}<no_data>"] = ""  # disappears later

    return _field_list


def gen_misc_shingled_features(
    field: pd.Series,
    ngram_length: list[int] = [2, 3],
    use_gen_skip_grams: bool = False,
    label: None | str | Hashable = None,
) -> pd.Series:
    """Generate shingled labelled features.

    Generate n-grams, with a label to distinguish them from (and ensure
    they're hashed separately from) names. Like `gen_name_features()`,
    this function makes a call to `gen_features()` via
    `pd.Series.apply()`.

    Parameters
    ----------
    field : pd.Series
        Series of string data.
    ngram_length : list, optional
        Shingle sizes to generate. By default `[2, 3]`.
    use_gen_skip_grams : bool
        Whether to generate skip 2-grams. `False` by default.
    label : str, optional
        A label to differentiate from other shingled features. If
        `field` has no name, this defaults to `zz`.

    Returns
    -------
    pd.Series
        Series containing lists of shingled string features.
    """
    label = label or field.name or "zz"

    _field = (
        field.copy()
        .fillna("")
        .apply(
            lambda string: [
                f"{label}<{feature}>"
                for feature in gen_features(
                    string,
                    ngram_length=ngram_length,
                    use_gen_skip_grams=use_gen_skip_grams,
                )
            ]
        )
    )

    return _field
