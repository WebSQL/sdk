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

file_header = """\
# Auto-generated file by wsql-codegen(part of WSQL-SDK)
# {timestamp}"""

includes_for_exceptions = """
from wsql import UserError"""

include_for_union = "from wsql.converters import ObjectDict"

include_local_exceptions = "\nfrom . import exceptions"""


def doc_open():
    """start doc-string"""
    return '    """'


def doc_close():
    """start doc-string"""
    return '    """'


def doc_arg(name, brief):
    """argument of doc_string"""
    return "    :param {0}: {1}".format(name, brief)


def doc_brief(brief):
    """format brief for doc-string"""
    return "    {0}\n".format(brief)


def doc_errors(errors):
    """format errors for doc-string"""
    return "    :raises: {0}".format(', '.join(errors))


def doc_return(returns):
    """format return for doc-string"""
    return "    :returns: {0}".format(repr(returns).replace("\'", '"'))


def format_result(name, result):
    if name:
        return 'ObjectDict({0}={1})'.format(name, result)
    return result


def return_empty():
    """return empty value"""
    pass


def return_one(result):
    """return one statement"""
    return "            return " + result


def return_tuple_open():
    """tuple of statements, open statement"""
    return "            return ("


def return_tuple_item(item):
    """tuple of statements, next statement"""
    return "                {0},".format(item)


def return_tuple_close():
    """tuple of statements, close statement"""
    return "            )"


def return_union_open(first):
    """union of statements, open statement"""
    return "            __result = " + first


def return_union_item(item):
    """union of statements, next statement"""
    return "            __result.update({0})".format(item)


def return_union_close():
    """union of statements, close statement"""
    return "            return __result"


def exception_class(name):
    """declare exception class"""
    return "class {0}(UserError):\n    pass".format(name)


def declare_constant(name, value):
    """declare constant"""
    try:
        if value and value[0] not in ('"', "'"):
            int(value)
    except ValueError:
        value = repr(value)

    return "\n{0} = {1}".format(name.upper(), value)


def include_for_structures(kinds):
    """get the includes for structures depends on kind"""
    if 'ENUM' in kinds:
        return '\nfrom enum import Enum'
    return ''


def declare_structure(kind, name, fields):
    """declare the structure"""
    name = name.title().replace("_", "")
    if kind == 'ENUM':
        return "class {0}(Enum):\n    {1}".format(
            name,
            "\n    ".join('{0} = {1!r}'.format(x.lower(), x) for x in fields)
        )

    return """\
class {0}(set):
    __choice = frozenset(({1}))

    def __init__(self, v):
        nv = set(v) & self.__choice
        if len(nv) != len(v):
            raise ValueError("unexpected value %s" % nv)
        self.__value = nv

    @property
    def value(self):
        return self.__value""".format(name, ", ".join(map(repr, fields)))
