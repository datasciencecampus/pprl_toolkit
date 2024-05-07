"""Unit tests for the features module."""

import re
from datetime import datetime
from unittest import mock

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from metaphone import doublemetaphone

from pprl.embedder import features as feat

from .strategies import (
    NAMES,
    st_default_dobs,
    st_dobs_and_order_params,
    st_fields_series,
    st_mutated_names,
    st_names_series,
    st_sexes_series,
    st_strings_series,
    st_tokenized_names,
)


@given(st_mutated_names())
def test_split_string_underscore(name_mutated):
    """Test the string splitter can tokenize names correctly."""

    name, mutated = name_mutated
    tokens = feat.split_string_underscore(mutated)
    expected = [f"_{word}_" for word in re.split("[ -]", name)]

    assert tokens == expected


@given(st_tokenized_names(), st.lists(st.integers(1, 3), min_size=1, max_size=2, unique=True))
def test_gen_ngram(tokens, lengths):
    """Test the ngram generator can process tokenized names."""

    ngrams = list(feat.gen_ngram(tokens, lengths))

    assert all(gram in "".join(tokens) for gram in ngrams)
    assert all(len(gram) in lengths for gram in ngrams)


@given(st_tokenized_names())
def test_gen_ngram_too_long(tokens):
    """Test the ngram generator returns nothing for too-long ngrams."""

    length = max(map(len, tokens)) + 1
    ngrams = list(feat.gen_ngram(tokens, [length]))

    assert ngrams == []


@pytest.mark.parametrize(
    "test_input,expected,ngram_length",
    [
        (
            ["dave", "wilson"],
            ["da", "av", "ve", "wi", "il", "ls", "so", "on", "wilso", "ilson"],
            [2, 5],
        ),
        (["ron", "bill"], ["r", "o", "n", "b", "i", "l", "l"], [1]),
    ],
)
def test_gen_ngram_examples(test_input, expected, ngram_length):
    """Test to make sure n-grams are generated correctly.

    Our examples include tests for multiple n-gram lengths and for
    1-grams.
    """
    assert set([i for i in feat.gen_ngram(test_input, ngram_length)]) == set(expected)


@given(st_tokenized_names())
def test_gen_skip_grams(tokens):
    """Test the skip 2-gram generator works."""

    skip2grams = list(feat.gen_skip_grams(tokens))

    joined = "".join(tokens)
    cursor = 0
    for a, b in skip2grams:
        match = re.match(f"{a}.{b}", joined[cursor:])
        cursor += 3 if b == "_" else 1
        assert match is not None


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (["dave", "wilson"], ["dv", "ae", "wl", "is", "lo", "sn"]),
        (["ron", "bill"], ["rn", "bl", "il"]),
    ],
)
def test_gen_skip_grams_examples(test_input, expected):
    """Tests to make sure skipgrams are generated separately for each token."""
    assert set([i for i in feat.gen_skip_grams(test_input)]) == set(expected)


@given(st.sampled_from(NAMES))
def test_gen_double_metaphone(name):
    """Test the double metaphone generator works."""

    doubles = list(feat.gen_double_metaphone(name))

    split = name.split()
    double_by_word = [doublemetaphone(word) for word in split]
    expected = [meta for double in double_by_word for meta in double if meta]

    assert len(split) <= len(doubles) <= len(split) * 2
    assert doubles == expected


@pytest.mark.parametrize(
    "test_input,expected", [("dave wilson", ["ALSN", "FLSN", "TF"]), ("ron bill", ["PL", "RN"])]
)
def test_gen_double_metaphone_examples(test_input, expected):
    """Tests to make sure double metaphones are generated separately for each token."""
    assert set([i for i in feat.gen_double_metaphone(test_input)]) == set(expected)


