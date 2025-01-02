from typing import List, Union, Dict
import logging

from pathlib import Path
import duckdb

from .action import Action

logger = logging.getLogger()


class Statement:
    def __init__(
        self,
        value: str = None,
    ):
        self.value = value

    def __str__(self):
        return f"{self.value}"

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"

    def __eq__(self, other):
        return self.value == other.value


class SQLStatement(Statement):
    """Represents a SQL query to be executed for forming part of a query.
    Additionally, result field name the required value will be returned within
    """

    def __init__(self, value: str = None, result_field: str = None):
        self.result_field = result_field
        super().__init__(value)

    def __eq__(self, other):
        return self.value == other.value and self.result_field == other.result_field


class DirectStatement(Statement):
    """Represents a direct value to be used in a query"""

    def __init__(self, value: str = None):
        super().__init__(value)

    def __eq__(self, value: object) -> bool:
        return super().__eq__(value)


class ActionStatementCollection:
    """List of statements to run, as well as the action class"""

    def __init__(self, statements: List[Statement], action: Action):
        self.statements = statements
        self.action = action

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"

    def __eq__(self, other):
        return self.statements == other.statements and self.action == other.action


class StatementResult:
    """Result of a query"""

    def __init__(
        self, result_set: List[Dict], table_name: str, action: Action, effect_count: int
    ):
        self.result_set = result_set
        self.table_name = table_name
        self.action = action

        # How many times the action was executed
        self.effect_count = effect_count

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"


class DBConnector:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = duckdb.connect(str(db_path))

    def get_latest_rows(self, table_name: str) -> List[Dict]:
        """Returns the most recently modified row(s)

        Args:
            table_name (str): table name to extract the most recent values from

        Returns:
            List[Dict]: list of most recently modified records
        """
        return (
            self.conn.sql(
                f"SELECT * FROM {table_name} where change_token = (select max(change_token) from {table_name})"
            )
            .to_df()
            .to_dict(orient="records")
        )

    def get_max_change_token(self, table_name: str) -> int:
        """Select max change token from the table

        Args:
            table_name (str):  table name to extract the greatest change record token from

        Returns:
            int: max change token value
        """
        return (
            self.conn.sql(f"SELECT max(change_token) as change_token from {table_name}")
            .to_df()
            .to_dict()["change_token"][0]
        )

    def execute_sql(self, query: str, result_field: str = None) -> Union[Dict, str]:
        """Execute SQL statement and optionally return a specific field

        Args:
            query (str): query to execute
            result_field (str, optional): field to extract from. Defaults to None.

        Returns:
            Union[Dict, str]: value or return value
        """
        logging.info(f"Executing query: {query}")
        res = self.conn.sql(query)
        if result_field is None:
            if res:
                return res.to_df().to_dict()
            else:
                return {}
        return str(self.conn.sql(query).to_df().to_dict()[result_field][0])

    def execute(self, statements: List[Statement]) -> Union[Dict, str]:
        """Execute a list of statements

        Args:
            statements (List[Statement]): List of statements to execute

        Returns:
            _type_: _description_
        """
        final_result = ""
        for statement in statements:
            if isinstance(statement, SQLStatement):
                final_result += self.execute_sql(
                    statement.value, statement.result_field
                )
            elif isinstance(statement, DirectStatement):
                final_result += str(statement.value)

        try:
            return self.execute_sql(final_result)
        except duckdb.ParserException as e:
            logger.error(f"Error executing query: {final_result}")
            raise e
