import time
from typing import Dict, Optional, Tuple, List, Union
import threading
import random

from .config import Config
from .db_connector import DBConnector, ActionStatementCollection, StatementResult
from .exporter import Exporter
from .table import Table
from .action import Action, Remove


class MockPipe:
    METADATA_TABLE_NAME = "_mockpipe_metadata"

    def __init__(self, config_path: Union[str, dict]):

        self.cnf = Config(config_path)
        self.db = DBConnector(self.cnf.db_path, seed=self.cnf.seed)
        self.exporter = Exporter(
            self.cnf.output_path,
            {
                "url": self.cnf.output_url,
                "topic": self.cnf.output_topic,
                "bootstrap_servers": self.cnf.output_bootstrap_servers,
            },
        )
        self.tables = self.cnf.load_datasets()
        self.action_results: List[StatementResult] = []
        # Buffers changed rows per table until output.batch_size is reached,
        # instead of writing one export file per single change. Flushed by
        # flush_exports() - called automatically from stop(), but call it
        # yourself if you only ever use step() without start()/stop().
        self._export_buffers: Dict[str, List[Dict]] = {
            table_name: [] for table_name in self.tables
        }

        self.thread = None
        self.stop_event = threading.Event()
        self.is_running = False
        # Guards action_results/max_change_token_values/db access, since
        # execute_action() can be called directly while the background
        # thread from start() is also running. Reentrant because
        # execute_action() recurses into itself for effect chains.
        self._lock = threading.RLock()

        if self.cnf.output_format not in ("webhook", "kafka"):
            self.cnf.create_output_folders(
                [table.table_name for table in self.tables.values()]
            )

        self.max_change_token_values: Dict[str, Optional[int]] = {}
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

        # The metadata table persists across restarts (it lives in the same
        # db file), so re-opening the same db_path resumes the iteration
        # count instead of restarting full_load's schedule from zero.
        self.db.create_metadata_table(self.METADATA_TABLE_NAME)
        metadata_row_count = self.db.execute_sql(
            f"select count(1) as cnt from {self.METADATA_TABLE_NAME}", "cnt"
        )
        assert isinstance(metadata_row_count, str)
        self.iteration_count = int(metadata_row_count)

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
        self.flush_exports()
        self.exporter.close()

    def flush_exports(self):
        """Write out any buffered rows that haven't reached output.batch_size yet.

        Called automatically by stop(). Call this yourself if you only ever
        use step() without start()/stop() - otherwise a partial batch at the
        end of your run is never written out.
        """
        with self._lock:
            for table_name, buffer in self._export_buffers.items():
                if buffer:
                    self.exporter.export(table_name, buffer, self.cnf.output_format)
                    self._export_buffers[table_name] = []

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

        with self._lock:
            if (
                len(self.action_results) == 0
                or not self.action_results[-1].action.effect_count
            ):
                count = 1

            else:
                resolved_count = self.action_results[-1].action.effect_count.get_count()
                if resolved_count == "INHERIT":
                    resolved_count = self.action_results[-1].effect_count
                assert isinstance(resolved_count, int)
                count = resolved_count

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

            if action.effect:
                assert (
                    action.effect_table is not None and action.effect_action is not None
                )
                self.execute_action(
                    self.tables[action.effect_table],
                    self.tables[action.effect_table].actions[action.effect_action],
                    _is_effect=True,
                )

    def _handle_change(
        self,
        action_statement_collection: ActionStatementCollection,
        table_name: str,
        effect_count: int,  # stored in the action_results, but not used. To keep history of the previous effect_count
    ):
        with self._lock:
            self.db.execute(action_statement_collection.statements)
            max_change_token_value = self.db.get_max_change_token(table_name)
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

                buffer = self._export_buffers.setdefault(table_name, [])
                buffer.extend(latest_rows)
                if len(buffer) >= self.cnf.output_batch_size:
                    self.exporter.export(table_name, buffer, self.cnf.output_format)
                    self._export_buffers[table_name] = []

                is_deleted = isinstance(action_statement_collection.action, Remove)
                self.db.execute_sql(
                    f"INSERT INTO {self.METADATA_TABLE_NAME} "
                    "(id, change_token, action, action_id, is_deleted) VALUES ("
                    f"(select coalesce(max(id) + 1, 1) from {self.METADATA_TABLE_NAME}), "
                    f"{max_change_token_value}, "
                    f"'{action_statement_collection.action.name}', "
                    f"'{table_name}', "
                    f"{str(is_deleted).lower()});"
                )
                self.iteration_count += 1

                if (
                    self.cnf.full_load
                    and self.cnf.full_load_frequency > 0
                    and self.iteration_count % self.cnf.full_load_frequency == 0
                ):
                    self._perform_full_load()

            if self.cnf.delete_behaviour == "HARD":
                for table in self.tables.values():
                    self.db.execute_sql(
                        f"delete from {table.table_name} where change_type = 'D'"
                    )

    def _perform_full_load(self):
        """Export a full snapshot of every table's current rows, in addition to
        the normal incremental change stream. Triggered every full_load_frequency
        recorded changes when full_load is enabled in the config.
        """
        for table_name in self.tables:
            rows = self.db.get_all_rows(
                table_name, include_deleted=self.cnf.full_load_include_deletes
            )
            if rows:
                self.exporter.export(table_name, rows, self.cnf.output_format)

    def _execute(self, run_once: bool = False):
        while not self.stop_event.is_set():
            for table in self.tables.values():
                with self._lock:
                    iteration_results = self._perform_iteration()
                for res in iteration_results:
                    self._handle_change(*res)
                    if run_once:
                        return
                    time.sleep(self.cnf.inter_action_delay)

    def _perform_iteration(self) -> List[Tuple[ActionStatementCollection, str, int]]:
        """Perform an iteration of actions. If there is no previous action, a random action is selected.
        If there is a previous action which has an effect, the effect action is selected.
        Note: If there is a effect_count (i.e. the number of times an effect action is performed), multiple ActionStatements will be returned.
        Returns:
            List[Tuple[ActionStatementCollection, str, int]]: action statement, table name, and effect count for each action to perform
        """
        with self._lock:
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
                eligible_actions = [
                    action
                    for action in table.actions.values()
                    if action.action_condition != "EFFECT_ONLY"
                ]
                action = random.choices(
                    eligible_actions,
                    weights=[a.frequency for a in eligible_actions],
                    k=1,
                )[0]

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

                resolved_count = self.action_results[-1].action.effect_count.get_count()
                if resolved_count == "INHERIT":
                    resolved_count = self.action_results[-1].effect_count
                assert isinstance(resolved_count, int)
                count = resolved_count

                for cnt in range(count):
                    effect_table = self.action_results[-1].action.effect_table
                    effect_action = self.action_results[-1].action.effect_action
                    assert effect_table is not None and effect_action is not None
                    table = self.tables[effect_table]
                    action = table.actions[effect_action]

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
