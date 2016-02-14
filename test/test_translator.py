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

from unittest import TestCase, mock
from io import StringIO
from warnings import catch_warnings
from wsql_sdk import translator


_TEST_FILES = {
    "./main.sql": """
#include "common/func.sql"

select $_var1 from $_var2 where $_var3;
$f1(MAX(*), `test2`);
$f2(*, as23!@#%4);
$f3("a", "b c");
""",
    "./common/func.sql": """
#include "vars.sql"
#define f1(a,b) select $a from $b
#define f2(d, e) select $e from $d;\
 select $d from $e
#define f3(a, b) CALL p($a, $b)
""",
    "./common/vars.sql": """
#define _var1 "var1"
#define _var2 'var2'
#define _var3 `var3`
#define _var4 1
""",
    "./recursive.sql": """
#include "recursive.sql"

""",
    "./invalid_if.sql": """
#if defined("TEST")
#include "/common/vars.sql"
"""
}

_EXPECTED = """\
select "var1" from 'var2' where `var3`;
select MAX(*) from `test2`;
select as23!@#%4 from *; select * from as23!@#%4;
CALL p("a", "b c");\
"""


def _open_mock(filename):
    return StringIO(_TEST_FILES[filename])


def _listdir_mock(dirname):
    return [x.rpartition('/')[-1] for x in _TEST_FILES if x.startswith(dirname)]


