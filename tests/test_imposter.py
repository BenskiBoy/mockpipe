import pytest
from unittest.mock import patch
from mockpipe.imposter import (
    Imposter,
    ImposterDirectResult,
    ImposterLookupResult,
    ImposterIncrementResult,
)


@pytest.fixture
def imposter_static_true():
    return Imposter("static(true)")


@pytest.fixture
def imposter_increment():
    return Imposter("increment")


@pytest.fixture
def imposter_table_random():
    return Imposter("table_random(table_name, field_name, default_value)")


@pytest.fixture
def imposter_faker():
    return Imposter("fake.phone_number")


@pytest.fixture
def imposter_faker_name():
    return Imposter("fake.name")


def test_eval_static(imposter_static_true):
    result = imposter_static_true._eval_static()

    assert isinstance(result, ImposterDirectResult)
    assert result.value == True


def test_eval_increment(imposter_increment):
    result = imposter_increment._eval_increment()

    assert isinstance(result, ImposterIncrementResult)


def test_eval_table_random(imposter_table_random):
    result = imposter_table_random._eval_table_random()

    assert isinstance(result, ImposterLookupResult)
    assert result.table == "table_name"
    assert result.field == "field_name"
    assert result.default_val == "default_value"


@patch("mockpipe.imposter.fake.phone_number", return_value="fake_value")
def test_eval_faker(mock_fake, imposter_faker):
    result = imposter_faker._eval_faker()

    assert isinstance(result, ImposterDirectResult)
    assert result.value == "fake_value"


@patch("mockpipe.imposter.fake.name", return_value="smith's")
def test_eval_faker_quoted_string(mock_fake, imposter_faker_name):
    result = imposter_faker_name._eval_faker()

    assert isinstance(result, ImposterDirectResult)
    assert result.value == "smith\\'s"


def test_evaluate_static(imposter_static_true):
    result = imposter_static_true.evaluate()

    assert isinstance(result, ImposterDirectResult)
    assert result.value == True


def test_evaluate_increment():
    imp = Imposter(value="increment", arguments=[], field_name="field_name")
    result = imp.evaluate()

    assert isinstance(result, ImposterIncrementResult)
    assert imp.field_name == "field_name"
    assert imp.is_custom == True


def test_evaluate_table_random(imposter_table_random):
    result = imposter_table_random.evaluate()
    assert isinstance(result, ImposterLookupResult)
    assert result.table == "table_name"
    assert result.field == "field_name"
    assert result.default_val == "default_value"
