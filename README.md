# mockpipe
There's a lot of sample databases (for example the projects namesake, Northwind) out there and lots of ways to generate some dummy data (faker), but i couldn't find much in the way of dynamically generating realistic CDC data.
This is an attampt at that.

From a yaml config a set of sample tables can be defined, using dummy default values for any newly generated rows along with a set of actions that can be performed with a certain frequency.

The dummy values actually invoke the Faker library to generate somewhat realistic entries, along with support for other data types that may refer to existing values within the table or other tables so that relationships can be maintained.

Data is persisted onto a duckdb database so the outputs can be persisted between executions and support any other analysis/queries you may want to do.