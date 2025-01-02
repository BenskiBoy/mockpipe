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
      columns:
        - name: id
          type: integer
          primary_key: true
        - name: name
          type: string
          faker: name
        - name: email
          type: string
          faker: email
  actions:
    - table: users
      action: insert
      frequency: 1.0

  # Initialize Mockpipe with the configuration
  mp = mockpipe.Mockpipe(yaml_config)

Command line Usage
--------------------

.. code:: bash

  Usage: mockpipe [OPTIONS]

  Options:
    --config_create     generate a sample config file
    --config PATH       path to yaml config file
    --steps INTEGER     Number of steps to execute initially
    --run-time INTEGER  Time to run the mockpipe process in seconds
    --version           Show the version and exit.
    --help              Show this message and exit.

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


**Output**

+--------+------------+----------------+---------------+---------+------------------------+
| key    | value type | allowed values | default value | sample  | explanation            |
+========+============+================+===============+=========+========================+
| format | string     | [json, csv]    | json          | json    | file format output     |
+--------+------------+----------------+---------------+---------+------------------------+
| path   | path       | any            | extract       | extract | folder path for output |
+--------+------------+----------------+---------------+---------+------------------------+

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
| arugments | list       | any                                            | N/A           |- "-1y"              | Arguments to pass to faker functions  | See 'Field Value Usage' |
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
- improved yaml config validation
- improved logging
- increased test coverage
- simplyfy action usage and allow for duckdb functions
- support additional data output formats (e.g. xml, parquet)
- better sql typing support


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