class TestTranslator(TestCase):
    def setUp(self):
        self.output = StringIO()
        self.trans = translator.Translator(self.output)

    def test_define_variable(self):
        self.trans.parse(StringIO('#DEFINE a "1" '))
        self.assertEqual('"1"', self.trans.variables["a"])
        self.trans.parse(StringIO('#DEFINE b `12%&89qa@`'))
        self.assertEqual('`12%&89qa@`', self.trans.variables["b"])
        self.trans.parse(StringIO('#DEFINE c "1" '))
        self.assertEqual('"1"', self.trans.variables["c"])
        self.trans.parse(StringIO("#DEFINE d '*'"))
        self.assertEqual("'*'", self.trans.variables["d"])

    def test_expand_variable(self):
        self.trans.variables["var1"] = "`12%&89qa@`"
        self.trans.parse(StringIO('select $var1; select $var1;'))
        self.output.seek(0)
        self.assertEqual("select `12%&89qa@`; select `12%&89qa@`;\n", self.output.read())

    def test_define_macros(self):
        self.trans.parse(StringIO('#DEFINE f1(a) select * \\ \nfrom $a'))
        macros = self.trans.functions['f1']
        self.assertEqual(['a'], list(macros.args))
        self.assertEqual('select * from $a', macros.body)
        self.assertEqual(14, macros.ast[0][1])
        self.assertEqual(16, macros.ast[0][2])

    def test_undefine_function(self):
        self.trans.parse(StringIO('#define f1(a) select * from $a\n$f1(b);\n#undef f1'))
        self.output.seek(0)
        self.assertEqual("select * from b;\n", self.output.read())
        self.assertNotIn('f1', self.trans.functions)

    def test_undefine_variable(self):
        self.trans.parse(StringIO('#define _v 1\nselect $_v from a;\n#undef _v'))
        self.output.seek(0)
        self.assertEqual("select 1 from a;\n", self.output.read())
        self.assertNotIn('_v', self.trans.variables)
        self.trans.reset()
        with catch_warnings(record=True) as log:
            self.trans.parse(StringIO("#undef v\n"))
            self.assertEqual(1, len(log))
            self.assertIn("0: macros v is not defined!", str(log[0]))

    def test_expand_macros(self):
        self.trans.parse(StringIO('#DEFINE f1(a) select * \\ \nfrom $a\n$f1(`table1`);'))
        self.output.seek(0)
        self.assertEqual("select * from `table1`;\n", self.output.read())
        self.trans.reset()
        self.assertRaises(ValueError, self.trans.parse, StringIO('#DEFINE f2(a,b) select * \\ \nfrom $a\n$f2(`table1`);'))

    def test_expand_function(self):
        self.trans.parse(StringIO('#DEFINE v 1\n#DEFINE f(a) select $a\n$f($v);'))
        self.output.seek(0)
        self.assertEqual("-- CONSTANT v 1\nselect 1;\n", self.output.read())

    def test_include(self):
        with mock.patch('builtins.open', lambda f, *args, **kwargs: _open_mock(f)):
            with mock.patch('os.listdir', _listdir_mock):
                self.trans.compile('main.sql')
                self.output.seek(0)
                self.assertEqual(_EXPECTED, self.output.read().strip())

    def test_if(self):
        """ test conditions """
        self.trans.parse(StringIO("#define var4 1\n"
                                  "#if var4 == 0\n"
                                  "select $var4 from t1;\n"
                                  "#define var5 2\n"
                                  "#include \"./var1.sql\"\n"
                                  "#else\n"
                                  "select $var4 from t2;\n"
                                  "#endif"))

        self.output.seek(0)
        self.assertEqual("-- CONSTANT var4 1\nselect 1 from t2;\n", self.output.read())

        self.trans.reset()
        self.output.seek(0)
        self.output.truncate(0)
        self.trans.parse(StringIO("#if defined('VAR')\n"
                                  "select TRUE\n"
                                  "#else\n"
                                  "select FALSE\n"
                                  "#endif\n"))
        self.output.seek(0)
        self.assertEqual("select FALSE\n", self.output.read())

        with mock.patch('builtins.open', lambda f, *args, **kwargs: _open_mock(f)):
            with mock.patch('os.listdir', _listdir_mock):
                self.trans.reset()
                self.assertRaisesRegex(ValueError, "mismatch if/endif",
                                       self.trans.compile, "invalid_if.sql")

    def test_redefine_macros(self):
        """ test warning generated if macros was redefined """
        with catch_warnings(record=True) as log:
            self.trans.parse(StringIO("#define var4 1\n#define var4 2\n"))
            self.assertEqual(1, len(log))
            self.assertIn("1: macros var4 already defined!", str(log[0]))

        self.trans.reset()
        with catch_warnings(record=True) as log:
            self.trans.parse(StringIO("#define f(a) 1\n#define f(a) 2\n"))
            self.assertEqual(1, len(log))
            self.assertIn("1: macros f already defined!", str(log[0]))

    def test_recursion(self):
        """ test recursive includes"""
        with mock.patch('builtins.open', lambda f, *args, **kwargs: _open_mock(f)):
            with mock.patch('os.listdir', _listdir_mock):
                with catch_warnings(record=True) as log:
                    self.trans.compile("recursive.sql")
                    self.assertEqual(2, len(log))
                    self.assertIn("Already included: ./recursive.sql", str(log[0]))

    def test_no_inclusion_warning(self):
        """ test warning if there is no include files found"""
        with catch_warnings(record=True) as log:
            with mock.patch('builtins.open', lambda f, *args, **kwargs: _open_mock(f)):
                self.trans.compile("recursive.sql")

            self.assertEqual(1, len(log))
            self.assertIn("Not included: ./recursive.sql", str(log[0]))

    def test_arguments_parse(self):
        """ test cmdline arguments parsing """
        args = translator.parse_arguments(["test.sql", "test_o.sql", "-d", "k:v", "-d", "k1:v1 v2"])
        self.assertEqual("test.sql", args.input[0])
        self.assertEqual("test_o.sql", args.output)
        self.assertEqual(["k:v", "k1:v1 v2"], args.defines)
        args = translator.parse_arguments(["test.sql"])
        self.assertEqual("test.sql", args.input[0])
        self.assertIsNone(args.output)

    def test_global_defines(self):
        """test external defines"""
        self.trans.variables["DB_NAME"] = "test"
        self.trans.parse(StringIO("use `$DB_NAME`;"))
        self.output.seek(0)
        self.assertEqual("use `test`;\n", self.output.read())

    def test_recursive_expand_macros(self):
        """test recursive expand macros"""
        self.trans.parse(StringIO(
            """\
#define _G a
#define _K $_G
#define f1(t, g) $t WHERE $g
#define f2(v, t) SELECT $v FROM $f1($t, $_K)
$f2(1, t);"""
        ))
        self.output.seek(0)
        self.assertEqual("SELECT 1 FROM t WHERE a;", self.output.read().strip())

    def test_define_empty_macros(self):
        self.trans.parse(StringIO('#DEFINE f1(a)\n$f1(1)\n'))
        macros = self.trans.functions['f1']
        self.assertEqual(['a'], list(macros.args))
        self.assertEqual(0, len(macros.body))
        self.output.seek(0)
        self.assertEqual('', self.output.read())
