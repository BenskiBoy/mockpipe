# you can also create custom providers to generate data

import mockpipe
from mockpipe import fake  # NOTE: You need to import fake from mockpipe.

from collections import OrderedDict
from typing import List

from faker.providers import BaseProvider

_business_areas = OrderedDict(
    [
        (
            "BUSINESS",
            0.45,
        ),
        (
            "HR",
            0.35,
        ),
        (
            "IT",
            0.15,
        ),
        (
            "DELIVERY",
            0.05,
        ),
    ]
)


class CustomTypeProvider(BaseProvider):
    def business_area(self) -> str:
        """return a random business area, truth be told you could just use the faker provider for this, but this is just an example

        Returns:
            str: a random business area
        """
        return self.random_elements(
            _business_areas, 1, unique=False, use_weighting=True
        )[0]

    def custom_emp_id(self) -> int:
        """return some custom id, NOTE, this may provide duplicates. You could easily add some logic to prevent that if needed.

        Returns:
            int: some random id you might get from some prod system
        """
        return "E" + str(self.random_int(min=1, max=1000000000)).zfill(10)


if __name__ == "__main__":

    # Note, you need to add the custom provider BEFORE initializing MockPipe
    fake.add_provider(CustomTypeProvider)

    mp = mockpipe.MockPipe(
        """
db_path: mockpipe.db
delete_behaviour: soft
inter_action_delay: 0.5

output:
  format: json
  path: extract_json

tables:
  - name: employees
    fields:
      - name: id
        type: int
        value: increment
        is_pk: true
      - name: manager_id
        type: int
        value: table_random(employees, id, 0)
      - name: name
        type: string
        value: fake.name
      - name: address
        type: string
        value: fake.address
      - name: business_area
        type: string
        value: fake.business_area # hey hey, look at that!
      - name: custom_emp_id
        type: string
        value: fake.custom_emp_id # hey hey, also look at that!
    actions:
      - name: create
        action: create
        frequency: 0.25
      - name: remove
        action: remove
        frequency: 0.25
        where_condition: employees.id == table_random(employees, id, 0)
"""
    )

    mp.start()
