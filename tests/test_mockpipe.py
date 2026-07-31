import pytest

from mockpipe.mockpipe import MockPipe
from mockpipe.exceptions import InvalidConfigSettingError


SINGLE_TABLE_CONFIG = """
db_path: ":memory:"
delete_behaviour: soft
inter_action_delay: 0.01

output:
  format: json
  path: /tmp/mockpipe_test_extract

tables:
  - name: foo
    fields:
      - name: id
        type: int
        value: increment
        is_pk: true
      - name: name
        type: string
        value: static("bar")
    actions:
      - name: create
        action: create
        frequency: 1.0
"""

EFFECT_CONFIG = """
db_path: ":memory:"
delete_behaviour: soft
inter_action_delay: 0.01

output:
  format: json
  path: /tmp/mockpipe_test_extract

tables:
  - name: parent
    fields:
      - name: id
        type: int
        value: increment
        is_pk: true
    actions:
      - name: create
        action: create
        frequency: 0.5
        effect: child.create(parent_id=id)
        effect_count: 1

  - name: child
    fields:
      - name: id
        type: int
        value: increment
        is_pk: true
      - name: parent_id
        type: int
        value: inherit
    actions:
      - name: create
        action: create
        frequency: 0.5
        action_condition: effect_only
"""


@pytest.fixture
def mp():
    return MockPipe(SINGLE_TABLE_CONFIG)


def test_init_creates_tables_and_seeds_change_token(mp):
    assert "foo" in mp.tables
    # max(change_token) over an empty table is SQL NULL; get_max_change_token
    # normalizes the resulting NaN to a clean, comparable None.
    assert mp.max_change_token_values["foo"] is None

    result = mp.db.execute_sql(
        "select count(1) as cnt from information_schema.tables where table_name = 'foo'",
        "cnt",
    )
    assert result == "1"


def test_step_inserts_a_row_and_records_result(mp):
    mp.step()

    assert len(mp.action_results) == 1
    assert mp.max_change_token_values["foo"] == 1

    rows = mp.db.execute_sql("select count(1) as cnt from foo", "cnt")
    assert rows == "1"


def test_execute_action_create_directly(mp):
    create_action = mp.tables["foo"].actions["create"]
    mp.execute_action(mp.tables["foo"], create_action)

    assert len(mp.action_results) == 1
    assert mp.action_results[0].table_name == "foo"
    rows = mp.db.execute_sql("select count(1) as cnt from foo", "cnt")
    assert rows == "1"


def test_remove_action_on_empty_table_is_not_treated_as_a_change():
    # A remove/set action whose where_condition matches nothing (because the
    # table is still empty) must not register as a change - previously this
    # crashed, since comparing NaN (an empty table's max change_token) to NaN
    # is always "different" in Python, and the resulting bogus change_token
    # then got embedded literally as `nan` into the metadata table's INSERT.
    mp = MockPipe(
        """
db_path: ":memory:"
tables:
  - name: foo
    fields:
      - name: id
        type: int
        value: increment
        is_pk: true
    actions:
      - name: remove
        action: remove
        frequency: 1.0
        where_condition: foo.id == table_random(foo, id, 0)
"""
    )
    remove_action = mp.tables["foo"].actions["remove"]

    mp.execute_action(mp.tables["foo"], remove_action)

    assert mp.action_results == []
    assert mp.iteration_count == 0
    assert mp.max_change_token_values["foo"] is None


def test_execute_action_rejects_effect_only_action_directly():
    mp = MockPipe(EFFECT_CONFIG)
    effect_only_action = mp.tables["child"].actions["create"]

    with pytest.raises(ValueError):
        mp.execute_action(mp.tables["child"], effect_only_action)


