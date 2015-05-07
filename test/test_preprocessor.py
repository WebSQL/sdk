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

from unittest import TestCase, mock
from io import StringIO
from warnings import catch_warnings
from sqltoolchain import preprocessor


_TEST_FILES = {
    "./main.sql": """
#include "common/func.sql"

select $var1 from $var2 where ${var3};
$f1("test1", `test2`);
$f2(*, as23!@#%4);
""",
    "./common/func.sql": """
#include "vars.sql"
#define f1(a,b) select $a from $b
#define f2(d, e) select $e from $d;\
 select $d from $e
""",
    "./common/vars.sql": """
#define var1 "var1"
#define var2 'var2'
#define var3 `var3`
#define var4 1
""",
    "./recursive.sql": """
#include "recursive.sql"

"""
}

_EXPECTED = """







select "var1" from 'var2' where `var3`;
select "test1" from `test2`;
select as23!@#%4 from *; select * from as23!@#%4;
"""


def _open_mock(filename):
    return StringIO(_TEST_FILES[filename])


def _listdir_mock(dirname):
    return [x.rpartition('/')[-1] for x in _TEST_FILES if x.startswith(dirname)]


class TestCompiler(TestCase):
    def setUp(self):
        self.output = StringIO()
        self.compiler = preprocessor.Preprocessor(self.output)

    def test_define_variable(self):
        self.compiler.parse(StringIO('#DEFINE a "1" '))
        self.assertEqual('"1"', self.compiler.variables["a"])
        self.compiler.parse(StringIO('#DEFINE b `12%&89qa@`'))
        self.assertEqual('`12%&89qa@`', self.compiler.variables["b"])
        self.compiler.parse(StringIO('#DEFINE c "1" '))
        self.assertEqual('"1"', self.compiler.variables["c"])
        self.compiler.parse(StringIO("#DEFINE d '*'"))
        self.assertEqual("'*'", self.compiler.variables["d"])

    def test_expand_variable(self):
        self.compiler.variables["var1"] = "`12%&89qa@`"
        self.compiler.parse(StringIO('select $var1; select ${var1};'))
        self.output.seek(0)
        self.assertEqual("select `12%&89qa@`; select `12%&89qa@`;\n", self.output.read())

    def test_define_macros(self):
        self.compiler.parse(StringIO('#DEFINE f1(a) select * \\ \nfrom $a'))
        macros = self.compiler.functions['f1']
        self.assertEqual(['a'], list(macros.args))
        self.assertEqual('select * from $a', macros.body)
        self.assertEqual(14, macros.ast[0][1])
        self.assertEqual(16, macros.ast[0][2])

    def test_expand_macros(self):
        self.compiler.parse(StringIO('#DEFINE f1(a) select * \\ \nfrom $a\n$f1(`table1`);'))
        self.output.seek(0)
        self.assertEqual("\nselect * from `table1`;\n", self.output.read())
        self.compiler.reset()
        self.assertRaises(ValueError, self.compiler.parse, StringIO('#DEFINE f2(a,b) select * \\ \nfrom $a\n$f2(`table1`);'))

    def test_include(self):
        with mock.patch('builtins.open', lambda f, *args, **kwargs: _open_mock(f)):
            with mock.patch('os.listdir', _listdir_mock):
                self.compiler.compile('main.sql')
                self.output.seek(0)
                self.assertEqual(_EXPECTED, self.output.read())

    def test_if(self):
        """ test conditions """
        self.compiler.parse(StringIO("#define var4 1\n"
                                     "#if var4 == 0\n"
                                     "select $var4 from t1;\n"
                                     "#define var5 2\n"
                                     "#include \"./var1.sql\"\n"
                                     "#else\n"
                                     "select $var4 from t2;\n"
                                     "#endif"))

        self.output.seek(0)
        self.assertEqual("\nselect 1 from t2;\n", self.output.read())

        self.compiler.reset()
        self.assertRaisesRegex(ValueError, "mismatch if/endif",
                               self.compiler.parse, StringIO("#if 1\n select * from t;"))

        self.compiler.reset()
        self.assertRaisesRegex(ValueError, "mismatch if/endif",
                               self.compiler.parse, StringIO("select * from t;\n#endif\n"))

    def test_redefine_macros(self):
        """ test warning generated if macros was redefined """
        with catch_warnings(record=True) as log:
            self.compiler.parse(StringIO("#define var4 1\n"
                                         "#define var4 2\n"))
            self.assertEqual(1, len(log))
            self.assertIn("1: macros var4 already defined!", str(log[0]))

        self.compiler.reset()
        with catch_warnings(record=True) as log:
            self.compiler.parse(StringIO("#define f(a) 1\n"
                                         "#define f(a) 2\n"))
            self.assertEqual(1, len(log))
            self.assertIn("1: macros f already defined!", str(log[0]))

    def test_recursion(self):
        """ test recursive includes"""
        with mock.patch('builtins.open', lambda f, *args, **kwargs: _open_mock(f)):
            with mock.patch('os.listdir', _listdir_mock):
                self.assertRaisesRegex(RuntimeError, "Recursion detected: ./recursive.sql",
                                       self.compiler.compile, "recursive.sql")

    def test_no_inclusion_warning(self):
        """ test warning if there is no include files found"""
        with catch_warnings(record=True) as log:
            with mock.patch('builtins.open', lambda f, *args, **kwargs: _open_mock(f)):
                self.compiler.compile("recursive.sql")

            self.assertEqual(1, len(log))
            self.assertIn("There is no include files: ./recursive.sql", str(log[0]))

    def test_arguments_parse(self):
        """ test cmdline arguments parsing """
        args = preprocessor.parse_arguments(["-i", "test.sql", "-o", "test_o.sql"])
        self.assertEqual("test.sql", args.input)
        self.assertEqual("test_o.sql", args.output)
