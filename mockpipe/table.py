from typing import List, Dict
import logging

from .exceptions import InvalidValueError

from .field import Field
from .imposter import (
    ImposterResult,
    ImposterDirectResult,
    ImposterLookupResult,
    ImposterIncrementResult,
    ImposterType,
    Imposter,
)
from .action import Action, Set, Create, Remove
from .db_connector import (
    Statement,
    SQLStatement,
    DirectStatement,
    ActionStatementCollection,
    StatementResult,
)


logger = logging.getLogger()


class Table:
    """Table class to represent a table in the database, with fields and actions to perform on the table"""

    def __init__(
        self, table_name: str, fields: Dict[str, Field], actions: Dict[str, Action]
    ):
        self.table_name = table_name
        self.fields = fields
        self.fields.update(
            {
                "change_token": Field(
                    "change_token", "int", "increment"
                ),  # used as a cdc token to track changes
                "change_type": Field(
                    "change_type", "string", 'static("I")'
                ),  # used as a flag to track change type (D, U, I)
            }
        )
        self.actions = actions

    def get_action_by_name(self, action_name: str) -> Action:
        return self.actions[action_name]

    def generate_count_str(self, table: str) -> str:
        """Generate a count query for a table

        Args:
            table (str): table name

        Returns:
            str: SQL query
        """
        return f"""select count(*) as cnt from {table} where change_type != 'D';"""

    def generate_random_lookup_str(
        self, table: str, field: str, default_val: str = "1"
    ) -> str:
        """Generate a random lookup query for a table and field, with a default value of 1
            Will also handle for empty table and deleted records

        Args:
            table (str): table name
            field (str): field to perform random look of
            default_val (str, optional): default value if table is empty. Defaults to ""

        Returns:
            str: SQL query
        """
        return f"""select {field} from {table} where change_type != 'D' using sample 1 union all (select '{default_val}' as {field} order by {field} desc)"""  # handles for empty table and filters deleted records

    def generate_increment_str(self, table: str, field: str) -> str:
        """Gets the max of a field and increments it by 1, used for auto incrementing fields

        Args:
            table (str): table name
            field (str): field to get autoincrement of.

        Returns:
            str: SQL query
        """
        return f"""select coalesce((max({field}) + 1), 1) as inc from {table};"""  # not filtering out deleted records as we don't want to reuse the deleted record's id

    def genereate_create_table_str(self) -> str:
        """generate DDL

        Returns:
            str: SQL query
        """
        pks_fields = [field.name for field in self.fields.values() if field.is_pk]
        pk_str = ""
        if len(pks_fields) != 0:
            pk_str = f", PRIMARY KEY ({', '.join(pks_fields)})"

        return f"""
        CREATE TABLE if not exists {self.table_name}(
            {', '.join(' '.join([field.name, field.type]) for field in self.fields.values())}{pk_str});
        """

    def evaluate_imposter(
        self, imposter: Imposter, action_results: List[StatementResult] = []
    ) -> Statement:
        """Evaluate the imposter and return the appropriate Statement type

        Args:
            imposter (Imposter): Imposter to evaluate
            action_results (List[StatementResult], optional): results from previous action performed if there's an inherit field to evaluate. Defaults to [].

        Raises:
            InvalidValueError: In the event that there are no previous action results for an inherit imposter
            NotImplementedError: If the imposter type is not supported

        Returns:
            Statement: Resulting statement
        """

        if imposter.imposter_type == ImposterType.INHERIT:

            if len(action_results) == 0:
                raise InvalidValueError(
                    f"No previous action results for inherit imposter {imposter.field_name}"
                )

            source_column = action_results[-1].action.effect_fields[imposter.field_name]
            prev_result_row = action_results[-1].result_set[0]

            return DirectStatement(f"{prev_result_row[source_column]}")

        result = imposter.evaluate()

        if isinstance(result, ImposterDirectResult):
            return DirectStatement(result.value)

        elif isinstance(result, ImposterLookupResult):
            return SQLStatement(
                self.generate_random_lookup_str(
                    result.table, result.field, result.default_val
                ),
                result.field,
            )

        elif isinstance(result, ImposterIncrementResult):
            return SQLStatement(
                self.generate_increment_str(self.table_name, imposter.field_name), "inc"
            )

        else:
            raise NotImplementedError("Unsupported imposter type")

    def generate_insert(
        self, action: Create, action_results: List[StatementResult]
    ) -> List[Statement]:
        """Generate List of statements for insert
        Returns:
            List[Statement]: List of Statemet objects
        """
        result_values = []
        for field in self.fields.values():
            result_values.append(DirectStatement(f"'"))
            result_values.append(self.evaluate_imposter(field.imposter, action_results))
            result_values.append(
                DirectStatement(
                    "', " if field != list(self.fields.values())[-1] else "'"
                )
            )
        return ActionStatementCollection(
            [DirectStatement(f"INSERT INTO {self.table_name} VALUES (")]
            + result_values
            + [DirectStatement(");")],
            action,
        )

    def generate_set(
        self, action: Set, action_results: List[StatementResult]
    ) -> List[Statement]:
        """Generate List of statements for set
        Args:
            action (Set): Action to perform
        Returns:
            List[Statement]: List of Statement objects
        """

        result_values = [
            DirectStatement(f"UPDATE {self.table_name} set {action.field.name} = '")
        ]
        result_values.append(self.evaluate_imposter(action.value, action_results))

        if action.where_clause is not None:
            return ActionStatementCollection(
                result_values
                + [
                    DirectStatement(
                        f"', change_token = (SELECT MAX(change_token) + 1 FROM {self.table_name}), change_type = 'U' WHERE {action.where_table}.{action.where_field} {action.where_condition} '"
                    ),
                    self.evaluate_imposter(action.where_value, action_results),
                    DirectStatement("' AND change_type != 'D';"),
                ],
                action,
            )
        else:
            return ActionStatementCollection(
                result_values
                + [
                    DirectStatement(
                        f"', change_token = (SELECT MAX(change_token) + 1 FROM {self.table_name}), change_type = 'U' WHERE change_type != 'D';"
                    )
                ],
                action,
            )

    def generate_delete(
        self, action: Remove, action_results: List[StatementResult]
    ) -> List[Statement]:
        """Generate List of statements for delete
        Args:
            action (Remove): Action to perform
        Returns:
            List[Statement]: List of Statement objects
        """

        return ActionStatementCollection(
            [
                DirectStatement(
                    f"UPDATE {self.table_name} SET change_token = (SELECT MAX(change_token) + 1 FROM {self.table_name}), change_type = 'D' WHERE {action.where_table}.{action.where_field} {action.where_condition} '"
                ),
                self.evaluate_imposter(action.where_value, action_results),
                DirectStatement(
                    "' AND change_type != 'D';"
                ),  # probably not need, but will leave in for now
            ],
            action,
        )

    def get_action_statement(
        self, action: Action, action_results: List[StatementResult]
    ) -> ActionStatementCollection:
        """Perform a random action on a table

        Raises:
            NotImplementedError: if action is not implemented

        Returns:
            List[Statement]: List of Statement objects to be executed on the database
        """
        if isinstance(action, Set):
            return self.generate_set(action, action_results)
        elif isinstance(action, Create):
            return self.generate_insert(action, action_results)
        elif isinstance(action, Remove):
            return self.generate_delete(action, action_results)
        else:
            raise NotImplementedError()

    def __str__(self):
        return f"{self.table_name} {self.fields} {self.actions}"

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"