@given(
    st.sampled_from(NAMES),
    st.lists(st.integers(1, 3), min_size=1, max_size=2),
    st.booleans(),
    st.booleans(),
    st.booleans(),
)
def test_gen_features(name, lengths, ngram, skip2gram, double_metaphone):
    """Test the feature generator works."""

    with (
        mock.patch("pprl.embedder.features.split_string_underscore") as splitter,
        mock.patch("pprl.embedder.features.gen_ngram") as gen_ngram,
        mock.patch("pprl.embedder.features.gen_skip_grams") as gen_skip_grams,
        mock.patch("pprl.embedder.features.gen_double_metaphone") as gen_double_metaphone,
    ):
        splitter.return_value = "tokens"
        gen_ngram.return_value = iter(["ngram"])
        gen_skip_grams.return_value = iter(["skip2grams"])
        gen_double_metaphone.return_value = iter(["double_metaphone"])

        features = list(feat.gen_features(name, lengths, ngram, skip2gram, double_metaphone))

    assert isinstance(features, list)
    assert len(features) == sum((ngram, skip2gram, double_metaphone))

    if ngram:
        assert "ngram" in features
        gen_ngram.assert_called_once_with("tokens", ngram_length=lengths)
    else:
        gen_ngram.assert_not_called()

    if skip2gram:
        assert "skip2grams" in features
        gen_skip_grams.assert_called_once_with("tokens")
    else:
        gen_skip_grams.assert_not_called()

    if double_metaphone:
        assert "double_metaphone" in features
        gen_double_metaphone.assert_called_once_with(name.lower())
    else:
        gen_double_metaphone.assert_not_called()

    splitter.assert_called_once_with(name.lower())


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            "dave wilson",
            [
                "_d",
                "da",
                "av",
                "ve",
                "e_",
                "_w",
                "wi",
                "il",
                "ls",
                "so",
                "on",
                "n_",
                "_a",
                "dv",
                "ae",
                "v_",
                "_i",
                "wl",
                "is",
                "lo",
                "sn",
                "o_",
                "ALSN",
                "FLSN",
                "TF",
            ],
        ),
        (
            "ron bill",
            [
                "_r",
                "ro",
                "on",
                "n_",
                "_b",
                "bi",
                "il",
                "ll",
                "l_",
                "_o",
                "rn",
                "o_",
                "_i",
                "bl",
                "il",
                "l_",
                "PL",
                "RN",
            ],
        ),
    ],
)
def test_gen_features_examples(test_input, expected):
    """Tests to make sure all the string features can be made correctly.

    These include n-grams, skip-grams and double metaphones for the
    names 'dave wilson' and 'ron bill'.
    """
    assert set(
        [
            i
            for i in feat.gen_features(
                test_input, use_gen_skip_grams=True, use_double_metaphone=True, ngram_length=[2]
            )
        ]
    ) == set(expected)


@given(
    st_names_series(),
    st.lists(st.integers(1, 3), min_size=1, max_size=2),
    st.booleans(),
    st.booleans(),
    st.booleans(),
)
def test_gen_name_features(names, lengths, ngram, skip2gram, double_metaphone):
    """Test the name series feature generator works."""

    with mock.patch("pprl.embedder.features.gen_features") as gen_features:
        gen_features.return_value = ["foo"]

        name_features = feat.gen_name_features(names, lengths, ngram, skip2gram, double_metaphone)

    assert isinstance(name_features, pd.Series)
    assert name_features.to_list() == [["foo"]] * len(names)

    assert gen_features.call_count == len(names)
    gen_features.assert_called_with(names.iloc[-1], lengths, ngram, skip2gram, double_metaphone)


def test_gen_name_features_examples():
    """Tests to make sure all the name features are made correctly.

    These include n-grams, skip-grams and double metaphones for a series
    made up of 'dave wilson' and 'ron bill'.
    """
    name_series = pd.Series(["dave wilson", "ron bill"])
    ground_truth_series = pd.Series(
        [
            [
                "_d",
                "da",
                "av",
                "ve",
                "e_",
                "_w",
                "wi",
                "il",
                "ls",
                "so",
                "on",
                "n_",
                "_a",
                "dv",
                "ae",
                "v_",
                "_i",
                "wl",
                "is",
                "lo",
                "sn",
                "o_",
                "TF",
                "ALSN",
                "FLSN",
            ],
            [
                "_r",
                "ro",
                "on",
                "n_",
                "_b",
                "bi",
                "il",
                "ll",
                "l_",
                "_o",
                "rn",
                "o_",
                "_i",
                "bl",
                "il",
                "l_",
                "RN",
                "PL",
            ],
        ]
    )
    name_series_output = feat.gen_name_features(
        name_series,
        ngram_length=[2],
        use_gen_ngram=True,
        use_gen_skip_grams=True,
        use_double_metaphone=True,
    )
    assert name_series_output.equals(ground_truth_series)


@given(st_sexes_series())
def test_gen_sex_features(sexes):
    """Test the sex categoriser works."""

    features = feat.gen_sex_features(sexes)

    assert isinstance(features, pd.Series)
    assert len(features) == len(sexes)
    assert features.dtype == list

    for feature, sex in zip(features, sexes):
        assert feature == [""] if sex is None else [f"sex<{sex[0].lower()}>"]


def test_gen_sex_features_example():
    """Tests to make sure the sex features function works correctly.

    These examples ensure the function takes the first letter of any
    string and converts it to sex<letter>. It also makes sure any other
    values are converted to ''.
    """
    sex_features = feat.gen_sex_features(pd.Series(["Ostrich", "Male", None, "female", 42]))
    sex_features_ground_truth = pd.Series([["sex<o>"], ["sex<m>"], [""], ["sex<f>"], [""]])
    assert sex_features_ground_truth.equals(sex_features)


