import pytest
from mockpipe.action import Action, Create, Remove, Set
from mockpipe.exceptions import InvalidValueError
from mockpipe.imposter import Imposter
from mockpipe.field import Field


def test_action_init_effect():
    action = Action("test", 0.5)
    assert action.name == "test"
    assert action.frequency == 0.5
    assert action.arguments == []
    assert action.effect is None
    assert action.effect_count is None
    assert action.action_condition is None

    action = Action(
        "test", 0.5, effect="  foo  .  bar  (  id  =  id )", effect_count="1"
    )
    assert action.name == "test"
    assert action.frequency == 0.5
    assert action.arguments == []
    assert action.effect_table == "foo"
    assert action.effect_action == "bar"
    assert action.effect_fields == {"id": "id"}

    action = Action("test", 0.5, action_condition="EffEcT_OnLY")
    assert action.name == "test"
    assert action.frequency == 0.5
    assert action.arguments == []
    assert action.effect is None
    assert action.effect_count is None
    assert action.action_condition == "EFFECT_ONLY"

    with pytest.raises(InvalidValueError):
        action = Action("test", 0.5, action_condition="EFFECT_ONLYYYY")


def test_create_init():
    action = Create("test", 0.5)
    assert action.name == "test"
    assert action.frequency == 0.5
    assert action.arguments == []
    assert action.effect is None
    assert action.effect_count is None
    assert action.action_condition is None

    action = Create(
        "test", 0.5, effect="  foo  .  bar  (  id  =  id )", effect_count="1"
    )
    assert action.name == "test"
    assert action.frequency == 0.5
    assert action.arguments == []
    assert action.effect_table == "foo"
    assert action.effect_action == "bar"
    assert action.effect_fields == {"id": "id"}

    action = Create("test", 0.5, action_condition="EffEcT_OnLY")
    assert action.name == "test"
    assert action.frequency == 0.5
    assert action.arguments == []
    assert action.effect is None
    assert action.effect_count is None
    assert action.action_condition == "EFFECT_ONLY"

    with pytest.raises(InvalidValueError):
        action = Create("test", 0.5, action_condition="EFFECT_ONLYYYY")


def test_remove_init():
    action = Remove("test", 0.5, where_clause="foo.bar==static(123)")
    assert action.name == "test"
    assert action.frequency == 0.5
    assert action.arguments == []
    assert action.effect is None
    assert action.effect_count is None
    assert action.action_condition is None

    assert action.where_table == "foo"
    assert action.where_field == "bar"
    assert action.where_value == Imposter("static(123)")
    assert action.where_condition == "=="

    action = Remove(
        "test",
        0.5,
        effect="  foo  .  bar  (  id  =  id )",
        where_clause="",
        effect_count="1",
    )
    assert action.name == "test"
    assert action.frequency == 0.5
    assert action.arguments == []
    assert action.effect_table == "foo"
    assert action.effect_action == "bar"
    assert action.effect_fields == {"id": "id"}

    action = Remove("test", 0.5, where_clause="", action_condition="EffEcT_OnLY")
    assert action.name == "test"
    assert action.frequency == 0.5
    assert action.arguments == []
    assert action.effect is None
    assert action.effect_count is None
    assert action.action_condition == "EFFECT_ONLY"

    with pytest.raises(InvalidValueError):
        action = Remove(
            "test",
            0.5,
            action_condition="EFFECT_ONLYYYY",
            where_clause="",
        )


def test_pass_where_condition():

    for condition in Action.EQUALITIES:
        dummy_action = Remove(
            "test", 0.5, where_clause=f"  foo.bar   {condition}   static(  123 )   "
        )
        assert dummy_action.where_table == "foo"
        assert dummy_action.where_field == "bar"
        assert dummy_action.where_value == Imposter("static(123)")
        assert dummy_action.where_condition == condition

    dummy_action = Remove(
        "test", 0.5, where_clause="foo.bar==static('  john   smith  ')"
    )
    assert dummy_action.where_table == "foo"
    assert dummy_action.where_field == "bar"
    assert dummy_action.where_value == Imposter('static("  john   smith  ")')

    dummy_action = Remove(
        "test", 0.5, where_clause="foo.bar==table_random(  employees  ,    id,   0 )"
    )
    assert dummy_action.where_table == "foo"
    assert dummy_action.where_field == "bar"
    assert dummy_action.where_value == Imposter("table_random(employees,id,0)")


def test_set_init():
    set_action = Set(
        name="test",
        field=Field("foo", "string", 'static("john smith")'),
        value=Imposter("static('john smith')"),
        where_clause="foo.bar==static(123)",
    )
    assert set_action.name == "test"
    assert set_action.field == Field("foo", "string", 'static("john smith")')
    assert set_action.value == Imposter("static('john smith')")
    assert set_action.where_clause == "foo.bar==static(123)"
    assert set_action.where_table == "foo"
    assert set_action.where_field == "bar"
    assert set_action.where_value == Imposter("static(123)")
    assert set_action.where_condition == "=="


# def test_action_str():
#     action = Action("test", 0.5)
#     assert str(action) == "Action: test"


# def test_action_repr():
#     action = Action("test", 0.5)
#     assert repr(action) == "<Action: test>"


def test_create_is_valid():
    attribs = {"name": "test", "action": "create", "frequency": 0.5}
    assert Create.is_valid(attribs) == True


def test_remove_is_valid():
    attribs = {
        "name": "test",
        "action": "remove",
        "frequency": 0.5,
        "where_condition": "id == 1",
    }
    assert Remove.is_valid(attribs, table_name="foo") == True


def test_set_is_valid():
    attribs = {
        "name": "test",
        "action": "set",
        "frequency": 0.5,
        "field": Field("name", "string", "static('John Doe')"),
        "value": Imposter("static('John Doe')"),
    }
    assert Set.is_valid(attribs) == True
