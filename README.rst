WSQL-SDK
========
.. image:: https://travis-ci.org/WebSQL/sdk.svg?branch=master
    :target: https://travis-ci.org/WebSQL/sdk

.. image:: https://coveralls.io/repos/WebSQL/sdk/badge.png?branch=master
    :target: https://coveralls.io/r/WebSQL/sdk?branch=master

The chain of tools that make work with SQL procedures easier.

wsql-trans:
--------------
The extensions above native SQL.

supports:
*********

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
Now supports python3.
The C++ under development.
Required `WSQL`_.

SQL
***
.. code-block:: sql

    CREATE PROCEDURE table1.insert (value VARCHAR(10))
    BEGIN
        INSERT INTO table1 (value) VALUES(value);
        SELECT LAST_INSERT_ID() AS id;
    END

Python3
*******

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
