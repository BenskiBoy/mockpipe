from typing import List, Tuple

import yaml
import os

from pathlib import Path

from .exceptions import InvalidConfigSettingError
from .table import Table
from .field import Field
from .imposter import Imposter, ImposterType
from .action import Create, Remove, Set


class Config:
    """
    Config class to load the config file and generate table objects
    """

    DELETE_BEHAVIOURS = ["HARD", "SOFT"]
    DEFAULT_ACTION_RESULTS_LIMIT = 10

    def __init__(self, config: Tuple[str, dict]):
        """Init class variables and load the config file

        Args:
            config (str): path to config file or dictionary or yaml string

        Raises:
            ValueError: if the config is invalid
        """
        if isinstance(config, dict):
            self.config = config
        elif isinstance(config, str):
            if os.path.isfile(config):
                config_file = config
                with open(config_file, "r") as file:
                    self.config = yaml.safe_load(file)
            else:
                self.config = yaml.safe_load(config)
        else:
            raise ValueError("Invalid config_path")

        self.db_path = self.config["db_path"]
        self.output_format = self.config["output"]["format"]
        self.output_path = self.config["output"]["path"]
        self.delete_behaviour = self.config["delete_behaviour"].upper()
        self.inter_action_delay = self.config["inter_action_delay"]
        self.action_results_limit = self.config.get(
            "action_results_limit", Config.DEFAULT_ACTION_RESULTS_LIMIT
        )

        if self.delete_behaviour not in Config.DELETE_BEHAVIOURS:
            raise InvalidConfigSettingError(
                "Invalid delete behaviour, either 'HARD' or 'SOFT'"
            )

        if self.delete_behaviour not in Config.DELETE_BEHAVIOURS:
            raise InvalidConfigSettingError(
                "Invalid delete behaviour, either 'HARD' or 'SOFT'"
            )

    def create_output_folders(self, table_names: List[str]):
        """Generate the output folders for the tables

        Args:
            table_names (List[str]): List of table names
        """
        for table_name in table_names:
            Path(f"{self.output_path}/{table_name}").mkdir(parents=True, exist_ok=True)

    def load_datasets(self) -> List[Table]:
        """Load the datasets from the config file

        Returns:
            List[Table]: List of Table objects
        """

        if "tables" not in self.config:
            raise InvalidConfigSettingError(
                "'tables' not found in config, consult README for sample config"
            )

        tables = {}
        for table in self.config["tables"]:
            fields = {}
            actions = {}
            table_name = table.get("name", None)
            if table_name is None:
                raise InvalidConfigSettingError("Table name missing in config")

            if "fields" not in table:
                raise InvalidConfigSettingError(
                    f"'fields' not found in table {table_name}, consult README for sample config"
                )

            for field in table["fields"]:
                if field.get("name", None) is None:
                    raise InvalidConfigSettingError(
                        f"Field name not found in table `{table_name}`"
                    )
                if Field.is_valid(field, table_name):
                    fields[field["name"]] = Field(
                        field["name"],
                        field["type"],
                        field["value"],
                        field.get("is_pk", False),
                        table_name,  # passed so as to provide better error messages
                        field.get("arguments", []),
                    )

            for action in table["actions"]:
                if Create.is_valid(action, table_name):
                    actions[action.get("name")] = Create(
                        name=action.get("name"),
                        frequency=action.get("frequency", None),
                        effect=action.get("effect", None),
                        effect_count=action.get("effect_count", None),
                        action_condition=action.get("action_condition", None),
                    )
                elif Remove.is_valid(action, table_name):
                    actions[action.get("name")] = Remove(
                        name=action.get("name"),
                        frequency=action.get("frequency", None),
                        where_clause=action.get("where_condition", None),
                        effect=action.get("effect", None),
                        effect_count=action.get("effect_count", None),
                        action_condition=action.get("action_condition", None),
                    )
                elif Set.is_valid(action, table_name):

                    actions[action.get("name")] = Set(
                        name=action.get("name"),
                        field=action.get("field", None),
                        value=Imposter(
                            action.get("value", None),
                            action.get("arguments", []),
                            action.get("name", None),
                        ),
                        where_clause=action.get("where_condition", None),
                        frequency=action.get("frequency", None),
                        effect=action.get("effect", None),
                        effect_count=action.get("effect_count", None),
                        action_condition=action.get("action_condition", None),
                    )

            tables[table.get("name")] = Table(table.get("name"), fields, actions)

        self._validate_table_config(tables)

        return tables

    def _validate_table_config(self, tables: List[Table]):
        """Validate the tables and fields in the config. Can only be called after loading the tables

        Args:
            tables (List[Table]): List of Table objects to validate
        """

        # validate all fields metioned in where statements and actions match the fields in the tables

        for table in tables.values():
            for field in table.fields.values():
                if field.imposter.imposter_type == ImposterType.TABLE_RANDOM:
                    fields = (
                        field.imposter.value.split("(")[1]
                        .replace(")", "")
                        .replace(" ", "")
                        .split(",")
                    )
                    if len(fields) != 3:
                        raise InvalidConfigSettingError(
                            f"where condition `{field.imposter.value}` is invalid"
                        )
                    if not tables[fields[0]]:
                        raise InvalidConfigSettingError(
                            f"Table `{fields[0]}` not found in config for field value `{field.imposter.value}`"
                        )
                    if not tables[fields[0]].fields[fields[1]]:
                        raise InvalidConfigSettingError(
                            f"Field `{fields[1]}` not found in table `{fields[0]}` for field value `{field.imposter.value}`"
                        )

            for action in table.actions.values():
                if (
                    isinstance(action, Set) or isinstance(action, Remove)
                ) and action.where_clause is not None:
                    if tables[action.where_table] is None:
                        raise InvalidConfigSettingError(
                            f"Table `{action.where_table}` not found in config"
                        )
                    if tables[action.where_table].fields[action.where_field] is None:
                        raise InvalidConfigSettingError(
                            f"Field `{action.where_field}` not found in table `{action.where_table}`"
                        )
                    if action.where_value.imposter_type == ImposterType.TABLE_RANDOM:
                        fields = (
                            action.where_clause.split("(")[1]
                            .replace(")", "")
                            .replace(" ", "")
                            .split(",")
                        )
                        if len(fields) != 3:
                            raise InvalidConfigSettingError(
                                f"where condition {action.where_value} is invalid"
                            )
                        if not tables[fields[0]]:
                            raise InvalidConfigSettingError(
                                f"Table `{fields[0]}` not found in config for where condition `{action.where_value}`"
                            )
                        if not tables[fields[0]].fields[fields[1]]:
                            raise InvalidConfigSettingError(
                                f"Field `{fields[1]}` not found in table `{fields[0]}` for where condition `{action.where_value}`"
                            )

                if action.effect:

                    if tables[action.effect_table] is None:
                        raise InvalidConfigSettingError(
                            f"Table `{action.effect_table}` not found in config"
                        )
                    for effect_field_from in action.effect_fields.values():
                        if table.fields[effect_field_from] is None:
                            raise InvalidConfigSettingError(
                                f"Field `{effect_field_from}` not found in table `{action.effect_table}`"
                            )
                    for effect_field_to in action.effect_fields.keys():
                        if tables[action.effect_table].fields[effect_field_to] is None:
                            raise InvalidConfigSettingError(
                                f"Field `{effect_field_to}` not found in table `{action.effect_table}`"
                            )

                    # if effect action doesn't exist in the table
                    if not tables[action.effect_table].actions[action.effect_action]:
                        raise InvalidConfigSettingError(
                            f"""Effect action `{action.effect_action}` not found in table `{tables[action.effect_table].table_name}`"""
                        )

        return True
