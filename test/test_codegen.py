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
from io import BytesIO, StringIO
from warnings import catch_warnings
from wsql_sdk import codegen

try:
    from test.codegen_data import TEST_DATA
except ImportError:  # pragma: no cover
    from .codegen_data import TEST_DATA


class Dummy:
    pass


class TestCodeGen(TestCase):
    def test_validate(self):
        """ test validate the procedures """
        proc = Dummy()
        proc.name = "test"
        r1 = Dummy()
        r1.name = ""
        r1.type = "array"
        r2 = Dummy()
        r2.name = ""
        r2.type = "object"
        proc.returns = (r1, r2)
        proc.return_mod = "union"
        proc.queries = []

        self.assertRaisesRegex(ValueError, "cannot union of returns with different types", codegen.Builder.validate, proc)

    def test_parse_cmdline(self):
        """ test parse commandline arguments """
        args = codegen.parse_arguments(["-o", "build", "-l", "python3_aio", '--sep', '::', "test.sql"])
        self.assertEqual("test.sql", args.input)
        self.assertEqual("build", args.outdir)
        self.assertEqual("python3_aio", args.language)
        self.assertEqual("::", args.sep)

    def test_syntax(self):
        """ test generate result with different templates """
        for data in TEST_DATA:
            for lang in ("python3_aio", "python3"):
                args = Dummy()
                args.input = StringIO(data["sql"])
                args.language = lang
                args.outdir = ""
                args.sep = '.'

                opened_files = dict()

                def _open_mock(fname):
                    r = opened_files[fname] = StringIO()
                    r.close = lambda: None
                    return r

                with mock.patch('builtins.open', lambda f, *a, **kw: _open_mock(f)):
                    codegen.process(args)

                filename = data.get("filename", "__init__.py")

                self.assertIn(filename, opened_files)

                code = opened_files[filename]
                code.seek(0)
                actual = code.read()
                self.assertIn(data[lang], actual)
                for n in ("constants", "exceptions"):
                    fn = n + ".py"
                    if n in data:
                        self.assertIn(fn, opened_files)
                        file = opened_files[fn]
                        file.seek(0)
                        self.assertIn(data[n], file.read())
                    else:
                        self.assertNotIn(fn, opened_files)

    def test_duplicate_fields(self):
        """test the duplicated field fire warning"""
        r1 = Dummy()
        r1.name = ""
        r1.type = "object"
        r1.fields = ("a", "b", "c")
        r2 = Dummy()
        r2.name = ""
        r2.type = "object"
        r2.fields = ("a", "c")
        proc = Dummy()
        proc.name = "test"
        proc.arguments = []
        proc.temptable = None
        proc.return_mod = "union"
        proc.returns = (r1, r2)

        with catch_warnings(record=True) as log:
            codegen.Procedure(proc.name, "", proc, True, [], proc.returns)
            self.assertGreater(len(log), 0)
            self.assertIn("test has duplicated fields: a, c", str(log[0]))

        r2.name = "c"
        r2.type = "object"
        r2.fields = ("q", "e")

        with catch_warnings(record=True) as log:
            codegen.Procedure(proc.name, "", proc, True, [], proc.returns)
            self.assertGreater(len(log), 0)
            self.assertIn("test has duplicated fields: c", str(log[0]))

        r2.name = "c"
        r2.type = "array"
        r2.fields = ("q", "e")

        with catch_warnings(record=True) as log:
            codegen.Procedure(proc.name, "", proc, True, [], proc.returns)
            self.assertGreater(len(log), 0)
            self.assertIn("test has duplicated fields: c", str(log[0]))
