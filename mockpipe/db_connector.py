from typing import List, Optional, Union, Dict
import logging

from pathlib import Path
import duckdb

from .action import Action

logger = logging.getLogger()

StatementValue = Union[str, int, float, bool]


class Statement:
    def __init__(
        self,
        value: Optional[StatementValue] = None,
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

    def __init__(self, value: str, result_field: str):
        self.result_field = result_field
        super().__init__(value)

    def __eq__(self, other):
        return self.value == other.value and self.result_field == other.result_field


class DirectStatement(Statement):
    """Represents a direct value to be used in a query"""

    def __init__(self, value: Optional[StatementValue] = None):
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

    def get_all_rows(
        self, table_name: str, include_deleted: bool = False
    ) -> List[Dict]:
        """Returns every row currently in the table, for a full snapshot export

        Args:
            table_name (str): table name to extract rows from
            include_deleted (bool, optional): include soft-deleted rows. Defaults to False.

        Returns:
            List[Dict]: list of all records in the table
        """
        where_clause = "" if include_deleted else "where change_type != 'D'"
        return (
            self.conn.sql(f"SELECT * FROM {table_name} {where_clause}")
            .to_df()
            .to_dict(orient="records")
        )

    def get_max_change_token(self, table_name: str) -> Optional[int]:
        """Select max change token from the table

        Args:
            table_name (str):  table name to extract the greatest change record token from

        Returns:
            Optional[int]: max change token value, or None if the table has no rows yet
        """
        value = (
            self.conn.sql(f"SELECT max(change_token) as change_token from {table_name}")
            .to_df()
            .to_dict()["change_token"][0]
        )
        # max() over an empty table is SQL NULL, which pandas surfaces as NaN.
        # NaN is never equal to itself, so callers comparing old vs new values
        # need a real None here instead, or "still empty" reads as "changed".
        if value != value:
            return None
        return int(value)

    def execute_sql(
        self, query: str, result_field: Optional[str] = None
    ) -> Union[Dict, str]:
        """Execute SQL statement and optionally return a specific field

        Args:
            query (str): query to execute
            result_field (str, optional): field to extract from. Defaults to None.

        Returns:
            Union[Dict, str]: value or return value
        """
        logger.info(f"Executing query: {query}")
        try:
            res = self.conn.sql(query)
        except duckdb.ParserException as e:
            logger.error(f"Error executing query: {query}")
            raise e

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
            Union[Dict, str]: result of executing the concatenated statements as one query
        """
        final_result = ""
        for statement in statements:
            if isinstance(statement, SQLStatement):
                assert isinstance(statement.value, str)
                sql_result = self.execute_sql(statement.value, statement.result_field)
                assert isinstance(
                    sql_result, str
                ), f"Expected a scalar result for {statement.value!r}, got {sql_result!r}"
                final_result += sql_result
            elif isinstance(statement, DirectStatement):
                final_result += str(statement.value)

        try:
            return self.execute_sql(final_result)
        except duckdb.ParserException as e:
            logger.error(f"Error executing query: {final_result}")
            raise e

    def create_metadata_table(self, table_name: str):
        """Create a metadata table to track current iteration step, config, and other relevant information.

        Args:
            table_name (str): table name to create the metadata table for
        """

        self.conn.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY,
            change_token INTEGER,
            action TEXT,
            action_id TEXT,
            is_deleted BOOLEAN DEFAULT FALSE
        );
        """
        )
