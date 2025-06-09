from mockpipe import MockPipe
import time

from mockpipe.imposter import fake
from faker.providers import BaseProvider


# Custom Faker provider to generate employee IDs
class MyProvider(BaseProvider):
    __provider__ = "custom_emp_id"

    def custom_emp_id(self):
        return "E-" + str(self.random_int(min=0, max=9999)).zfill(4)


if __name__ == "__main__":

    fake.add_provider(MyProvider)  # Add custom provider

    mp = MockPipe(
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
      - name: country
        type: string
        value: fake.country
      - name: zipcode
        type: string
        value: fake.zipcode
      - name: hire_status
        type: boolean
        value: static(true)

      - name: custom_emp_id
        type: string
        value: fake.custom_emp_id
    actions:
      - name: create
        action: create
        frequency: 1
    """
    )

    # Run for 10 steps
    for _ in range(10):
        mp.step()
