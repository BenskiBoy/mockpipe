from typing import Dict, List, Union
import random

from .exceptions import InvalidValueError, validate_keys
from .field import Field
from .imposter import Imposter


class EffectCount:
    def __init__(self, effect_count: str):
        self.single_value = None
        self.range_values = None
        self.inherit = False

        # default effect count to 1 if not set
        if not effect_count:
            effect_count = 1

        effect_count = effect_count.strip().lower()
        if effect_count == "inherit":
            self.inherit = True
        elif "," in effect_count:
            min_val, max_val = map(int, effect_count.split(","))
            self.range_values = (min_val, max_val)
        else:
            self.single_value = int(effect_count)

    def get_count(self) -> int:
        if self.inherit:
            return "INHERIT"
        if self.range_values:
            return random.randint(self.range_values[0], self.range_values[1])
        return self.single_value

    def __repr__(self):
        if self.inherit:
            return "EffectCount(inherit=True)"
        if self.range_values:
            return f"EffectCount(range_values={self.range_values})"
        return f"EffectCount(single_value={self.single_value})"


class Action:
    """Parent class for all actions. Action is performs an action on a table"""

    REQUIRED_CONFIG_KEYS = ["name", "action", "frequency"]
    OPTIONAL_CONFIG_KEYS = []
    EQUALITIES = [
        "==",
        ">=",
        "<=",
        ">",
        "<",
        "!=",
    ]  # note, the order of these matters, especially for >= and <=
    ACTION_CONDITIONS = ["EFFECT_ONLY"]

    def __init__(
        self,
        name: str,
        frequency: float,
        arguments: Union[List[str], List[int]] = [],
        effect: str = None,
        effect_count: str = None,
        action_condition: str = None,
    ):
        self.name = name
        self.frequency = frequency
        self.arguments = arguments
        self.effect = effect
        self.action_condition = action_condition.upper() if action_condition else None
        # init effect fields to None
        (
            self.effect_table,
            self.effect_action,
            self.effect_count,
            self.effect_fields,
        ) = (None, None, None, {})
        if self.effect:
            self.effect_table = effect.split(".")[0].strip()
            self.effect_action = effect.split(".")[1].split("(")[0].strip()
            self.effect_fields = {}
            effect_fields = (
                effect.split(".")[1].split("(")[1].replace(")", "").split(",")
            )
            for field in effect_fields:
                field_to, field_from = field.split("=")
                self.effect_fields[field_to.strip()] = field_from.strip()

            if (
                not self.effect_table
                or not self.effect_action
                or not self.effect_fields
            ) and len(self.effect_fields) != len(effect_fields):
                raise InvalidValueError(
                    f"Invalid effect - {self.effect} - Syntax: table.action(field_from=field_to)"
                )

            # default effect count to 1 if not set
            if effect_count:
                self.effect_count = EffectCount(effect_count)
            else:
                self.effect_count = None

        if self.action_condition:
            if self.action_condition not in Action.ACTION_CONDITIONS:
                raise InvalidValueError(
                    f"Invalid action condition - {self.action_condition} - Must be one of {Action.ACTION_CONDITIONS} or not set"
                )

    def _pass_where_clause(self, where_clause: str):

        strip_ws = lambda txt: '"'.join(
            it if i % 2 else "".join(it.split())
            for i, it in enumerate(txt.split('"') if '"' in txt else txt.split("'"))
        )  # note, will replace single quotes with double quotes, this will be default behaviour for Imposter fields as well

        where_clause = strip_ws(where_clause)

        tokens = None
        for condition in Action.EQUALITIES:
            if condition in where_clause:
                tokens = where_clause.split(condition)
                self.where_condition = condition
                break
        if not tokens:
            raise InvalidValueError(f"Invalid where condition - {self.where_condition}")

        self.where_table = tokens[0].split(".")[0]
        self.where_field = tokens[0].split(".")[1]
        self.where_value = Imposter(tokens[1])

    @classmethod
    def get_type(self, attribs: Dict):
        if Create.is_valid(attribs):
            return Create
        elif Remove.is_valid(attribs):
            return Remove
        elif Set.is_valid(attribs):
            return Set
        else:
            raise NotImplementedError()

    @classmethod
    def is_valid(self, attribs: Dict):
        raise NotImplementedError()

    def __str__(self):
        return f"{self.name}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.__dict__})"


