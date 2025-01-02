import time
from typing import Tuple, List
import threading
import random

from .config import Config
from .db_connector import DBConnector, ActionStatementCollection, StatementResult
from .exporter import Exporter
from .table import Table
from .action import Action


class MockPipe:
    def __init__(self, config_path: str):

        self.cnf = Config(config_path)
        self.db = DBConnector(self.cnf.db_path)
        self.exporter = Exporter(self.cnf.output_path)
        self.tables = self.cnf.load_datasets()
        self.action_results = []

        self.thread = None
        self.stop_event = threading.Event()
        self.is_running = False

        self.cnf.create_output_folders(
            [table.table_name for table in self.tables.values()]
        )

        self.max_change_token_values = {}
        for table in self.tables.values():
            result = self.db.execute_sql(
                f"select count(1) as cnt from information_schema.tables where table_name = '{table.table_name}'",
                "cnt",
            )
            if result == "0":
                self.db.execute_sql(table.genereate_create_table_str())
            self.max_change_token_values[table.table_name] = (
                self.db.get_max_change_token(table.table_name)
            )

    def start(self):
        if not self.is_running:
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._execute)
            self.thread.start()
            self.is_running = True

    def stop(self):
        if self.is_running:
            self.stop_event.set()
            self.thread.join()
            self.is_running = False

    def step(self):
        if not self.is_running:
            self._execute(True)

    def execute_action(self, table: Table, action: Action, _is_effect: bool = False):
        """Directly execute a specific action on a table. If the action is an effect action, the function will call itself with the effect action.

        Args:
            table (Table): target table
            action (Action): target action
            _is_effect (bool, optional): This function calls itself if executed action has effects. When this occurs, _is_effect set to true. Defaults to False.

        Raises:
            ValueError: In the event this function is called with an EFFECT_ONLY action, raises an error
        """

        # make sure not an effect only action. However, this function calls itself with an effect action, so allow if _is_effect
        if action.action_condition == "EFFECT_ONLY" and not _is_effect:
            raise ValueError(
                f"Cannot execute an action directly for an EFFECT_ONLY action - {table.table_name}.{action.name}"
            )

        if (
            len(self.action_results) == 0
            or not self.action_results[-1].action.effect_count
        ):
            count = 1

        else:
            count = self.action_results[-1].action.effect_count.get_count()
            if count == "INHERIT":
                count = self.action_results[-1].effect_count

        results = []
        for cnt in range(count):
            results.append(
                (
                    table.get_action_statement(action, self.action_results),
                    table.table_name,
                    count,
                )
            )
        for res in results:
            self._handle_change(*res)

        if self.action_results[-1].action.effect:
            self.execute_action(
                self.tables[self.action_results[-1].action.effect_table],
                self.tables[self.action_results[-1].action.effect_table].actions[
                    self.action_results[-1].action.effect_action
                ],
                _is_effect=True,
            )

    def _handle_change(
        self,
        action_statement_collection: ActionStatementCollection,
        table_name: str,
        effect_count: int,  # stored in the action_results, but not used. To keep history of the previous effect_count
    ):
        self.db.execute(action_statement_collection.statements)
        max_change_token_value = self.db.get_latest_rows(table_name)
        if max_change_token_value != self.max_change_token_values[table_name]:
            self.max_change_token_values[table_name] = max_change_token_value
            latest_rows = self.db.get_latest_rows(table_name)

            self.action_results.append(
                StatementResult(
                    latest_rows,
                    table_name,
                    action_statement_collection.action,
                    effect_count,
                )
            )

            # Limit the number of action results stored, remove the oldest.
            # This is to prevent memory issues when running for a long time.
            if len(self.action_results) > self.cnf.action_results_limit:
                self.action_results.pop(0)

            self.exporter.export(table_name, latest_rows, self.cnf.output_format)

        if self.cnf.delete_behaviour == "HARD":
            for table in self.tables.values():
                self.db.execute_sql(
                    f"delete from {table.table_name} where change_type = 'D'"
                )

    def _execute(self, run_once: bool = False):
        while not self.stop_event.is_set():
            for table in self.tables.values():
                for res in self._perform_iteration():
                    self._handle_change(*res)
                    if run_once:
                        return
                    time.sleep(self.cnf.inter_action_delay)

    def _perform_iteration(self) -> List[Tuple[ActionStatementCollection, str]]:
        """Perform an iteration of actions. If there is no previous action, a random action is selected.
        If there is a previous action which has an effect, the effect action is selected.
        Note: If there is a effect_count (i.e. the number of times an effect action is performed), multiple ActionStatements will be returned.
        Returns:
            List[Tuple[ActionStatementCollection, str]]: _description_
        """
        # Get all tables that have actions that are not effect only or missing an action
        available_tables = [
            table
            for table in self.tables.values()
            if any(
                action.action_condition != "EFFECT_ONLY"
                for action in table.actions.values()
            )
        ]

        if (
            len(self.action_results) == 0
            or not self.action_results[-1].action.effect_count
        ):
            table = random.choice(available_tables)
            action = random.choice(
                [
                    action
                    for action in table.actions.values()
                    if action.action_condition != "EFFECT_ONLY"
                ]
            )

            return [
                (
                    table.get_action_statement(action, self.action_results),
                    table.table_name,
                    1,
                )
            ]

        # If there is a previous action with an effect,
        # select the effect action and run according to effect_count or effect_count_random_min/max
        else:
            results = []

            count = self.action_results[-1].action.effect_count.get_count()
            if count == "INHERIT":
                count = self.action_results[-1].effect_count

            for cnt in range(count):
                table = self.tables[self.action_results[-1].action.effect_table]
                action = table.actions[self.action_results[-1].action.effect_action]

                results.append(
                    (
                        table.get_action_statement(action, self.action_results),
                        table.table_name,
                        count,
                    )
                )
        return results

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"