@given(st_dobs_and_order_params(), st_default_dobs())
def test_gen_dateofbirth_features(dobs_dayfirst_yearfirst_format, default):
    """Test the DOB feature generator works."""

    dobs, dayfirst, yearfirst, format_ = dobs_dayfirst_yearfirst_format

    features = feat.gen_dateofbirth_features(dobs, dayfirst, yearfirst, default)

    assert isinstance(features, pd.Series)
    assert len(features) == len(dobs)
    assert features.dtype == list

    for feature, dob in zip(features, dobs):
        if dob is None:
            assert feature == default
        else:
            date = datetime.strptime(dob, format_)
            assert all(
                str(getattr(date, name)) in part
                for name, part in zip(("day", "month", "year"), feature)
            )


@pytest.mark.parametrize(
    "test_input,expected,default",
    [
        (
            pd.Series(["01/03/2012", "12/25/1993", "11/12/1960", ""]),
            pd.Series(
                [
                    ["day<01>", "month<03>", "year<2012>"],
                    ["missing"],
                    ["day<11>", "month<12>", "year<1960>"],
                    ["missing"],
                ]
            ),
            ["missing"],
        ),
        (
            pd.Series(["01/03/2012", "12/25/1993", "11/12/1960", ""]),
            pd.Series(
                [
                    ["day<01>", "month<03>", "year<2012>"],
                    "missing",
                    ["day<11>", "month<12>", "year<1960>"],
                    "missing",
                ]
            ),
            "missing",
        ),
    ],
)
def test_gen_dateofbirth_features_examples(test_input, expected, default):
    """Tests to make sure date of birth is generated correctly.

    The examples include dates and missing or invalid dates, checking
    they are replaced with the default value regardless of data type.
    """
    dob_features = feat.gen_dateofbirth_features(test_input, default=default)
    assert dob_features.equals(expected)


@given(st_fields_series(), st.sampled_from(("misc", "foo", "label")))
def test_gen_misc_features(fields, label):
    """Test the miscellaneous feature generator works."""

    features = feat.gen_misc_features(fields, label)

    assert isinstance(features, pd.Series)
    assert len(features) == len(fields)
    assert features.dtype == list

    for feature, field in zip(features, fields):
        if field is None or field == "" or (isinstance(field, float) and pd.isna(field)):
            assert feature == ""
        else:
            assert feature == [f"{label}<{str(field).casefold()}>"]


@pytest.mark.parametrize(
    "test_input,expected,label",
    [
        (pd.Series(list("abc")), pd.Series([["foo<a>"], ["foo<b>"], ["foo<c>"]]), "foo"),
        (
            pd.Series([1, 2, ["a", 1], None]),
            pd.Series([["bar<1>"], ["bar<2>"], ["bar<['a', 1]>"], ""]),
            "bar",
        ),
    ],
)
def test_gen_misc_features_examples(test_input, expected, label):
    """Tests for the miscellaneous string feature generator."""
    misc_features = feat.gen_misc_features(test_input, label=label)

    assert (misc_features).equals(expected)


@given(
    st_strings_series(),
    st.lists(st.integers(1, 3), min_size=1, max_size=2, unique=True),
    st.booleans(),
    st.sampled_from(("zz", "shingle")),
)
def test_gen_misc_shingled_features(fields, lengths, skip2grams, label):
    """Test the shingled labelled feature generator works."""

    with mock.patch("pprl.embedder.features.gen_features") as gen_features:
        gen_features.return_value = ["foo"]
        features = feat.gen_misc_shingled_features(fields, lengths, skip2grams, label)

    nrows = len(fields)
    assert isinstance(features, pd.Series)
    assert len(features) == nrows

    assert features.to_list() == [[f"{label}<foo>"]] * nrows

    assert gen_features.call_count == nrows
    last_field = fields.iloc[-1] or ""
    gen_features.assert_called_with(
        last_field, ngram_length=lengths, use_gen_skip_grams=skip2grams
    )


@pytest.mark.parametrize(
    "test_input,expected,ngram_length",
    [
        (
            pd.Series(["russ abbott", "terry wogan"]),
            pd.Series(
                [
                    ["zz<_russ_>", "zz<_abbot>", "zz<abbott>", "zz<bbott_>"],
                    ["zz<_terry>", "zz<terry_>", "zz<_wogan>", "zz<wogan_>"],
                ]
            ),
            [6],
        ),
        (
            pd.Series(["ab", "cd", "ef"]),
            pd.Series(
                [
                    ["zz<a>", "zz<b>", "zz<_a>", "zz<ab>", "zz<b_>"],
                    ["zz<c>", "zz<d>", "zz<_c>", "zz<cd>", "zz<d_>"],
                    ["zz<e>", "zz<f>", "zz<_e>", "zz<ef>", "zz<f_>"],
                ]
            ),
            [1, 2],
        ),
    ],
)
def test_gen_misc_shingled_features_examples(test_input, expected, ngram_length):
    """Tests for the miscellaneous shingled feature generator."""
    misc_features = feat.gen_misc_shingled_features(test_input, ngram_length=ngram_length)

    assert (misc_features).equals(expected)
