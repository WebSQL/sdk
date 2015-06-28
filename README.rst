WSQL-SDK
========
.. image:: https://travis-ci.org/WebSQL/sdk.svg?branch=master
    :target: https://travis-ci.org/WebSQL/sdk

.. image:: https://coveralls.io/repos/WebSQL/sdk/badge.png?branch=master
    :target: https://coveralls.io/r/WebSQL/sdk?branch=master

The chain of tools that make work with SQL procedures easier.

Syntax
******
* *#include "<filename>"* - include the specified filename, the absolute and relative urls supported.
* *#define name <value>*  - specify the value, that can be used as *$name*
* *#define name(arg1, ..., argN)* - the function, that can be used as *$name(a1,...aN)*
* *#undef name* - undefine previously defined instruction
* *#if condition expression else alternative* - conditional expressions
* *SELECT ... ; -- > array* - hint, that informs about query returns more that one element
* *SELECT ... ; -- > object* - hint, that informs about query returns exactly one element
* *COMMENT "returns union"* - hint, to merge all objects from results sets to one
* *COMMENT "<table name> (<colum name column type>,...);"* - hint, that allow to pass the list of arguments to procedure via temporary table

wsql-trans:
-----------
The extensions above native SQL.

supports:
#########

* macros

.. code-block::
 
    #define table_name "mytable"
    select * from $table_name;


* macro-functions

.. code-block:: sql

    #define quote(a) "a"
    select upper(quote(a));

  
* conditions

.. code-block:: sql

    #define a 1
    #if a == 1
    select * from t1;
    #else
    select * from t2;
    #endif

* includes

.. code-block:: sql

    #include "common.sql"

wsql-codegen:
-------------

Generate the native code to work with SQL procedures.
Now supports python3 native and aio.
The C++ under development.
Required `WSQL`_.

Hints
#####
* *SELECT ... ; -- > array* - hint, that informs about query returns more that one element
* *SELECT ... ; -- > object* - hint, that informs about query returns exactly one element
* *COMMENT "returns union"* - hint, to merge all objects from results sets to one
* *COMMENT "<table name> (<colum name column type>,...);"* - hint, that allow to pass the list of arguments to procedure via temporary table


SQL
###
.. code-block:: sql

    CREATE PROCEDURE table1.insert (value VARCHAR(10))
    BEGIN
        INSERT INTO table1 (value) VALUES(value);
        SELECT LAST_INSERT_ID() AS id;
    END

Python3
#######

.. code-block:: python

    @coroutine
    def insert(connection, value=None):
        """
        insert, table1
        :param value: the value(VARCHAR(10), IN))
        :return (id,)
        """
        @coroutine
        def __query(__connection):
            __cursor = __connection.cursor()
            try:
                yield from __cursor.callproc(b"procedure4", (value,))
                return (yield from __cursor.fetchall())[0]
            finally:
                yield from __cursor.close()
        try:
            return (yield from connection.execute(__query))
        except Error as e:
            raise handle_error(exceptions, e)


.. _`WSQL`: http://www.mysql.com/