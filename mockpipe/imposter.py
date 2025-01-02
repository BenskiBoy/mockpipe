from typing import List, Union
from enum import Enum
import ast
import random
import time
import re

from faker import Faker
import faker_commerce

from .exceptions import InvalidValueError


fake = Faker("en_US")
fake.add_provider(faker_commerce.Provider)
random.seed(int(time.time()))
Faker.seed(random.randint(0, 10000))


class ImposterResult:
    """
    Parent class for all imposter results.
    For the simple case of inserting a dummy value, we'd just have to return a value.
    However, we also want to be able to return a value from a table, or increment a value that is the result of a query.
    This is what these and the child classes are for.
    """

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.__dict__})"


class ImposterDirectResult(ImposterResult):
    """Direct result from faker method"""

    def __init__(self, value, type: str = None):
        self.value = value
        self.type = type  # type of value, static, imposter, etc. (for debugging)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.__dict__})"

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ImposterDirectResult):
            return False
        return self.value == value.value and self.type == value.type


class ImposterLookupResult(ImposterResult):
    """Custom faker method to lookup result from table"""

    def __init__(self, table: str, field: str, default_val: str):
        self.table = table
        self.field = field
        self.default_val = default_val

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.__dict__})"


class ImposterIncrementResult(ImposterResult):
    """Custom faker method to perform an auto increment value"""

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.__dict__})"


class ImposterType(Enum):
    STATIC = "static"  # custom static value
    INCREMENT = "increment"  # custom increment value
    TABLE_RANDOM = "table_random"  # custom table random value
    INHERIT = "inherit"  # inherit from previous result
    FAKER = "faker"  # faker method

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ImposterType):
            return False
        return self.value == value.value


class Imposter:
    """Imposter class used to either generate a value or lookup a value from a table"""

    # TODO: Make sub classes for faker types that inherit from parent Imposter

    CUSTOM_METHODS = ["table_random", "static", "increment"]
    STATIC_REGEX_CHECK = r"static\((.*?)\)"
    STATIC_REGEX_EXTRACT = r"static\(.*?\)"
    INCREMENT_REGEX_CHECK = r"increment"
    INHERIT_REGEX_CHECK = r"inherit"
    TABLE_RANDOM_REGEX_EXTRACT = r"table_random\(.*?, *.*?, *.*?\)"
    TABLE_RANDOM_REGEX_CHECK = r"table_random\((.*?), *(.*?), *(.*?)\)"

    STATIC_LOOKUP = {
        "true": True,
        "false": False,
        "null": None,
        "None": None,
    }

    def __init__(
        self,
        value: str,
        arguments: Union[List[str], List[int]] = [],
        field_name: str = "",
    ) -> None:
        self.value = value.replace(
            "'", '"'
        )  # replace single quotes with double quotes, makes consistent with action parsing
        self.arguments = arguments
        self.field_name = field_name
        if self.is_type(value) == False:
            raise InvalidValueError("Imposter value must be valid faker method")

        if self.is_custom_method(value):
            self.is_custom = True
        else:
            self.is_custom = False

        if self.is_static(self.value):
            self.imposter_type = ImposterType.STATIC
        elif self.is_increment(self.value):
            self.imposter_type = ImposterType.INCREMENT
        elif self.is_table_random(self.value):
            self.imposter_type = ImposterType.TABLE_RANDOM
        elif self.is_inherit(self.value):
            self.imposter_type = ImposterType.INHERIT
        else:
            self.imposter_type = ImposterType.FAKER

    def _eval_static(self) -> ImposterDirectResult:
        match = re.match(Imposter.STATIC_REGEX_CHECK, self.value)
        if not match:
            raise InvalidValueError(f"Invalid static value - {self.value}")
        result = match.group(1)
        if result in Imposter.STATIC_LOOKUP:
            return ImposterDirectResult(Imposter.STATIC_LOOKUP[result], "STATIC")
        if result.isdigit():
            return ImposterDirectResult(int(result), "STATIC")
        if result.replace(".", "", 1).isdigit():
            return ImposterDirectResult(float(result), "STATIC")
        if result[0] == '"' and result[-1] == '"':
            return ImposterDirectResult(result[1:-1], "STATIC")
        else:
            raise InvalidValueError(f"Invalid static value - {self.value}")

    def _eval_increment(self) -> ImposterLookupResult:
        return ImposterIncrementResult()

    def _eval_table_random(self) -> ImposterLookupResult:
        match = re.match(Imposter.TABLE_RANDOM_REGEX_CHECK, self.value)
        if match:
            table = match.group(1)
            field = match.group(2)
            value = match.group(3)
            return ImposterLookupResult(table, field, value)
        else:
            raise InvalidValueError(f"Invalid table_random value - {self.value}")

    def _eval_faker(self) -> ImposterDirectResult:
        # TODO: The handling of the arguments is questionable, should mostly work for now, but be mindful there may
        # be issues here and a great spot to refactor

        # if there's a defition of a set or something that requires a ast.literal_eval
        requires_lit = False
        if self.arguments:
            for arg in self.arguments:
                if not isinstance(arg, (str)):
                    continue
                if "(" in arg or "," in arg:
                    requires_lit = True

        if requires_lit:
            lits = [
                ast.literal_eval(arg) if isinstance(arg, str) else arg
                for arg in self.arguments
            ]
            val = getattr(fake, self.value.replace("fake.", ""))(*lits)
            if isinstance(val, str):
                val = val.replace("'", "\\'")
            return ImposterDirectResult(val, "FAKER")
        elif self.arguments:
            val = getattr(fake, self.value.replace("fake.", ""))(*self.arguments)
            if isinstance(val, str):
                val = val.replace("'", "\\'")
            return ImposterDirectResult(val, "FAKER")
        else:
            val = getattr(fake, self.value.replace("fake.", ""))()
            if isinstance(val, str):
                val = val.replace("'", "\\'")
            return ImposterDirectResult(val, "FAKER")

    def evaluate(self):
        if Imposter.is_static(self.value):
            return self._eval_static()
        if Imposter.is_increment(self.value):
            return self._eval_increment()
        if Imposter.is_table_random(self.value):
            return self._eval_table_random()
        return self._eval_faker()

    @classmethod
    def is_static(cls, value: str) -> bool:
        if re.match(Imposter.STATIC_REGEX_EXTRACT, value):
            return True
        return False

    @classmethod
    def is_increment(cls, value: str) -> bool:
        if re.match(Imposter.INCREMENT_REGEX_CHECK, value):
            return True
        return False

    @classmethod
    def is_inherit(cls, value: str) -> bool:
        if re.match(Imposter.INHERIT_REGEX_CHECK, value):
            return True
        return False

    @classmethod
    def is_table_random(cls, value: str) -> bool:
        if re.match(Imposter.TABLE_RANDOM_REGEX_EXTRACT, value):
            return True
        return False

    @classmethod
    def is_custom_method(cls, value: str) -> bool:
        if (
            Imposter.is_static(value)
            or Imposter.is_increment(value)
            or Imposter.is_table_random(value)
            or Imposter.is_inherit(value)
        ):
            return True
        return False

    @classmethod
    def is_type(cls, value: str):
        faker_methods = [meth for meth in dir(fake) if meth[0] != "_"]
        if value.replace("fake.", "").split("(")[0] in faker_methods:
            return True
        if not cls.is_custom_method(value):
            raise InvalidValueError(
                f"Imposter value must be valid faker method, got - {value}"
            )
        return True

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Imposter):
            return False
        return (
            self.value == value.value
            and self.arguments == value.arguments
            and self.field_name == value.field_name
            and self.imposter_type == value.imposter_type
        )
