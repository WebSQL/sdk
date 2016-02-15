"""
This file is part of WSQL-SDK

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__author__ = "@bg"


TEST_DATA = [
    {
        "sql": """
CREATE PROCEDURE `test_procedure1` ()
 COMMENT "args (c1 INT, c2 BINARY(255)); returns union"
BEGIN
    SELECT 1 AS `a`;
    CALL __test_procedure1();
    IF FOUND_ROWS() == 0 THEN CALL __throw("TestError", CONCAT("test error: ", "test")); END IF;
    CALL __throw("TestError", "test");
END$$

CREATE PROCEDURE `__test_procedure1` ()
BEGIN
    SELECT 2 AS `b`;
END$$

CREATE PROCEDURE `test.__procedure1` ()
BEGIN
END$$

CREATE PROCEDURE `test_procedure2` ()
BEGIN
END$$
""",
        "exceptions": """
from wsql import UserError


class TestError(UserError):
    pass
""",
        "python3_aio": '''
from asyncio import coroutine
from wsql import Error, handle_error
from wsql.cluster import transaction
from wsql.converters import ObjectDict

from . import exceptions


@coroutine
def test_procedure1(connection, args=None):
    """
    test the procedure1

    :param connection: the connection object
    :param args: list of {c1(INT),c2(BINARY(255))}
    :returns: ("a", "b")
    :raises: TestError
    """

    @coroutine
    def __query(__connection):
        __cursor = __connection.cursor()
        try:
            if args is None:
                return
            __args = ((x.get(y, None) for y in ("c1", "c2")) for x in args)
            yield from __cursor.execute(b"DROP TEMPORARY TABLE IF EXISTS `args`;")
            yield from __cursor.execute(b"CREATE TEMPORARY TABLE `args`(`c1` INT, `c2` BINARY(255)) ENGINE=MEMORY;")
            yield from __cursor.executemany(b"INSERT INTO `args` (`c1`, `c2`) VALUES (%s, %s);", __args)
            yield from __cursor.callproc(b"test_procedure1", ())
            __result = (yield from __cursor.fetchxall())[0]
            __result.update((yield from __cursor.fetchxall())[0])
            return __result
        finally:
            yield from __cursor.close()

    try:
        return (yield from connection.execute(__query))
    except Error as e:
        raise handle_error(exceptions, e)
''',

        "python3": '''
from wsql import Error, handle_error
from wsql.cluster import transaction
from wsql.converters import ObjectDict

from . import exceptions


def test_procedure1(connection, args=None):
    """
    test the procedure1

    :param connection: the connection object
    :param args: list of {c1(INT),c2(BINARY(255))}
    :returns: ("a", "b")
    :raises: TestError
    """

    def __query(__connection):
        with __connection.cursor() as __cursor:
            if args is None:
                return
            __args = ((x.get(y, None) for y in ("c1", "c2")) for x in args)
            __cursor.execute(b"DROP TEMPORARY TABLE IF EXISTS `args`;")
            __cursor.execute(b"CREATE TEMPORARY TABLE `args`(`c1` INT, `c2` BINARY(255)) ENGINE=MEMORY;")
            __cursor.executemany(b"INSERT INTO `args` (`c1`, `c2`) VALUES (%s, %s);", __args)
            __cursor.callproc(b"test_procedure1", ())
            __result = __cursor.fetchxall()[0]
            __result.update(__cursor.fetchxall()[0])
            return __result

    try:
        return connection.execute(__query)
    except Error as e:
        raise handle_error(exceptions, e)
''',

    },
    {
        "sql": """
CREATE PROCEDURE `test_procedure2` (c1 INT, c2 VARCHAR(255))
BEGIN
    SELECT `a` FROM t; -- > array
END$$
""",
        "python3_aio": '''
@coroutine
def test_procedure2(connection, c1=None, c2=None):
    """
    test the procedure2

    :param connection: the connection object
    :param c1: the c1(INT, IN)
    :param c2: the c2(VARCHAR(255), IN)
    :returns: [("a",)]
    """

    @coroutine
    def __query(__connection):
        __cursor = __connection.cursor()
        try:
            yield from __cursor.callproc(b"test_procedure2", (c1, c2))
            return (yield from __cursor.fetchxall())
        finally:
            yield from __cursor.close()
''',

        "python3": '''
def test_procedure2(connection, c1=None, c2=None):
    """
    test the procedure2

    :param connection: the connection object
    :param c1: the c1(INT, IN)
    :param c2: the c2(VARCHAR(255), IN)
    :returns: [("a",)]
    """

    def __query(__connection):
        with __connection.cursor() as __cursor:
            __cursor.callproc(b"test_procedure2", (c1, c2))
            return __cursor.fetchxall()
'''
    },
    {
        "sql": """
CREATE PROCEDURE `procedure3` ()
BEGIN
    DELETE FROM t;
