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
        proc.returns = Dummy()
        proc.returns.types = ("array", "object")
        proc.returns.merge = True
        proc.queries = []

        with catch_warnings(record=True) as log:
            self.assertRaisesRegex(ValueError, "cannot merge of returns with different types", pygen.Builder.validate, proc)
            self.assertEqual(1, len(log))
            self.assertIn("returns does not match queries", str(log[0]))

        with catch_warnings(record=True) as log:
            proc.returns = []
            proc.queries = ["SELECT"]
            pygen.Builder.validate(proc)
            self.assertIn("returns does not match queries", str(log[0]))

    def test_parse_cmdline(self):
        """ test parse commandline arguments """
        args = pygen.parse_arguments(["-i", "test.sql", "-o", "build", "-s", "aio"])
        self.assertEqual("test.sql", args.input)
        self.assertEqual("build", args.outdir)
        self.assertEqual("aio", args.syntax)

    def test_syntax(self):
        """ test generate result with different templates """
        for data in TEST_DATA:
            for syntax in ("aio", "pure"):
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
