from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from mockpipe.exporter import Exporter, ExporterRegistry


VALUES = [
    {"id": 1, "name": "foo"},
    {"id": 2, "name": "bar"},
]


def test_parquet_export_roundtrip(tmp_path):
    exporter = Exporter(str(tmp_path))
    exporter.export("mytable", VALUES, "parquet")

    files = list((tmp_path / "mytable").glob("*.parquet"))
    assert len(files) == 1

    df = pd.read_parquet(files[0])
    assert df.to_dict(orient="records") == VALUES


def test_parquet_is_a_registered_format():
    assert "parquet" in ExporterRegistry.list_formats()


def test_parquet_exporter_rejects_other_formats(tmp_path):
    exporter = Exporter(str(tmp_path))
    with pytest.raises(NotImplementedError):
        ExporterRegistry.get_exporter("parquet", str(tmp_path)).export(
            "mytable", VALUES, "json"
        )


def test_webhook_is_a_registered_format():
    assert "webhook" in ExporterRegistry.list_formats()


@patch("mockpipe.exporter.requests.post")
def test_webhook_export_posts_rows_to_configured_url(mock_post, tmp_path):
    mock_post.return_value = MagicMock(status_code=200)
    exporter = Exporter(str(tmp_path), {"url": "https://example.com/hook"})

    exporter.export("mytable", VALUES, "webhook")

    mock_post.assert_called_once_with(
        "https://example.com/hook",
        json={"table": "mytable", "rows": VALUES},
        timeout=10,
    )
    mock_post.return_value.raise_for_status.assert_called_once()


def test_webhook_export_without_url_raises(tmp_path):
    exporter = Exporter(str(tmp_path))
    with pytest.raises(ValueError):
        exporter.export("mytable", VALUES, "webhook")


@patch("mockpipe.exporter.requests.post")
def test_webhook_exporter_rejects_other_formats(mock_post, tmp_path):
    webhook_exporter = ExporterRegistry.get_exporter(
        "webhook", str(tmp_path), {"url": "https://example.com/hook"}
    )
    with pytest.raises(NotImplementedError):
        webhook_exporter.export("mytable", VALUES, "json")
    mock_post.assert_not_called()


def test_kafka_is_a_registered_format():
    assert "kafka" in ExporterRegistry.list_formats()


@patch("mockpipe.exporter.KafkaProducer")
def test_kafka_export_sends_rows_to_configured_topic(mock_producer_cls, tmp_path):
    mock_producer = MagicMock()
    mock_producer_cls.return_value = mock_producer
    exporter = Exporter(
        str(tmp_path), {"topic": "mytopic", "bootstrap_servers": "localhost:9092"}
    )

    exporter.export("mytable", VALUES, "kafka")

    mock_producer_cls.assert_called_once()
    assert mock_producer_cls.call_args.kwargs["bootstrap_servers"] == "localhost:9092"
    mock_producer.send.assert_called_once_with(
        "mytopic", value={"table": "mytable", "rows": VALUES}
    )


@patch("mockpipe.exporter.KafkaProducer")
def test_kafka_export_reuses_producer_across_calls(mock_producer_cls, tmp_path):
    mock_producer_cls.return_value = MagicMock()
    exporter = Exporter(
        str(tmp_path), {"topic": "mytopic", "bootstrap_servers": "localhost:9092"}
    )

    exporter.export("mytable", VALUES, "kafka")
    exporter.export("mytable", VALUES, "kafka")

    mock_producer_cls.assert_called_once()


@patch("mockpipe.exporter.KafkaProducer")
def test_kafka_export_without_topic_raises(mock_producer_cls, tmp_path):
    exporter = Exporter(str(tmp_path), {"bootstrap_servers": "localhost:9092"})
    with pytest.raises(ValueError):
        exporter.export("mytable", VALUES, "kafka")
    mock_producer_cls.assert_not_called()


@patch("mockpipe.exporter.KafkaProducer")
def test_kafka_export_without_bootstrap_servers_raises(mock_producer_cls, tmp_path):
    exporter = Exporter(str(tmp_path), {"topic": "mytopic"})
    with pytest.raises(ValueError):
        exporter.export("mytable", VALUES, "kafka")
    mock_producer_cls.assert_not_called()


@patch("mockpipe.exporter.KafkaProducer")
def test_kafka_exporter_close_flushes_and_closes_producer(mock_producer_cls, tmp_path):
    mock_producer = MagicMock()
    mock_producer_cls.return_value = mock_producer
    exporter = Exporter(
        str(tmp_path), {"topic": "mytopic", "bootstrap_servers": "localhost:9092"}
    )
    exporter.export("mytable", VALUES, "kafka")

    exporter.close()

    mock_producer.flush.assert_called_once()
    mock_producer.close.assert_called_once()


@patch("mockpipe.exporter.KafkaProducer")
def test_kafka_exporter_rejects_other_formats(mock_producer_cls, tmp_path):
    kafka_exporter = ExporterRegistry.get_exporter(
        "kafka",
        str(tmp_path),
        {"topic": "mytopic", "bootstrap_servers": "localhost:9092"},
    )
    with pytest.raises(NotImplementedError):
        kafka_exporter.export("mytable", VALUES, "json")
    mock_producer_cls.assert_not_called()