class Create(Action):
    """Create action to create a new record in the table"""

    REQUIRED_CONFIG_KEYS = Action.REQUIRED_CONFIG_KEYS
    OPTIONAL_CONFIG_KEYS = Action.OPTIONAL_CONFIG_KEYS + [
        "effect",
        "action_condition",
        "effect_count",
    ]

    def __init__(
        self,
        name: str,
        frequency: float,
        effect: str = None,
        effect_count: str = None,
        action_condition: str = None,
    ):
        super().__init__(
            name,
            frequency,
            [],
            effect,
            effect_count,
            action_condition,
        )

    @classmethod
    def is_valid(self, attribs: Dict, table_name: str = "") -> bool:
        if attribs["action"].lower() != "create":
            return False
        validate_keys(
            dictionary=attribs,
            required_keys=Create.REQUIRED_CONFIG_KEYS,
            optional_keys=Create.OPTIONAL_CONFIG_KEYS,
            additional_context=f"Create action requires {' and '.join(Create.REQUIRED_CONFIG_KEYS)} - Table `{table_name}` - Action `{attribs.get('name', '')}`",
        )
        if not (attribs["frequency"] > 0 and attribs["frequency"] <= 1):
            raise InvalidValueError("Frequency must be between 0 and 1")
        return True


class Remove(Action):
    """Remove action to remove a record from the table"""

    REQUIRED_CONFIG_KEYS = Action.REQUIRED_CONFIG_KEYS
    OPTIONAL_CONFIG_KEYS = Action.OPTIONAL_CONFIG_KEYS + [
        "where_condition",
        "effect",
        "effect_count",
        "action_condition",
    ]

    def __init__(
        self,
        name: str,
        frequency: float,
        where_clause: str,
        effect: str = None,
        effect_count: str = None,
        action_condition: str = None,
    ):
        super().__init__(
            name,
            frequency,
            [],
            effect,
            effect_count,
            action_condition,
        )

        self.where_clause = where_clause

        if where_clause:
            self._pass_where_clause(self.where_clause)

    @classmethod
    def is_valid(self, attribs: Dict, table_name: str) -> bool:
        if attribs["action"].lower() != "remove":
            return False
        validate_keys(
            dictionary=attribs,
            required_keys=Remove.REQUIRED_CONFIG_KEYS,
            optional_keys=Remove.OPTIONAL_CONFIG_KEYS,
            additional_context=f"Remove action requires [{','.join(Create.REQUIRED_CONFIG_KEYS)}] and an optional [{','.join(Create.OPTIONAL_CONFIG_KEYS)}] - Table `{table_name}` - Action `{attribs.get('name', '')}`",
        )
        if not (attribs["frequency"] > 0 and attribs["frequency"] <= 1):
            raise InvalidValueError("Frequency must be between 0 and 1")
        return True


class Set(Action):
    """Set action to set a field to a value in the table"""

    REQUIRED_CONFIG_KEYS = Action.REQUIRED_CONFIG_KEYS + ["field", "value"]
    OPTIONAL_CONFIG_KEYS = Action.OPTIONAL_CONFIG_KEYS + [
        "where_condition",
        "arguments",
        "effect",
        "effect_count",
        "action_condition",
    ]

    def __init__(
        self,
        name: str,
        field: Field,
        value: Imposter,
        where_clause: str = None,
        frequency: float = 0.0,
        arguments: Union[List[str], List[int]] = [],
        effect: str = None,
        effect_count: str = None,
        action_condition: str = None,
    ) -> None:
        super().__init__(
            name,
            frequency,
            [],
            effect,
            effect_count,
            action_condition,
        )
        self.field = field
        self.value = value
        self.where_clause = where_clause
        self.arguments = arguments
        if where_clause:
            self._pass_where_clause(self.where_clause)

    @classmethod
    def is_valid(self, attribs: Dict, table_name: str = "") -> bool:
        if attribs["action"].lower() != "set":
            return False
        validate_keys(
            dictionary=attribs,
            required_keys=Set.REQUIRED_CONFIG_KEYS,
            optional_keys=Set.OPTIONAL_CONFIG_KEYS,
            additional_context=f"Set action requires {' and '.join(Set.REQUIRED_CONFIG_KEYS)} and an optional [{','.join(Set.OPTIONAL_CONFIG_KEYS)}] - Table `{table_name}` - Action `{attribs.get('name', '')}`",
        )
        if not (attribs["frequency"] > 0 and attribs["frequency"] <= 1):
            raise InvalidValueError("Frequency must be between 0 and 1")

        return True

    def __str__(self):
        return f"{self.name} {self.frequency} {self.field} {self.value} {self.where_condition}"

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"
