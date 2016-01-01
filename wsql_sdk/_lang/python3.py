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

from wsql_sdk._lang._python import *

includes_for_api = """
from wsql import Error, handle_error
from wsql.cluster import transaction"""

file_ext = ".py"
indent = "    "
doc_indent = indent
break_lines = 2


return_array = """__cursor.fetchxall()"""
return_object = return_array + "[0]"


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
            __cursor.execute(b"DROP TEMPORARY TABLE IF EXISTS `{0}`;")
            __cursor.execute(b"CREATE TEMPORARY TABLE `{0}`({2}) ENGINE=MEMORY;")
            __cursor.executemany(b"INSERT INTO `{0}` ({3}) VALUES ({4});", __args)"""\
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

    return "def {0}(connection{1}):".format(name, args)


def procedure_close():
    """close procedure body"""

    return """
    try:
        return connection.execute(__query)
    except Error as e:
        raise handle_error(exceptions, e)"""


def body_open():
    """open the main logic"""
    return "    def __query(__connection):"


def body_close():
    """close the main logic"""
    pass


def cursor_open():
    """open cursor"""
    return "        with __connection.cursor() as __cursor:"


def cursor_close():
    """close cursor"""
    pass


def procedure_call(name, args):
    """call procedure"""

    args_str = ', '.join(x.name for x in args)
    if len(args) == 1:
        args_str += ","

    return '            __cursor.callproc(b"{0}", ({1}))'.format(name, args_str)
