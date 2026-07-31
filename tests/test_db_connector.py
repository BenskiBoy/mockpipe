import pytest
import duckdb

from mockpipe.db_connector import DBConnector, DirectStatement, SQLStatement


@pytest.fixture
def db():
    return DBConnector(":memory:")


@pytest.fixture
def db_with_table(db):
    db.execute_sql(
        "CREATE TABLE foo (id INTEGER, change_token INTEGER, change_type TEXT);"
    )
    return db


def test_execute_sql_with_result_field_returns_scalar(db_with_table):
    db_with_table.execute_sql("INSERT INTO foo VALUES (1, 1, 'I');")
    result = db_with_table.execute_sql("SELECT count(*) as cnt FROM foo", "cnt")
    assert result == "1"


def test_execute_sql_without_result_field_returns_dict(db_with_table):
    db_with_table.execute_sql("INSERT INTO foo VALUES (1, 1, 'I');")
    result = db_with_table.execute_sql("SELECT * FROM foo")
    assert isinstance(result, dict)
    assert result["id"] == {0: 1}


def test_execute_sql_raises_on_invalid_sql(db):
    with pytest.raises(duckdb.ParserException):
        db.execute_sql("this is not valid sql;")


def test_get_max_change_token_and_get_latest_rows(db_with_table):
    db_with_table.execute_sql("INSERT INTO foo VALUES (1, 1, 'I');")
    db_with_table.execute_sql("INSERT INTO foo VALUES (2, 2, 'I');")

    assert db_with_table.get_max_change_token("foo") == 2

    latest = db_with_table.get_latest_rows("foo")
    assert len(latest) == 1
    assert latest[0]["id"] == 2


def test_execute_runs_mixed_statements(db_with_table):
    statements = [
        DirectStatement("INSERT INTO foo VALUES ("),
        DirectStatement("3"),
        DirectStatement(", "),
        SQLStatement(
            value="select coalesce((max(change_token) + 1), 1) as inc from foo;",
            result_field="inc",
        ),
        DirectStatement(", 'I');"),
    ]
    db_with_table.execute(statements)

    count = db_with_table.execute_sql("SELECT count(*) as cnt FROM foo", "cnt")
    assert count == "1"


def test_create_metadata_table(db):
    db.create_metadata_table("mp_metadata")
    db.execute_sql(
        "INSERT INTO mp_metadata (id, change_token, action, action_id) "
        "VALUES (1, 1, 'create', 'a');"
    )
    result = db.execute_sql("SELECT count(*) as cnt FROM mp_metadata", "cnt")
    assert result == "1"
