::

  ███╗   ███╗ ██████╗  ██████╗██╗  ██╗██████╗ ██╗██████╗ ███████╗
  ████╗ ████║██╔═══██╗██╔════╝██║ ██╔╝██╔══██╗██║██╔══██╗██╔════╝
  ██╔████╔██║██║   ██║██║     █████╔╝ ██████╔╝██║██████╔╝█████╗  
  ██║╚██╔╝██║██║   ██║██║     ██╔═██╗ ██╔═══╝ ██║██╔═══╝ ██╔══╝  
  ██║ ╚═╝ ██║╚██████╔╝╚██████╗██║  ██╗██║     ██║██║     ███████╗
  ╚═╝     ╚═╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚══════╝

|pypi| |build| |license|

-------------

MockPipe
-------------

There's a lot of sample databases out there and lots of ways to generate some dummy data (i.e. faker, which this project uses), but i couldn't find much in the way of dynamically generating realistic data that could be used to generate some scenarios that one might actually find coming out of a operational systems CDC feed.
This is an attampt to create a utility/library that can be used to setup some .

From a yaml config a set of sample tables can be defined, using dummy default values for any newly generated rows along with a set of actions that can be performed with a certain frequency.

The dummy values actually invoke the Faker library to generate somewhat realistic entries, along with support for other data types that may refer to existing values within the table or other tables so that relationships can be maintained.

Data is persisted onto a duckdb database so the outputs can be persisted between executions and support any other analysis/queries you may want to do.


Features
-------------
- **Dynamic Data Generation**: Generate sample tables from a YAML configuration, using dummy default values for newly generated rows.
- **Faker Integration**: Leverage the Faker library to create realistic entries.
- **Relationship Maintenance**: Support for data types that refer to existing values within the same table or other tables, ensuring relationships are preserved.
- **Action Frequency**: Define a set of actions to be performed with a certain frequency.
- **Persistence**: Data is persisted in a DuckDB database, allowing outputs to be saved between executions and enabling further analysis or queries.

Installation
-------------

To install Mockpipe, you can use pip:

.. code:: bash

  pip install mockpipe

Basic Usage
-------------

.. code:: python

  import mockpipe

  # Define your YAML configuration
  yaml_config = """
  tables:
    - name: users
      fields:
        - name: id
          type: int
          value: increment
          is_pk: true
        - name: name
          type: string
          value: fake.name
        - name: email
          type: string
          value: fake.email
      actions:
        - name: create
          action: create
          frequency: 1.0
  """

  # Initialize MockPipe with the configuration
  mp = mockpipe.MockPipe(yaml_config)

  # Run for 10 steps
  for _ in range(10):
      mp.step()

Command line Usage
--------------------

.. code:: bash

  Usage: mockpipe [OPTIONS]

  Options:
    --config-create      generate a sample config file
    --config PATH        path to yaml config file
    --steps INTEGER       Number of steps to execute initially
    --run-time INTEGER   Time to run the mockpipe process in seconds
    --dry-run            Validate the config file and exit without running anything
    --output-format TEXT Override the config file's output.format (e.g. json, csv, parquet, webhook)
    --output-path TEXT   Override the config file's output.path
    --output-url TEXT    Override the config file's output.url (used by the webhook format)
    --verbose            Enable verbose logging
    --version            Show the version and exit.
    --help               Show this message and exit.

Config Specification
--------------------
**Top Level Keys**

+--------------------+------------+----------------+---------------+-----------+---------------------------------------------------------------------------------------------------------+
| key                | value type | allowed values | default value | sample    | explanation                                                                                             |
+====================+============+================+===============+===========+=========================================================================================================+
| db_path            | path       | any            | mockpipe.db   | sample.db | path of duckdb db                                                                                       |
+--------------------+------------+----------------+---------------+-----------+---------------------------------------------------------------------------------------------------------+
| delete_behaviour   | string     | [soft, hard]   | soft          | soft      | whether deleted records will be marked as deleted with 'D' or actually hard deleted in the persisted db |
+--------------------+------------+----------------+---------------+-----------+---------------------------------------------------------------------------------------------------------+
| inter_action_delay | float      | 0.0 ->         | 0.5           | 0.1       | delay between each action                                                                               |
+--------------------+------------+----------------+---------------+-----------+---------------------------------------------------------------------------------------------------------+
| output             | table      |                |               |           | output format                                                                                           |
+--------------------+------------+----------------+---------------+-----------+---------------------------------------------------------------------------------------------------------+
| full_load          | table      |                | N/A           |           | periodic full-table snapshot export, alongside the incremental change stream. See 'Full Load'           |
+--------------------+------------+----------------+---------------+-----------+---------------------------------------------------------------------------------------------------------+
| seed               | int        | any            | N/A (random)  | 42        | seed for reproducible runs. See 'Reproducible Runs (seed)'                                              |
+--------------------+------------+----------------+---------------+-----------+---------------------------------------------------------------------------------------------------------+


