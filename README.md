# SQL-toolchain

The chain of tools to make work with SQL easier

[![Build Status](https://travis-ci.org/WebSQL/sqltoolchain.svg?branch=master)](https://travis-ci.org/WebSQL/sqltoolchain)
[![Coverage Status](https://coveralls.io/repos/WebSQL/sqltoolchain/badge.svg?branch=master)](https://coveralls.io/r/WebSQL/sqltoolchain?branch=master)


* sql-preprocessor:<br/>
    supports:
    * macro-variables<br/>
        ```
          #define table_name "mytable"
          SELECT * from $table_name;`
        ```
    *  macro-functions<br/>
        ```
        #define quote(a) "a"
        SELECT UPPER(quote(a));
        ```
  
    *  conditions<br/>
        ```
        #define a 1
        #if a == 1
        SELECT * from t1;
        #else
        SELECT * from t2;
        #endif
        ```  
    *  includes<br/>
        ```
        #include "common.sql"
        ```
  
* sql-pygen<br/>
    (generate python code around SQL procedures)
    *  asynchronous and synchronous syntax supported.
    *  can extend to support other languages, in plans to support C++
    *  auto-detect r/o r/w procedures, raised errors etc.

    ```SQL
    CREATE PROCEDURE table1.insert (value VARCHAR(10)) COMMENT "returns object"
    BEGIN
        INSERT INTO table1 (value) VALUES(value);
        SELECT LAST_INSERT_ID() AS id;
    END$$
    ```

    -->
    table1.py<br/>
    ...<br/>
    ```python
    @coroutine
    def insert(connection, value=None):
        """
        insert, table1
        :param value: the value(VARCHAR(10), IN))
        :return (id,)
        """
        @coroutine
        def query(connection_):
            cursor = connection_.cursor()`
            try:
                yield from cursor.callproc(b"table1.insert", (value,))
                return (yield from cursor.fetchall())[0]
            finally:
                yield from cursor.close()
        try:
            return (yield from connection.execute(query))
        except Error as e:
            raise handle_error(exceptions, e)
    ```
