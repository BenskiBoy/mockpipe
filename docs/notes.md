# imposter
- increment (auto incrementing id)
- table_random(<table>, <field>, <default>) use an existing value in a table. If none yet created, use the default
- random([<value1>, <value2>])
- static(<value>)
- faker
- inherit - to be used when the value is inherited from another tables 'effect' action. It will fetch the value

# action types
An action will be performed on a random row
- create
- delete
- set
    - constraint

## action effect
Upon completing the action, the next action performed can be designated by the effect.
The syntax for this is `<table>.<action>(<target_field>=<source_field>, (<target_field>=<source_field>) where target_field is the target actions field value and the source field is the field from the table that just had an action invoked.

An example might look like below.
In this example, when the foo tables 'create' action is performed, the effect is that bar's create action is invoked, passing foo's most recent 'id' value to be used as the value for bar's 'some_id' value.
Note the bar's value field is set to 'inherit' to denote that this is going to inherit from the effect.
You'll also note, effects can be chained.

When an effect is provided, an effect_count or effect_count_random can also be provided for how many times the effect should run.
Syntax for effect_count_random is `<min>,<max>`

```
db_path: simple.db
delete_behaviour: soft
inter_action_delay: 0.5
action_results_limit: 10 # Limit the number of results to store

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
        effect: bar.create(foo_id=id, some_other_inherit_value=some_value)
        effect_count_random: 1,5
      - name: remove
        action: remove
        frequency: 0.25
        where_condition: foo.id == table_random(foo, id, 0)

  - name: bar
    fields:
      - name: id
        type: int
        value: increment
        is_pk: true
      - name: foo_id
        type: int
        value: inherit
      - name: some_date
        type: string
        value: fake.date_between
        arguments:
        - "-1y"
        - "today"
      - name: some_other_inherit_value
        type: string
        value: inherit
    actions:
      - name: create
        action: create
        frequency: 0.25
        effect: baz.create(some_other_id=foo_id)
        action_condition: effect_only

  - name: baz
    fields:
      - name: some_other_id
        type: int
        value: inherit
        is_pk: true
      - name: some_date
        type: string
        value: fake.date_between
        arguments:
        - "-1y"
        - "today"
    actions:
      - name: create
        action: create
        frequency: 0.25
        action_condition: effect_only
```


# Where Condition
for now very simple and relies on spaces
<table>.<field> [==,!=,>=,<=, >, <] val

# deletes
In order to actually capture deletes, deletes will simply be marked by setting the change_type to 'D'
Can have two types of behaviour set in the config field delete_behaviour
If set to 'HARD' - after handling the update and exporting the value, the deleted record(s) will be hard deleted
If set to 'SOFT' - after handling will leave the record in the backend, however subsequent updates and deletes will be filtered out
This is done for all tables.