**Output**

+------------+------------+-------------------------------+---------------+----------------------------+-------------------------------------------------------------------+
| key        | value type | allowed values                | default value | sample                     | explanation                                                       |
+============+============+===============================+===============+============================+===================================================================+
| format     | string     | [json, csv, parquet, webhook] | json          | json                       | output format                                                     |
+------------+------------+-------------------------------+---------------+----------------------------+-------------------------------------------------------------------+
| path       | path       | any                           | extract       | extract                    | folder path for output (unused for webhook)                       |
+------------+------------+-------------------------------+---------------+----------------------------+-------------------------------------------------------------------+
| batch_size | int        | 1 ->                          | 1             | 50                         | buffer this many changed rows per table before writing a file     |
+------------+------------+-------------------------------+---------------+----------------------------+-------------------------------------------------------------------+
| url        | string     | any URL                       | N/A           | http://localhost:8080/hook | HTTP(S) endpoint to POST rows to. Required when format is webhook |
+------------+------------+-------------------------------+---------------+----------------------------+-------------------------------------------------------------------+

Note: without ``batch_size``, mockpipe writes one output file per changed row, which can produce a large number of small files over a long run. Buffered rows are also written out when the process stops (or via ``MockPipe.flush_exports()`` if you only ever call ``step()`` directly).

Note: the ``webhook`` format POSTs each exported batch as JSON (``{"table": <table_name>, "rows": [...]}``) to ``output.url``, instead of writing a file - useful for testing a downstream consumer directly. ``output.path`` is unused for this format.

**Reproducible Runs (seed)**

Set the top-level ``seed`` key to a fixed integer to make a run reproducible - useful for turning a flaky/failing test run into something you can reliably re-run. With the same ``seed`` and the same config, Faker-generated field values and action/table selection will be identical between runs.

Note: ``table_random`` lookups rely on DuckDB's own ``USING SAMPLE`` clause, which DuckDB does not guarantee is bit-for-bit reproducible even with a fixed seed (an upstream engine limitation) - mockpipe still seeds it, but treat that part as best-effort rather than guaranteed.

**Full Load**

If the ``full_load`` key is present, every ``full_load.frequency`` recorded changes (across all tables combined), mockpipe exports a full snapshot of each table's current rows in addition to the normal incremental export for the change that just happened. This is useful for downstream consumers that periodically want a fresh full baseline rather than only ever seeing incremental changes.

+-----------------+------------+----------------+---------------+--------+-------------------------------------------------------------+
| key             | value type | allowed values | default value | sample | explanation                                                 |
+=================+============+================+===============+========+=============================================================+
| include_deletes | bool       | any            | false         | true   | whether soft-deleted rows are included in the full snapshot |
+-----------------+------------+----------------+---------------+--------+-------------------------------------------------------------+
| frequency       | int        | 1 ->           | 100           | 50     | how many recorded changes between each full snapshot export |
+-----------------+------------+----------------+---------------+--------+-------------------------------------------------------------+

Note: ``include_deletes: true`` is incompatible with ``delete_behaviour: hard``, since hard-deleted rows no longer exist to include.

mockpipe also creates its own ``_mockpipe_metadata`` table in your ``db_path`` database (alongside the tables you define). It tracks how many changes have been recorded so far, so that ``full_load``'s schedule resumes correctly if you re-open the same ``db_path`` in a later run instead of restarting from zero. You can safely ignore this table - it isn't exported and isn't part of the data mockpipe generates for you.

**Tables**

+---------+------------+----------------+---------------+-----------+---------------------------------------+
| key     | value type | allowed values | default value | sample    | explanation                           |
+=========+============+================+===============+===========+=======================================+
| name    | string     | any            | N/A           | employees | table name used. Also used for output |
+---------+------------+----------------+---------------+-----------+---------------------------------------+
| fields  | table      |                |               |           | List of fields in table               |
+---------+------------+----------------+---------------+-----------+---------------------------------------+
| actions | table      |                |               |           | List of actions within table          |
+---------+------------+----------------+---------------+-----------+---------------------------------------+

**Fields**

