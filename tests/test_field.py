import pytest
from unittest.mock import patch
from mockpipe.field import Field
from mockpipe.imposter import Imposter, ImposterDirectResult
from mockpipe.exceptions import InvalidValueError

from mockpipe.exceptions import MissingMandatoryConfigSetting, UnexpectedConfigSetting


def test_field_init():
    field = Field("name", "string", "fake.name")
    assert field.name == "name"
    assert field.type == "string"
    assert field.imposter == Imposter("fake.name", [], "name")
    assert field.is_pk == False


@patch("mockpipe.imposter.fake.name", return_value="Joey Joe Joe Shabadoo")
def test_field_evaluate(mock_fake_name):
    field = Field("some_name", "string", "fake.name")
    assert field.evaluate() == ImposterDirectResult(
        value="Joey Joe Joe Shabadoo", type="FAKER"
    )


def test_field_is_valid():
    with pytest.raises(MissingMandatoryConfigSetting):
        Field.is_valid(attribs={"name": "John"}, table_name="users")

    with pytest.raises(UnexpectedConfigSetting):
        Field.is_valid(
            attribs={
                "name": "John",
                "type": "string",
                "value": "fake.name",
                "something": "else",
            },
            table_name="users",
        )

    with pytest.raises(InvalidValueError):
        Field.is_valid(
            attribs={"name": "John", "type": "not_a_valid_type", "value": "fake.name"},
            table_name="users",
        )

    assert Field.is_valid(
        attribs={"name": "John", "type": "string", "value": "fake.name"},
        table_name="users",
    )


def test_non_int_increment():
    with pytest.raises(InvalidValueError):
        Field.is_valid({"name": "foo", "type": "string", "value": "increment"}, "foo")
