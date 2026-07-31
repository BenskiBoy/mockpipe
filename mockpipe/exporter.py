from typing import Any, List, Dict, Optional, Type
import itertools
import json
import time
import csv
import jsonlines
import os

import pandas as pd
import requests
from kafka import KafkaProducer


class BaseExporter:
    """Base class for exporters, to be extended for specific formats"""

    # Shared across all exporter instances so filenames stay unique even if
    # two exports happen within the same clock tick - time.time()'s
    # resolution isn't fine enough to guarantee that on its own (observed
    # colliding on Windows, silently overwriting one export's file with
    # another's).
    _filename_counter = itertools.count()

    def __init__(self, base_path: str, output_config: Optional[Dict[str, Any]] = None):
        self.base_path = base_path
        self.output_config = output_config or {}

    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        raise NotImplementedError("Subclasses should implement this method")

    def close(self) -> None:
        """Release any held resources (connections, etc). No-op by default."""

    def _export_file_path(self, table_name: str, extension: str) -> str:
        """Build a guaranteed-unique output file path for a table/format,
        creating the table's output directory if it doesn't exist yet."""
        os.makedirs(f"{self.base_path}/{table_name}", exist_ok=True)
        timestamp = str(time.time()).replace(".", "").ljust(17, "0")
        unique_id = f"{timestamp}_{next(BaseExporter._filename_counter)}"
        return f"{self.base_path}/{table_name}/{table_name}_{unique_id}.{extension}"


class CSVExporter(BaseExporter):
    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        """Export data to CSV format"""
        if format.lower() != "csv":
            raise NotImplementedError("CSVExporter only supports CSV format")
        file_path = self._export_file_path(table_name, "csv")
        with open(file_path, "w", newline="") as f:
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
        file_path = self._export_file_path(table_name, "json")
        with jsonlines.open(file_path, "w") as f:
            f.write_all(values)


class ParquetExporter(BaseExporter):
    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        """Export data to Parquet format"""
        if format.lower() != "parquet":
            raise NotImplementedError("ParquetExporter only supports Parquet format")
        file_path = self._export_file_path(table_name, "parquet")
        pd.DataFrame(values).to_parquet(file_path)


class WebhookExporter(BaseExporter):
    """Posts changed rows to a configured HTTP(S) endpoint, instead of a file.

    Useful for testing a downstream consumer directly, rather than polling
    for files it would otherwise have to pick up.
    """

    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        if format.lower() != "webhook":
            raise NotImplementedError("WebhookExporter only supports webhook format")
        url = self.output_config.get("url")
        if not url:
            raise ValueError(
                "output.url must be set in the config when using the webhook output format"
            )
        response = requests.post(
            url, json={"table": table_name, "rows": values}, timeout=10
        )
        response.raise_for_status()


class KafkaExporter(BaseExporter):
    """Publishes changed rows as a JSON message to a configured Kafka topic,
    instead of a file.

    The producer connection is created lazily on first use and kept open for
    reuse across calls - call close() (done automatically by
    MockPipe.stop()) to flush and release it at the end of a run.
    """

    def __init__(self, base_path: str, output_config: Optional[Dict[str, Any]] = None):
        super().__init__(base_path, output_config)
        self._producer: Optional[KafkaProducer] = None

    def _get_producer(self) -> KafkaProducer:
        if self._producer is None:
            bootstrap_servers = self.output_config.get("bootstrap_servers")
            if not bootstrap_servers:
                raise ValueError(
                    "output.bootstrap_servers must be set in the config when using "
                    "the kafka output format"
                )
            self._producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        return self._producer

    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        if format.lower() != "kafka":
            raise NotImplementedError("KafkaExporter only supports kafka format")
        topic = self.output_config.get("topic")
        if not topic:
            raise ValueError(
                "output.topic must be set in the config when using the kafka output format"
            )
        producer = self._get_producer()
        future = producer.send(topic, value={"table": table_name, "rows": values})
        future.get(timeout=10)

    def close(self) -> None:
        if self._producer is not None:
            self._producer.flush()
            self._producer.close()
            self._producer = None


class ExporterRegistry:
    """Registry for managing exporter classes"""

    _exporters: Dict[str, Type[BaseExporter]] = {}

    @classmethod
    def register(cls, format_name: str, exporter_class: Type[BaseExporter]) -> None:
        """Register an exporter class for a specific format"""
        cls._exporters[format_name.lower()] = exporter_class

    @classmethod
    def get_exporter(
        cls,
        format_name: str,
        base_path: str,
        output_config: Optional[Dict[str, Any]] = None,
    ) -> BaseExporter:
        """Get an exporter instance for the specified format"""
        format_key = format_name.lower()
        if format_key not in cls._exporters:
            raise ValueError(f"No exporter registered for format: {format_name}")

        exporter_class = cls._exporters[format_key]
        return exporter_class(base_path, output_config)

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
ExporterRegistry.register("parquet", ParquetExporter)
ExporterRegistry.register("webhook", WebhookExporter)
ExporterRegistry.register("kafka", KafkaExporter)


class Exporter:
    def __init__(self, base_path: str, output_config: Optional[Dict[str, Any]] = None):
        self.base_path = base_path
        self.output_config = output_config or {}
        # Cached per format, rather than instantiated fresh on every export()
        # call, so stateful exporters (e.g. KafkaExporter's producer
        # connection) are reused across a run instead of reconnecting per row.
        self._exporters: Dict[str, BaseExporter] = {}

    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        """Export data using the appropriate exporter for the format

        Args:
            table_name (str): table name (used as file partition)
            values (List[Dict]): list of dictionaries to export to target format
            format (str): export format (e.g., 'json', 'csv', or custom format)

        Raises:
            ValueError: If no exporter is registered for the format
        """
        format_key = format.lower()
        exporter = self._exporters.get(format_key)
        if exporter is None:
            exporter = ExporterRegistry.get_exporter(
                format, self.base_path, self.output_config
            )
            self._exporters[format_key] = exporter
        exporter.export(table_name, values, format)

    def close(self) -> None:
        """Release any resources held by exporters used during this run."""
        for exporter in self._exporters.values():
            exporter.close()

    @staticmethod
    def register_exporter(format_name: str, exporter_class: Type[BaseExporter]) -> None:
        """Register a custom exporter class"""
        ExporterRegistry.register(format_name, exporter_class)

    @staticmethod
    def list_supported_formats() -> List[str]:
        """List all supported export formats"""
        return ExporterRegistry.list_formats()