+-----------+------------+------------------------------------------------+---------------+---------------------+---------------------------------------+-------------------------+
| key       | value type | allowed values                                 | default value | sample              | explanation                           | Note                    |
+===========+============+================================================+===============+=====================+=======================================+=========================+
| name      | string     | any                                            | N/A           | order_date          | table name used. Also used for output |                         |
+-----------+------------+------------------------------------------------+---------------+---------------------+---------------------------------------+-------------------------+
| type      | string     | [string, int, float, boolean]                  | N/A           | string              | List of fields in table               |                         |
+-----------+------------+------------------------------------------------+---------------+---------------------+---------------------------------------+-------------------------+
| value     | string     | [increment, static(*), table_random(), fake.*] | N/A           | fake.date_between   | List of actions within table          | See 'Field Value Usage' |
+-----------+------------+------------------------------------------------+---------------+---------------------+---------------------------------------+-------------------------+
| arguments | list       | any                                            | N/A           |- "-1y"              | Arguments to pass to faker functions  | See 'Field Value Usage' |
|           |            |                                                |               |- "today"            |                                       |                         |
+-----------+------------+------------------------------------------------+---------------+---------------------+---------------------------------------+-------------------------+

**Actions**

+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+
| key                 | value type    | allowed values                                   | default value | sample                                                       | explanation                                                                                                      | Note                |
+=====================+===============+==================================================+===============+==============================================================+==================================================================================================================+=====================+
| name                | string        | any                                              | N/A           | update_order_status                                          | name of action                                                                                                   |                     |
+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+
| field               | string        | any                                              | N/A           | order_status                                                 | field which gets updated                                                                                         |                     |
+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+
| action              | string        | [create, delete, set]                            | N/A           | set                                                          | type of action to perform                                                                                        |                     |
+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+
| value               | string        | [increment, static(*), table_random(), fake.*]   | N/A           | fake.random_element                                          | value to set field to                                                                                            |                     |
+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+
| arguments           | list          | any                                              | N/A           | ('pending', 'completed', 'shipped', 'delivered')             | if using faker, arguments to pass                                                                                |                     |
+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+
| frequency           | float         | 0->1                                             | N/A           | 0.25                                                         | relative frequency of action                                                                                     |                     |
+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+
| where_condition     | string        | <table>.<value> == <condition>                   | N/A           | products.product_id == table_random(products, product_id, 0) | where condition to limit which rows in table to apply action to                                                  | See where condition |
+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+
| action_condition    | string        | EFFECT_ONLY                                      | N/A           | EFFECT_ONLY                                                  | used to specify if the action is only ever to be invoked by another action (i.e., an effect)                     |                     |
+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+
| effect              | string        | <table>.<action>(<target_col>=<source_col>, ...) | N/A           | product.product_count(order_id=order_id)                     | After the specified action is executed, another action can be invoked, passing values onwards to the next action | See Effect          |
+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+
| effect_count        | [int, string] | 0->max(int), inherit                             | N/A           | inherit                                                      | if effect is set, how many times to invoke the next effect                                                       | See Effect          |
+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+
| effect_count_random | string        | <min>,<max>                                      | N/A           | 1,5                                                          | if effect is set, how many times to invoke the next effect                                                       | See Effect          |
+---------------------+---------------+--------------------------------------------------+---------------+--------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------+---------------------+


**Field Values**

+-------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| type        | increment                                                                                                                                                                             |
+=============+=======================================================================================================================================================================================+
| explanation | Will only wok for integer fields. It acts as you'd expect, incrementing the value by 1 for each new row generated and selecting a random value from the specified table respectively. |
+-------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| syntax      | ``increment``                                                                                                                                                                         |
+-------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| examples    | ``increment``                                                                                                                                                                         |
+-------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

+-------------+------------------------------------------------------------------------------------------------------------------------------------+
| type        | static                                                                                                                             |
+=============+====================================================================================================================================+
| explanation | Will set a static value on each new row generated. This can be any value you want, but it will be the same for each row generated. |
+-------------+------------------------------------------------------------------------------------------------------------------------------------+
| syntax      | ``static(<value>)``                                                                                                                |
+-------------+------------------------------------------------------------------------------------------------------------------------------------+
| examples    | ``static(false), static(100), static('pending')``                                                                                  |
+-------------+------------------------------------------------------------------------------------------------------------------------------------+


+-------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| type        | table_random                                                                                                                                                                               |
+=============+============================================================================================================================================================================================+
| explanation | Will select a random value from the specified table for each new row generated. Note, will only select non-deleted rows. It's important to set a default value in case the table is empty. |
+-------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| syntax      | ``table_random(<table_name>, <column_name>, <default_value>)``                                                                                                                             |
+-------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| examples    | ``table_random(products, product_id, 0)``                                                                                                                                                  |
+-------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


+-------------+-----------------------------------------------------------------------------------------------------------------------+
| type        | fake.*                                                                                                                |
+=============+=======================================================================================================================+
| explanation | Will generate a value using the faker library. The arguments key can be used to pass arguments to the faker function. |
+-------------+-----------------------------------------------------------------------------------------------------------------------+
| syntax      | ``fake.<faker_function>``                                                                                             |
+-------------+-----------------------------------------------------------------------------------------------------------------------+
| examples    | fake.company                                                                                                          |
+-------------+-----------------------------------------------------------------------------------------------------------------------+

