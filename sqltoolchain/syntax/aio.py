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


file_header = """
# auto-generated file by WebSQL-Toolkit
# {timestamp}
"""


includes_for_api = """
from asyncio import coroutine
from websql import Error, handle_error
from websql.cluster import transaction
from . import exceptions"""

includes_for_exceptions = """\nfrom websql import UserError"""

file_ext = ".py"
indent = "    "
doc_indent = indent
break_lines = 2


return_array = """(yield from __cursor.fetchall())"""
return_object = return_array + "[0]"


def doc_open():
    """start doc-string"""
    return '    """'


def doc_close():
    """start doc-string"""
    return '    """'


def doc_arg(name, brief):
    """argument of doc_string"""
    return "    :param {0}: {1})".format(name, brief)


def doc_brief(brief):
    """format brief for doc-string"""
    return "    " + brief


def doc_errors(errors):
    """format errors for doc-string"""
    return "    :raises: {0}".format(', '.join(errors))


def doc_return(returns):
    """format return for doc-string"""
    return "    :return {!r}".format(returns)


def return_empty():
    """return empty value"""
    pass


def return_single(r):
    """return single statement"""
    return "            return " + r


def return_multi_open():
    """combine result set(start)"""
    return "            return ["


def return_multi_item(item):
    """combine result set(item)"""
    return "                {0},".format(item)


def return_multi_close():
    """combine result set(end)"""
    return "            ]"


def return_merge_open(first):
    """merge result set(start)"""
    return "            __result = " + first


def return_merge_item(item):
    """merge result set(item)"""
    return "            __result.update({0})".format(item)


def return_merge_close():
    """merge result set(end)"""
    return "            return __result"


def temporary_table(name, columns):
    """create a temporary table"""
    columns_def = ', '.join('`{0.name}` {0.type}'.format(x) for x in columns)
    column_names = ', '.join('"{0.name}"'.format(x) for x in columns)
    column_names_sql = ', '.join('`{0.name}`'.format(x) for x in columns)
    place_holders = ', '.join(["%s"] * len(columns))

    return """\
            if {0} is None:
                return
            __args = ((x.get(y, None) for y in ({1})) for x in {0})
            yield from __cursor.execute(b"DROP TEMPORARY TABLE IF EXISTS `{0}`;")
            yield from __cursor.execute(b"CREATE TEMPORARY TABLE `{0}`({2}) ENGINE=MEMORY;")
            yield from __cursor.execute_many(b"INSERT INTO `{0}` ({3}) VALUES ({4});", __args)"""\
        .format(name, column_names, columns_def, column_names_sql, place_holders)


def transaction_open():
    """open transaction scope"""
    return "    @transaction"


def transaction_close():
    """close transaction scope"""
    pass


def procedure_open(name, args):
    """open procedure body"""

    args = ', '.join('{0}=None'.format(x) for x in args)
    if args:
        args = ', ' + args

    return "@coroutine\ndef {0}(connection{1}):".format(name, args)


def procedure_close():
    """close procedure body"""

    return """
    try:
        return (yield from connection.execute(__query))
    except Error as e:
        raise handle_error(exceptions, e)"""


def body_open():
    """open the main logic"""
    return "    @coroutine\n    def __query(__connection):"


def body_close():
    """close the main logic"""
    pass


def cursor_open():
    """open cursor"""
    return "        __cursor = __connection.cursor()\n        try:"


def cursor_close():
    """close cursor"""
    return "        finally:\n            yield from __cursor.close()"


def procedure_call(name, args):
    """call procedure"""

    args_str = ', '.join(x.name for x in args)
    if len(args) == 1:
        args_str += ","

    return '            yield from __cursor.callproc(b"`{0}`", ({1}))'.format(name, args_str)


def exception_class(name):
    """declare exception class"""

    return "class {0}Error(UserError):\n    pass".format(name)