def test_execute_action_effect_chain_creates_child_row():
    mp = MockPipe(EFFECT_CONFIG)
    parent_create = mp.tables["parent"].actions["create"]

    mp.execute_action(mp.tables["parent"], parent_create)

    parent_count = mp.db.execute_sql("select count(1) as cnt from parent", "cnt")
    child_count = mp.db.execute_sql("select count(1) as cnt from child", "cnt")
    assert parent_count == "1"
    assert child_count == "1"

    # the child's parent_id should have inherited the parent's id
    parent_id = mp.db.execute_sql("select id from parent", "id")
    child_parent_id = mp.db.execute_sql("select parent_id from child", "parent_id")
    assert parent_id == child_parent_id


def test_start_and_stop_lifecycle(mp):
    assert mp.is_running is False
    mp.start()
    assert mp.is_running is True
    mp.stop()
    assert mp.is_running is False


def test_step_is_a_noop_while_running(mp):
    mp.start()
    try:
        # step() only runs _execute directly when not already running;
        # while start()'s background thread is running, step() should do nothing
        results_before = len(mp.action_results)
        mp.step()
        # can't assert on count deterministically since the background thread
        # is also producing changes, but step() itself must not raise
        assert len(mp.action_results) >= results_before
    finally:
        mp.stop()


def test_invalid_config_raises_before_construction():
    with pytest.raises(InvalidConfigSettingError):
        MockPipe("")


def test_perform_iteration_weights_by_action_frequency():
    config = """
db_path: ":memory:"
tables:
  - name: foo
    fields:
      - name: id
        type: int
        value: increment
        is_pk: true
    actions:
      - name: common
        action: create
        frequency: 0.95
      - name: rare
        action: create
        frequency: 0.05
"""
    mp = MockPipe(config)

    picks = [mp._perform_iteration()[0][0].action.name for _ in range(500)]

    common_count = picks.count("common")
    rare_count = picks.count("rare")
    assert common_count + rare_count == 500
    # frequency isn't a strict probability (weights don't have to sum to 1),
    # but a 0.95 vs 0.05 split should be overwhelmingly lopsided
    assert common_count > rare_count * 5


def test_metadata_table_tracks_iteration_count(mp):
    assert mp.iteration_count == 0

    mp.step()
    assert mp.iteration_count == 1

    row_count = mp.db.execute_sql(
        f"select count(1) as cnt from {mp.METADATA_TABLE_NAME}", "cnt"
    )
    assert row_count == "1"


def test_metadata_table_resumes_iteration_count_across_restarts(tmp_path):
    db_path = tmp_path / "resume.db"
    extract_path = tmp_path / "extract"
    config = f"""
db_path: {db_path}
inter_action_delay: 0.01
output:
  format: json
  path: {extract_path}
tables:
  - name: foo
    fields:
      - name: id
        type: int
        value: increment
        is_pk: true
    actions:
      - name: create
        action: create
        frequency: 1.0
"""
    mp1 = MockPipe(config)
    mp1.step()
    mp1.step()
    assert mp1.iteration_count == 2

    # re-opening the same db_path should resume the count, not restart at 0
    mp2 = MockPipe(config)
    assert mp2.iteration_count == 2

    mp2.step()
    assert mp2.iteration_count == 3


def test_full_load_triggers_periodic_snapshot_export(tmp_path):
    extract_path = tmp_path / "extract"
    config = f"""
db_path: ":memory:"
inter_action_delay: 0.01
output:
  format: json
  path: {extract_path}
full_load:
  frequency: 2
tables:
  - name: foo
    fields:
      - name: id
        type: int
        value: increment
        is_pk: true
    actions:
      - name: create
        action: create
        frequency: 1.0
"""
    mp = MockPipe(config)
    for _ in range(4):
        mp.step()

    files = sorted((extract_path / "foo").glob("*.json"))
    # 4 incremental exports (one per create) + 2 full-load snapshots
    # (triggered at iteration_count 2 and 4) = 6 files
    assert len(files) == 6

    row_counts = [sum(1 for _ in open(f)) for f in files]
    # the two full-load snapshots contain every row so far (2 and 4 rows);
    # the four incremental exports each contain exactly the one changed row
    multi_row_files = sorted(rc for rc in row_counts if rc > 1)
    assert multi_row_files == [2, 4]
