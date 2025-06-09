# Example usage in user code
from mockpipe import MockPipe
from mockpipe.exporter import BaseExporter, Exporter
import xml.etree.ElementTree as ET
import os
from typing import List, Dict
import time


class XMLExporter(BaseExporter):
    """Custom XML exporter"""

    def export(self, table_name: str, values: List[Dict], format: str) -> None:
        if format.lower() != "xml":
            raise NotImplementedError("XMLExporter only supports XML format")
        self._export_xml(self.base_path, table_name, values)

    def _export_xml(self, base_path: str, table_name: str, values: List[Dict]) -> None:
        # Create directory if it doesn't exist
        os.makedirs(f"{base_path}/{table_name}", exist_ok=True)

        root = ET.Element("data")
        for row in values:
            record = ET.SubElement(root, "record")
            for key, value in row.items():
                field = ET.SubElement(record, key)
                field.text = str(value)

        tree = ET.ElementTree(root)
        filename = f"{base_path}/{table_name}/{table_name}_{str(time.time()).replace('.', '').ljust(17, '0')}.xml"
        tree.write(filename, encoding="utf-8", xml_declaration=True)


# Register the custom exporter
Exporter.register_exporter("xml", XMLExporter)

if __name__ == "__main__":

    mp = MockPipe(
        """
db_path: mockpipe.db
delete_behaviour: soft
inter_action_delay: 0.5

output:
  format: xml
  path: extract_xml

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

    actions:
      - name: create
        action: create
        frequency: 1
    """
    )

    # Run for 10 steps
    for _ in range(10):
        mp.step()
