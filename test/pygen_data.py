"""
Copyright (c) 2015 WebSQL
This file is part of sqltoolchain

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
        "sql": b"""
CREATE PROCEDURE `test_procedure1` ()
 COMMENT "args (c1 INT, c2 BINARY(255)); returns union"
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
        "pyaio": '''
from asyncio import coroutine
from websql import Error, handle_error
from websql.cluster import transaction
from . import exceptions


@coroutine
def test_procedure1(connection, args=None):
    """
    test the procedure1
    :param args: list of {c1(INT),c2(BINARY(255))})
    :return ("a", "b")
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
            yield from __cursor.execute_many(b"INSERT INTO `args` (`c1`, `c2`) VALUES (%s, %s);", __args)
            yield from __cursor.callproc(b"`test_procedure1`", ())
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

        "pynative": '''
from websql import Error, handle_error
from websql.cluster import transaction
from . import exceptions


def test_procedure1(connection, args=None):
    """
    test the procedure1
    :param args: list of {c1(INT),c2(BINARY(255))})
    :return ("a", "b")
    :raises: TestError
    """

    def __query(__connection):
        with __connection.cursor() as __cursor:
            if args is None:
                return
            __args = ((x.get(y, None) for y in ("c1", "c2")) for x in args)
            __cursor.execute(b"DROP TEMPORARY TABLE IF EXISTS `args`;")
            __cursor.execute(b"CREATE TEMPORARY TABLE `args`(`c1` INT, `c2` BINARY(255)) ENGINE=MEMORY;")
            __cursor.execute_many(b"INSERT INTO `args` (`c1`, `c2`) VALUES (%s, %s);", __args)
            __cursor.callproc(b"`test_procedure1`", ())
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
        "sql": b"""
CREATE PROCEDURE `test_procedure2` (c1 INT, c2 VARCHAR(255))
BEGIN
    SELECT `a` FROM t; -- > array
END$$
""",
        "exceptions": """
from websql import UserError
""",
        "pyaio": '''
@coroutine
def test_procedure2(connection, c1=None, c2=None):
    """
    test the procedure2
    :param c1: the c1(INT, IN))
    :param c2: the c2(VARCHAR(255), IN))
    :return [("a",)]
    """

    @coroutine
    def __query(__connection):
        __cursor = __connection.cursor()
        try:
            yield from __cursor.callproc(b"`test_procedure2`", (c1, c2))
            return (yield from __cursor.fetchxall())
        finally:
            yield from __cursor.close()
''',

        "pynative": '''
def test_procedure2(connection, c1=None, c2=None):
    """
    test the procedure2
    :param c1: the c1(INT, IN))
    :param c2: the c2(VARCHAR(255), IN))
    :return [("a",)]
    """

    def __query(__connection):
        with __connection.cursor() as __cursor:
            __cursor.callproc(b"`test_procedure2`", (c1, c2))
            return __cursor.fetchxall()
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
        "pyaio": '''
@coroutine
def procedure3(connection):
    """
    procedure3
    """

    @transaction
    @coroutine
    def __query(__connection):
        __cursor = __connection.cursor()
        try:
            yield from __cursor.callproc(b"`procedure3`", ())
        finally:
            yield from __cursor.close()
''',

        "pynative": '''
def procedure3(connection):
    """
    procedure3
    """

    @transaction
    def __query(__connection):
        with __connection.cursor() as __cursor:
            __cursor.callproc(b"`procedure3`", ())
'''
    },
    {
        "sql": b"""
CREATE PROCEDURE `table1.update` (i BIGINT)
BEGIN
    SELECT 1 AS `a`; -- > object
    SELECT b, c FROM t; -- > array
END$$
""",
        "filename": "table1.py",
        "exceptions": """
from websql import UserError
""",
        "pyaio": '''
@coroutine
def update(connection, i=None):
    """
    update the table1
    :param i: the i(BIGINT, IN))
    :return (("a",), [("b", "c")])
    """

    @coroutine
    def __query(__connection):
        __cursor = __connection.cursor()
        try:
            yield from __cursor.callproc(b"`table1.update`", (i,))
            return (
                (yield from __cursor.fetchxall())[0],
                (yield from __cursor.fetchxall()),
            )
        finally:
            yield from __cursor.close()
''',

        "pynative": '''
def update(connection, i=None):
    """
    update the table1
    :param i: the i(BIGINT, IN))
    :return (("a",), [("b", "c")])
    """

    def __query(__connection):
        with __connection.cursor() as __cursor:
            __cursor.callproc(b"`table1.update`", (i,))
            return (
                __cursor.fetchxall()[0],
                __cursor.fetchxall(),
            )
'''
    },
    {
        "sql": b"""
CREATE PROCEDURE `table1.query` (i BIGINT) COMMENT "returns union"
BEGIN
    SELECT 1 AS `a`; -- > object
    SELECT b, c FROM t; -- > items:array
END$$
""",
        "filename": "table1.py",
        "exceptions": """
from websql import UserError
""",
        "pyaio": '''
@coroutine
def query(connection, i=None):
    """
    query the table1
    :param i: the i(BIGINT, IN))
    :return ("a", "items.b", "items.c")
    """

    @coroutine
    def __query(__connection):
        __cursor = __connection.cursor()
        try:
            yield from __cursor.callproc(b"`table1.query`", (i,))
            __result = (yield from __cursor.fetchxall())[0]
            __result.update({"items": (yield from __cursor.fetchxall())})
            return __result
        finally:
            yield from __cursor.close()
''',

        "pynative": '''
def query(connection, i=None):
    """
    query the table1
    :param i: the i(BIGINT, IN))
    :return ("a", "items.b", "items.c")
    """

    def __query(__connection):
        with __connection.cursor() as __cursor:
            __cursor.callproc(b"`table1.query`", (i,))
            __result = __cursor.fetchxall()[0]
            __result.update({"items": __cursor.fetchxall()})
            return __result

'''
    }
]
