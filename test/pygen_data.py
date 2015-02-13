# @copyright (c) 2002-2015 Acronis International GmbH. All rights reserved.
# since    $Id: $

__author__ = "Bulat Gaifullin (bulat.gaifullin@acronis.com)"


TEST_DATA = [
    {
        "sql": b"""
CREATE PROCEDURE `test_procedure1` ()
 COMMENT "args (c1 INT, c2 BINARY(255)); returns merge: object, object"
BEGIN
    SELECT 1 AS `a`;
    SELECT 2 AS `b`;
    CALL __throw("TestError", "test error")
END$$
""",
        "exceptions": """
from websql import UserError


class TestErrorError(UserError):
    pass
""",
        "aio": '''
from asyncio import coroutine
from websql import Error, handle_error
from websql.cluster import transaction
from . import exceptions


@coroutine
def test_procedure1(connection, args=None):
    """
    test the procedure1
    :param args: list of {c1(INT),c2(BINARY(255))})
    :return ('a', 'b')
    :raises: TestError
    """

    @coroutine
    def query(connection_):
        cursor = connection_.cursor()
        try:
            if args is None:
                return
            __args = ((x.get(y, None) for y in ("c1", "c2")) for x in args)
            yield from cursor.execute(b"DROP TEMPORARY TABLE IF EXISTS `args`; CREATE TEMPORARY TABLE `args`(`c1` INT, `c2` BINARY(255)) ENGINE=MEMORY;")
            yield from cursor.execute_many(b"INSERT INTO `args` (`c1`, `c2`) VALUES (%s, %s);", __args)
            yield from cursor.callproc(b"test_procedure1", ())
            __result = (yield from cursor.fetchall())[0]
            __result.update((yield from cursor.fetchall())[0])
            return __result
        finally:
            yield from cursor.close()

    try:
        return (yield from connection.execute(query))
    except Error as e:
        raise handle_error(exceptions, e)
''',

        "pure": '''
from websql import Error, handle_error
from websql.cluster import transaction
from . import exceptions


def test_procedure1(connection, args=None):
    """
    test the procedure1
    :param args: list of {c1(INT),c2(BINARY(255))})
    :return ('a', 'b')
    :raises: TestError
    """

    def query(connection_):
        with connection_.cursor() as cursor:
            if args is None:
                return
            __args = ((x.get(y, None) for y in ("c1", "c2")) for x in args)
            cursor.execute(b"DROP TEMPORARY TABLE IF EXISTS `args`; CREATE TEMPORARY TABLE `args`(`c1` INT, `c2` BINARY(255)) ENGINE=MEMORY;")
            cursor.execute_many(b"INSERT INTO `args` (`c1`, `c2`) VALUES (%s, %s);", __args)
            cursor.callproc(b"test_procedure1", ())
            __result = cursor.fetchall()[0]
            __result.update(cursor.fetchall()[0])
            return __result

    try:
        return connection.execute(query)
    except Error as e:
        raise handle_error(exceptions, e)
''',

    },
    {
        "sql": b"""
CREATE PROCEDURE `test_procedure2` (c1 INT, c2 VARCHAR(255)) COMMENT "returns array"
BEGIN
    SELECT `a` FROM t;
END$$
""",
        "exceptions": """
from websql import UserError
""",
        "aio": '''
@coroutine
def test_procedure2(connection, c1=None, c2=None):
    """
    test the procedure2
    :param c1: the c1(INT, IN))
    :param c2: the c2(VARCHAR(255), IN))
    :return ((\'a\',),)
    """

    @coroutine
    def query(connection_):
        cursor = connection_.cursor()
        try:
            yield from cursor.callproc(b"test_procedure2", (c1, c2))
            return (yield from cursor.fetchall())
        finally:
            yield from cursor.close()
''',

        "pure": '''
def test_procedure2(connection, c1=None, c2=None):
    """
    test the procedure2
    :param c1: the c1(INT, IN))
    :param c2: the c2(VARCHAR(255), IN))
    :return ((\'a\',),)
    """

    def query(connection_):
        with connection_.cursor() as cursor:
            cursor.callproc(b"test_procedure2", (c1, c2))
            return cursor.fetchall()
'''
    },
    {
        "sql": b"""
CREATE PROCEDURE `procedure3` ()
BEGIN
    DELETE FROM t;
END$$
""",
        "exceptions": """
from websql import UserError
""",
        "aio": '''
@coroutine
def procedure3(connection):
    """
    procedure3
    """

    @transaction
    @coroutine
    def query(connection_):
        cursor = connection_.cursor()
        try:
            yield from cursor.callproc(b"procedure3", ())
        finally:
            yield from cursor.close()
''',

        "pure": '''
def procedure3(connection):
    """
    procedure3
    """

    @transaction
    def query(connection_):
        with connection_.cursor() as cursor:
            cursor.callproc(b"procedure3", ())
'''
    },
    {
        "sql": b"""
CREATE PROCEDURE `table1.update` (i BIGINT) COMMENT "returns object, array"
BEGIN
    SELECT 1 AS `a`;
    SELECT b, c FROM t;
END$$
""",
        "filename": "table1.py",
        "exceptions": """
from websql import UserError
""",
        "aio": '''
@coroutine
def update(connection, i=None):
    """
    update the table1
    :param i: the i(BIGINT, IN))
    :return ((\'a\',), ([\'b\', \'c\'],))
    """

    @coroutine
    def query(connection_):
        cursor = connection_.cursor()
        try:
            yield from cursor.callproc(b"table1.update", (i,))
            return [
                (yield from cursor.fetchall())[0],
                (yield from cursor.fetchall()),
            ]
        finally:
            yield from cursor.close()
''',

        "pure": '''
def update(connection, i=None):
    """
    update the table1
    :param i: the i(BIGINT, IN))
    :return ((\'a\',), ([\'b\', \'c\'],))
    """

    def query(connection_):
        with connection_.cursor() as cursor:
            cursor.callproc(b"table1.update", (i,))
            return [
                cursor.fetchall()[0],
                cursor.fetchall(),
            ]
'''
    }
]
