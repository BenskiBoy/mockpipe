from mockpipe.config import Config
from mockpipe.imposter import Imposter
import pytest
from mockpipe.config import InvalidConfigSettingError


def test_basic_config():
    config_str = """
db_path: simple.db
delete_behaviour: soft
inter_action_delay: 0.5
action_results_limit: 10

output:
  format: json
  path: extract_json

tables:
  - name: foo
    fields:
      - name: id
        type: int
        value: increment
        is_pk: true
      - name: some_value
        type: string
        value: fake.company
    actions:
      - name: create
        action: create
        frequency: 0.25
      - name: remove
        action: remove
        frequency: 0.25
        where_condition: foo.id == table_random(foo, id, 0)
"""

    config = Config(config_str)

    assert config.db_path == "simple.db"
    assert config.delete_behaviour == "SOFT"
    assert config.inter_action_delay == 0.5
    assert config.action_results_limit == 10
    assert config.output_format == "json"
    assert config.output_path == "extract_json"

    assert config.full_load == False

    tables = config.load_datasets()
    assert tables["foo"].table_name == "foo"
    assert tables["foo"].fields["id"].name == "id"
    assert tables["foo"].fields["id"].type == "int"
    imp = Imposter(value="increment", arguments=[], field_name="id")
    assert tables["foo"].fields["id"].imposter.value == imp.value
    assert tables["foo"].fields["id"].imposter.arguments == imp.arguments
    assert tables["foo"].fields["id"].imposter.field_name == imp.field_name
    assert tables["foo"].fields["id"].imposter.imposter_type == imp.imposter_type


def test_empty_config_raises():
    with pytest.raises(InvalidConfigSettingError):
        Config("")

    with pytest.raises(InvalidConfigSettingError):
        Config("# just a comment, no mapping")

    with pytest.raises(InvalidConfigSettingError):
        Config("- just\n- a\n- list")


def test_full_load_config():
    config = Config(
        """
db_path: simple.db
delete_behaviour: soft
inter_action_delay: 0.5
action_results_limit: 10
full_load:
  include_deletes: true
  frequency: 50
"""
    )
    assert config.full_load is True
    assert config.full_load_include_deletes is True
    assert config.full_load_frequency == 50

    # can't have full load include deletes with hard delete behaviour
    with pytest.raises(InvalidConfigSettingError):
        config = Config(
            """
    db_path: simple.db
    delete_behaviour: hard
    inter_action_delay: 0.5
    action_results_limit: 10
    full_load:
      include_deletes: true
      frequency: 50
    """
        )
