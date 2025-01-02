from mockpipe import MockPipe
import time

from faker.providers import BaseProvider

_kebab_types = OrderedDict(
    [
        (
            "Doner",
            65,
        ),
        (
            "Shish",
            30,
        ),
        (
            "Adana",
            5,
        ),
        (
            "Kofte",
            20,
        ),
    ]
)


class KebabTypeProvider(BaseProvider):
    def kebab_types(self, length: int = None) -> List[str]:
        return self.random_elements(
            _kebab_types, length, unique=False, use_weighting=True
        )

    def kebab_type(self) -> str:
        return self.kebab_types(1)[0]


if __name__ == "__main__":

    # Just start running from a config file
    # mp = MockPipe("config.yaml")

    # Or just pass in a yaml string
    mp = MockPipe(
        """
db_path: simple.db
delete_behaviour: soft
inter_action_delay: 0.1
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
        value: fake.kebab_types
    actions:
      - name: create
        action: create
        frequency: 0.25
        effect: bar.create(foo_id=id, some_other_inherit_value=some_value)
        effect_count: 1,5
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
        is_pk: true
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
        effect_count: inherit
        action_condition: effect_only

  - name: baz
    fields:
      - name: some_other_id
        type: int
        value: inherit
        # is_pk: true
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
     
    """
    )

    # Run for 10 steps
    for _ in range(10):
        mp.step()

    # Run for 10 seconds
    mp.start()
    time.sleep(10)
    mp.stop()

    # execute a specific action
    mp.execute_action(table=mp.tables["foo"], action=mp.tables["foo"].actions["create"])