Note: for ``fake.random_element`` (or any other faker method accepting a set of choices), passing a dict-literal string as the argument instead of a tuple gives each option a weighted probability instead of a uniform chance, e.g.:

.. code:: yaml

  value: fake.random_element
  arguments:
    - "{'pending': 0.05, 'shipped': 0.05, 'delivered': 0.9}"

The values don't need to sum to 1 - they're relative weights, not strict probabilities.


**Effects**

The effect is used to specify that after the specified action is executed, another action can be invoked, passing values onwards to the next action.
This can be useful for chaining actions together to create one to one, one to many relationships, you can also specify how many times to invoke the next 

effect: 

+-------------+--------------------------------------------------------------------------------+
| explanation | Which action to invoke after the current action is executed.                   |
+-------------+--------------------------------------------------------------------------------+
| syntax      | ``<table>.<action>(<target_col>=<source_col>, <target_col=<source_col>, ...)`` |
+-------------+--------------------------------------------------------------------------------+
| example     | ``effect: product.product_count(order_id=order_id)``                           |
+-------------+--------------------------------------------------------------------------------+


effect_count:

+-------------+-----------------------------------------------------------------------------------------------------------------+
| explanation | If the effect is set, how many times to invoke the next effect. Note, can not be used with effect_count_random. |
+-------------+-----------------------------------------------------------------------------------------------------------------+
| syntax      | ``<int>``                                                                                                       |
+-------------+-----------------------------------------------------------------------------------------------------------------+
| example     | ``1``                                                                                                           |
+-------------+-----------------------------------------------------------------------------------------------------------------+



effect_count_random:

+-------------+----------------------------------------------------------------------------------------------------------+
| explanation | If the effect is set, how many times to invoke the next effect. Note, can not be used with effect_count. |
+-------------+----------------------------------------------------------------------------------------------------------+
| syntax      | ``<min>,<max>``                                                                                          |
+-------------+----------------------------------------------------------------------------------------------------------+
| example     | ``1,5``                                                                                                  |
+-------------+----------------------------------------------------------------------------------------------------------+


action_condition:

Used to specify if the action is only ever to be invoked by another action (i.e., an effect).

+-------------+-----------------------------------------------------------------------------------------------+
| explanation | Used to specify if the action is only ever to be invoked by another action (i.e., an effect). |
+-------------+-----------------------------------------------------------------------------------------------+
| syntax      | ``EFFECT_ONLY``                                                                               |
+-------------+-----------------------------------------------------------------------------------------------+
| example     | ``EFFECT_ONLY``                                                                               |
+-------------+-----------------------------------------------------------------------------------------------+

**Where Condition**

+-------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| explanation                   | The where condition is used to limit which rows in the table an action is applied to. It can be set to a filter, i.e. where status=='pending' or it can perform a lookup to another table to get the value to filter on. |
+-------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| syntax                        | ``<table>.<value> == / != / >= / <= / > / < <condition>``                                                                                                                                                                |
+-------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| table_random condition syntax | ``table_random(<table_name>, <column_name>, <default_value>)``                                                                                                                                                           |
+-------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| static syntax                 | ``static(<value>)``                                                                                                                                                                                                      |
+-------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| table_random example          | ``products.product_id == table_random(orders, product_id, 0)``                                                                                                                                                           |
+-------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| static example                | ``products.product_id == static(1)``                                                                                                                                                                                     |
+-------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


Future Enhancements
--------------------
- simplify action usage and allow for duckdb functions
- move from raw SQL string concatenation to parameterized queries
- additional exporters (e.g. direct-to-Postgres/S3, message queues)



Contributing
-------------

Contributions are welcome, Please open an issue or submit a pull request on GitHub.


License
-------------

This project is licensed under the MIT License. See the LICENSE file for details.


Acknowledgements
-----------------

- [Faker](https://github.com/joke2k/faker) - For generating realistic dummy data.
- [DuckDB](https://duckdb.org/) - For data persistence and analysis.


.. |pypi| image:: https://img.shields.io/pypi/v/mockpipe.svg?style=flat-square&label=version
    :target: https://pypi.org/project/mockpipe/
    :alt: Latest version released on PyPI

.. |build| image:: https://github.com/BenskiBoy/mockpipe/actions/workflows/build.yml/badge.svg
    :target: https://github.com/BenskiBoy/mockpipe/actions/workflows/build.yml
    :alt: Build status of the master branch

.. |license| image:: https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square
    :target: https://raw.githubusercontent.com/BenskiBoy/mockpipe/master/LICENSE
    :alt: Package license
