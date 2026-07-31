from typing import List, Dict, Type
import time
import csv
import jsonlines
import os


class BaseExporter:
    """Base class for exporters, to be extended for specific formats"""

    def __init__(self, base_path: str):
        self.base_path = base_path

    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        raise NotImplementedError("Subclasses should implement this method")


class CSVExporter(BaseExporter):
    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        """Export data to CSV format"""
        if format.lower() != "csv":
            raise NotImplementedError("CSVExporter only supports CSV format")
        self._export_csv(self.base_path, table_name, values)

    def _export_csv(self, base_path: str, table_name: str, values: List[Dict]) -> None:
        # Create directory if it doesn't exist
        os.makedirs(f"{base_path}/{table_name}", exist_ok=True)

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


class JSONExporter(BaseExporter):
    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        """Export data to JSON format"""
        if format.lower() != "json":
            raise NotImplementedError("JSONExporter only supports JSON format")
        self._export_json(self.base_path, table_name, values)

    def _export_json(self, base_path: str, table_name: str, values: List[Dict]) -> None:
        # Create directory if it doesn't exist
        os.makedirs(f"{base_path}/{table_name}", exist_ok=True)

        with jsonlines.open(
            f"{base_path}/{table_name}/{table_name}_{str(time.time()).replace('.', '').ljust(17, '0')}.json",
            "w",
        ) as f:
            f.write_all(values)


class ExporterRegistry:
    """Registry for managing exporter classes"""

    _exporters: Dict[str, Type[BaseExporter]] = {}

    @classmethod
    def register(cls, format_name: str, exporter_class: Type[BaseExporter]) -> None:
        """Register an exporter class for a specific format"""
        cls._exporters[format_name.lower()] = exporter_class

    @classmethod
    def get_exporter(cls, format_name: str, base_path: str) -> BaseExporter:
        """Get an exporter instance for the specified format"""
        format_key = format_name.lower()
        if format_key not in cls._exporters:
            raise ValueError(f"No exporter registered for format: {format_name}")

        exporter_class = cls._exporters[format_key]
        return exporter_class(base_path)

    @classmethod
    def list_formats(cls) -> List[str]:
        """List all registered formats"""
        return list(cls._exporters.keys())

    @classmethod
    def unregister(cls, format_name: str) -> None:
        """Unregister an exporter for a specific format"""
        format_key = format_name.lower()
        if format_key in cls._exporters:
            del cls._exporters[format_key]


# Register built-in exporters
ExporterRegistry.register("csv", CSVExporter)
ExporterRegistry.register("json", JSONExporter)


class Exporter:
    def __init__(self, base_path: str):
        self.base_path = base_path

    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        """Export data using the appropriate exporter for the format

        Args:
            table_name (str): table name (used as file partition)
            values (List[Dict]): list of dictionaries to export to target format
            format (str): export format (e.g., 'json', 'csv', or custom format)

        Raises:
            ValueError: If no exporter is registered for the format
        """
        exporter = ExporterRegistry.get_exporter(format, self.base_path)
        exporter.export(table_name, values, format)

    @staticmethod
    def register_exporter(format_name: str, exporter_class: Type[BaseExporter]) -> None:
        """Register a custom exporter class"""
        ExporterRegistry.register(format_name, exporter_class)

    @staticmethod
    def list_supported_formats() -> List[str]:
        """List all supported export formats"""
        return ExporterRegistry.list_formats()