END$$
""",
        "python3_aio": '''
@coroutine
def procedure3(connection):
    """
    procedure3

    :param connection: the connection object
    """

    @transaction
    @coroutine
    def __query(__connection):
        __cursor = __connection.cursor()
        try:
            yield from __cursor.callproc(b"procedure3", ())
        finally:
            yield from __cursor.close()
''',

        "python3": '''
def procedure3(connection):
    """
    procedure3

    :param connection: the connection object
    """

    @transaction
    def __query(__connection):
        with __connection.cursor() as __cursor:
            __cursor.callproc(b"procedure3", ())
'''
    },
    {
        "sql": """
CREATE PROCEDURE `table1.update` (i BIGINT)
BEGIN
    SELECT 1 AS `a`; -- > object
    SELECT b, c FROM t; -- > array
END$$
""",
        "filename": "table1.py",
        "python3_aio": '''
@coroutine
def update(connection, i=None):
    """
    update the table1

    :param connection: the connection object
    :param i: the i(BIGINT, IN)
    :returns: (("a",), [("b", "c")])
    """

    @coroutine
    def __query(__connection):
        __cursor = __connection.cursor()
        try:
            yield from __cursor.callproc(b"table1.update", (i,))
            return (
                (yield from __cursor.fetchxall())[0],
                (yield from __cursor.fetchxall()),
            )
        finally:
            yield from __cursor.close()
''',

        "python3": '''
def update(connection, i=None):
    """
    update the table1

    :param connection: the connection object
    :param i: the i(BIGINT, IN)
    :returns: (("a",), [("b", "c")])
    """

    def __query(__connection):
        with __connection.cursor() as __cursor:
            __cursor.callproc(b"table1.update", (i,))
            return (
                __cursor.fetchxall()[0],
                __cursor.fetchxall(),
            )
'''
    },
    {
        "sql": """
CREATE PROCEDURE `table1.query` (i BIGINT) COMMENT "returns union"
BEGIN
    SELECT 1 AS `a`; -- > object
    SELECT b, c FROM t; -- > items:array
END$$
""",
        "filename": "table1.py",
        "python3_aio": '''
@coroutine
def query(connection, i=None):
    """
    query the table1

    :param connection: the connection object
    :param i: the i(BIGINT, IN)
    :returns: ("a", "items.b", "items.c")
    """

    @coroutine
    def __query(__connection):
        __cursor = __connection.cursor()
        try:
            yield from __cursor.callproc(b"table1.query", (i,))
            __result = (yield from __cursor.fetchxall())[0]
            __result.update(ObjectDict(items=(yield from __cursor.fetchxall())))
            return __result
        finally:
            yield from __cursor.close()
''',

        "python3": '''
def query(connection, i=None):
    """
    query the table1

    :param connection: the connection object
    :param i: the i(BIGINT, IN)
    :returns: ("a", "items.b", "items.c")
    """

    def __query(__connection):
        with __connection.cursor() as __cursor:
            __cursor.callproc(b"table1.query", (i,))
            __result = __cursor.fetchxall()[0]
            __result.update(ObjectDict(items=__cursor.fetchxall()))
            return __result

'''
    },
    {
        "sql": """
-- CONSTANT THIS_IS_CONST_1 1
-- CONSTANT CONST2 abc(1)

CREATE TABLE IF NOT EXISTS `table2` (
 column_enum ENUM('one', 'two'), column_set SET('red', 'blue', 'green')
);

CREATE PROCEDURE `table2.query` (i BIGINT)
BEGIN
    SELECT $C1 AS `a`;
END$$
""",
        "filename": "table2.py",
        "constants": """
CONST2 = 'abc(1)'

THIS_IS_CONST_1 = 1
""",
        "python3_aio": '''\
from enum import Enum


class ColumnEnum(Enum):
    one = 'one'
    two = 'two'


class ColumnSet(set):
    __choice = frozenset(('blue', 'green', 'red'))

    def __init__(self, v):
        nv = set(v) & self.__choice
        if len(nv) != len(v):
            raise ValueError("unexpected value %s" % nv)
        self.__value = nv

    @property
    def value(self):
        return self.__value


@coroutine
def query(connection, i=None):
    """
    query the table2

    :param connection: the connection object
    :param i: the i(BIGINT, IN)
    """

    @coroutine
    def __query(__connection):
        __cursor = __connection.cursor()
        try:
            yield from __cursor.callproc(b"table2.query", (i,))
        finally:
            yield from __cursor.close()
''',

        "python3": '''\
from enum import Enum


class ColumnEnum(Enum):
    one = 'one'
    two = 'two'


class ColumnSet(set):
    __choice = frozenset(('blue', 'green', 'red'))

    def __init__(self, v):
        nv = set(v) & self.__choice
        if len(nv) != len(v):
            raise ValueError("unexpected value %s" % nv)
        self.__value = nv

    @property
    def value(self):
        return self.__value


def query(connection, i=None):
    """
    query the table2

    :param connection: the connection object
    :param i: the i(BIGINT, IN)
    """

    def __query(__connection):
        with __connection.cursor() as __cursor:
            __cursor.callproc(b"table2.query", (i,))

'''
    }
]
