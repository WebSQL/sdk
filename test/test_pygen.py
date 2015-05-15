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
from io import BytesIO, StringIO
from warnings import catch_warnings
from sqltoolchain import pygen

try:
    from test.pygen_data import TEST_DATA
except ImportError:  # pragma: no cover
    from .pygen_data import TEST_DATA


class Dummy:
    pass


class TestGenerator(TestCase):
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

        self.assertRaisesRegex(ValueError, "cannot union of returns with different types", pygen.Builder.validate, proc)

    def test_parse_cmdline(self):
        """ test parse commandline arguments """
        args = pygen.parse_arguments(["-i", "test.sql", "-o", "build", "-s", "pyaio"])
        self.assertEqual("test.sql", args.input)
        self.assertEqual("build", args.outdir)
        self.assertEqual("pyaio", args.syntax)

    def test_syntax(self):
        """ test generate result with different templates """
        for data in TEST_DATA:
            for syntax in ("pyaio", "pynative"):
                args = Dummy()
                args.input = BytesIO(data["sql"])
                args.syntax = syntax
                args.outdir = ""

                opened_files = dict()

                def _open_mock(filename):
                    r = opened_files[filename] = StringIO()
                    r.close = lambda: None
                    return r

                with mock.patch('builtins.open', lambda f, *a, **kw: _open_mock(f)):
                    pygen.process(args)

                filename = data.get("filename", "__init__.py")

                self.assertEqual({filename, "exceptions.py"}, set(opened_files.keys()))

                code = opened_files[filename]
                code.seek(0)
                self.assertIn(data[syntax], code.read())
                exceptions = opened_files["exceptions.py"]
                exceptions.seek(0)
                self.assertIn(data["exceptions"], exceptions.read())

    def test_duplicate_fields(self):
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
            pygen.Procedure(proc, True, [])
            self.assertIn("test has duplicated fields: a, c", str(log[0]))
