from typing import Dict
from .imposter import Imposter

from .exceptions import InvalidValueError, validate_keys


class Field:
    VALID_FIELD_TYPES = ["string", "int", "float", "boolean"]

    def __init__(
        self,
        name: str,
        type: str,
        imposter: str,
        is_pk: bool = False,
        table: str = "",
        arguments: list = [],
    ) -> None:
        """A field is a column in a table.

        Args:
            name (str): field name as it will appear in the table
            type (str): data type, valid values are string, int, float, boolean
            imposter (str): imposter method to generate data for the field e.g. `imposter.name()`
            is_pk (bool, optional): whether a primary key. Defaults to False.
            table (str, optional): _description_. Defaults to ''.

        Raises:
            InvalidValueError: _description_
        """
        self.name = name
        self.type = type
        self.is_pk = is_pk
        if Imposter.is_type(imposter) == False:
            raise InvalidValueError(
                f"Imposter value `{imposter}` is invalid for field `{name}` in table `{table}`"
            )
        self.imposter = Imposter(imposter, arguments, name)

    def evaluate(self):
        return self.imposter.evaluate()

    @classmethod
    def is_valid(self, attribs: Dict, table_name: str):
        validate_keys(
            attribs,
            ["name", "type", "value"],
            ["is_pk", "arguments"],
            f"Table: {table_name} - Field: {attribs.get('name', '')}",
        )
        if attribs["type"] not in Field.VALID_FIELD_TYPES:
            raise InvalidValueError(
                f"Field type must be string, int, float, or bool - got {attribs['type']}"
            )
        if Imposter.is_type(attribs["value"]) == False:
            raise InvalidValueError("Imposter value is invalid")

        if attribs["value"] == "increment" and attribs["type"] != "int":
            raise InvalidValueError("Increment value must be of type int")

        return True

    def __str__(self):
        return f"{self.name} {self.type} {self.imposter}"

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Field):
            return False
        return (
            self.name == value.name
            and self.type == value.type
            and self.imposter == value.imposter
            and self.is_pk == value.is_pk
        )
