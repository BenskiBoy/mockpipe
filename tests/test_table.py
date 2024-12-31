import pytest
from unittest.mock import patch

# from unittest.mock import MagicMock
from mockpipe.table import Table
from mockpipe.field import Field
from mockpipe.action import Action, Create, Set, Remove
from mockpipe.imposter import Imposter
from mockpipe.db_connector import StatementResult, SQLStatement, DirectStatement


@pytest.fixture
def table():
    fields = {
        "id": Field(
            name="id",
            type="int",
            imposter="increment",
            is_pk=True,
        ),
        "name": Field(
            name="name",
            type="str",
            imposter="fake.name",
            arguments=[],
        ),
        "age": Field(
            name="age",
            type="int",
            imposter="fake.random_int",
            arguments=[0, 100],
        ),
    }
    actions = {
        "create": Create("create", 0.5),
        "update_name": Set(
            "update_name",
            Field(
                name="name",
                type="str",
                imposter="fake.name",
                arguments=[],
            ),
            Imposter(value="fake.name", arguments=[], field_name="update_name"),
        ),
        "remove_row": Remove(
            "remove_row", 0.25, where_clause="users.id == table_random(users, id, 0)"
        ),
    }
    return Table("users", fields, actions)


def test_get_action_by_name(table):
    action = table.get_action_by_name("update_name")
    assert action == table.actions["update_name"]


def test_generate_count_str(table):
    count_str = table.generate_count_str("users")
    assert count_str == "select count(*) as cnt from users where change_type != 'D';"


def test_generate_random_lookup_str(table):
    lookup_str = table.generate_random_lookup_str("users", "name", "John")
    assert (
        lookup_str
        == "select name from users where change_type != 'D' using sample 1 union all (select 'John' as name order by name desc)"
    )


def test_generate_increment_str(table):
    increment_str = table.generate_increment_str("users", "age")
    assert increment_str == "select coalesce((max(age) + 1), 1) as inc from users;"


def test_genereate_create_table_str(table):
    create_table_str = table.genereate_create_table_str()
    assert (
        " ".join(create_table_str.replace("\n", "").strip().split())
        == "CREATE TABLE if not exists users( id int, name str, age int, change_token int, change_type string, PRIMARY KEY (id));"
    )


@patch("mockpipe.imposter.fake.name", return_value="Joey Joe Joe Shabadoo")
@patch("mockpipe.imposter.fake.random_int", return_value=42)
def test_evaluate_imposter(mock_fake_name, mock_fake_int, table):
    imposter_results = {
        "id": SQLStatement(
            result_field="inc",
            value="select coalesce((max(id) + 1), 1) as inc from users;",
        ),
        "name": DirectStatement(
            value="Joey Joe Joe Shabadoo",
        ),
        "age": DirectStatement(
            value=42,
        ),
        "change_token": SQLStatement(
            result_field="inc",
            value="select coalesce((max(change_token) + 1), 1) as inc from users;",
        ),
        "change_type": DirectStatement(
            value="I",
        ),
    }
    for field in table.fields.values():
        assert (
            table.evaluate_imposter(field.imposter, []) == imposter_results[field.name]
        )


@patch("mockpipe.imposter.fake.name", return_value="Joey Joe Joe Shabadoo")
@patch("mockpipe.imposter.fake.random_int", return_value=42)
def test_generate_insert(mock_fake_name, mock_fake_int, table):
    action_statement_collection = table.generate_insert(
        list(table.actions.values()), []
    )

    statements = [
        DirectStatement("INSERT INTO users VALUES ("),
        DirectStatement("'"),
        SQLStatement(
            result_field="inc",
            value="select coalesce((max(id) + 1), 1) as inc from users;",
        ),
        DirectStatement("', "),
        DirectStatement("'"),
        DirectStatement("Joey Joe Joe Shabadoo"),
        DirectStatement("', "),
        DirectStatement("'"),
        DirectStatement(42),
        DirectStatement("', "),
        DirectStatement("'"),
        SQLStatement(
            result_field="inc",
            value="select coalesce((max(change_token) + 1), 1) as inc from users;",
        ),
        DirectStatement("', "),
        DirectStatement("'"),
        DirectStatement("I"),
        DirectStatement("'"),
        DirectStatement(");"),
    ]

    for i, statement in enumerate(action_statement_collection.statements):
        assert statement == statements[i]


@patch("mockpipe.imposter.fake.name", return_value="Joey Joe Joe Shabadoo")
def test_generate_set(mock_fake_name, table):
    action_statement_collection = table.generate_set(
        table.get_action_by_name("update_name"), []
    )

    statements = [
        DirectStatement("UPDATE users set name = '"),
        DirectStatement("Joey Joe Joe Shabadoo"),
        DirectStatement(
            "', change_token = (SELECT MAX(change_token) + 1 FROM users), change_type = 'U' WHERE change_type != 'D';"
        ),
    ]

    for i, statement in enumerate(action_statement_collection.statements):
        assert statement == statements[i]


def test_generate_delete(table):
    action_statement_collection = table.generate_delete(
        table.get_action_by_name("remove_row"), []
    )

    statements = [
        DirectStatement(
            "UPDATE users SET change_token = (SELECT MAX(change_token) + 1 FROM users), change_type = 'D' WHERE users.id == '"
        ),
        SQLStatement(
            result_field="id",
            value="select id from users where change_type != 'D' using sample 1 union all (select '0' as id order by id desc)",
        ),
        DirectStatement("' AND change_type != 'D';"),
    ]

    for i, statement in enumerate(action_statement_collection.statements):
        assert statement == statements[i]


def test_get_action_statement(table):
    for action in ["create", "update_name", "remove_row"]:
        statement_collection = table.get_action_statement(
            table.get_action_by_name(action), []
        )
        assert statement_collection.action == table.get_action_by_name(action)


def test_get_field_by_name(table):
    for field in table.fields.values():
        assert table.fields[field.name] == field
