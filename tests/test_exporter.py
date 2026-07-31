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
