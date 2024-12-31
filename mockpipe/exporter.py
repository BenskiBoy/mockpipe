from typing import List, Dict
import time
import csv
import jsonlines


class Exporter:
    def __init__(self, base_path: str):
        self.base_path = base_path

    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        """_summary_

        Args:
            table_name (str): table name (used as file partition)
            values (List[Dict]): list of dictionaries to export to target format
            format (str): export format, either 'json' or 'csv'

        Raises:
            NotImplementedError: If not a valid export format
        """
        if format.lower() == "json":
            self._export_json(self.base_path, table_name, values)
        elif format.lower() == "csv":
            self._export_csv(self.base_path, table_name, values)
        else:
            raise NotImplementedError()

    def _export_json(self, base_path: str, table_name: str, values: List[Dict]) -> None:
        with jsonlines.open(
            f"{base_path}/{table_name}/{table_name}_{str(time.time()).replace('.', '').ljust(17, '0')}.json",
            "w",
        ) as f:
            f.write_all(values)

    def _export_csv(self, base_path: str, table_name: str, values: List[Dict]) -> None:
        with open(
            f"{base_path}/{table_name}/{table_name}_{str(time.time()).replace('.', '').ljust(17, '0')}.csv",
            "w",
            newline="",
        ) as f:
            writer = csv.DictWriter(
                f, fieldnames=values[0].keys(), quoting=csv.QUOTE_ALL
            )
            writer.writeheader()
            writer.writerows(values)
