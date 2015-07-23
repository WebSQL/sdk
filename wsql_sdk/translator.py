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

import fnmatch
import os
import warnings
from .grammar import MacrosTokenizer


class Translator(MacrosTokenizer):
    def __init__(self, output, close_output=False):
        super().__init__()
        self.output = output
        self.close_output = close_output
        self.includes = set()
        self.workdir = os.curdir

    def write(self, raw):
        line = raw.strip('\n')
        if line:
            self.output.write(line)
            if raw.endswith('\n'):
                self.output.write('\n')

    def on_function(self, ast, body, args):
        start = 0
        for t in ast:
            self.write(body[start:t[1]])
            self.write(args[t[0].getName()])
            start = t[2]

        self.write(body[start:])

    def on_constant(self, name, value):
        self.write('-- CONSTANT {0} {1}\n'.format(name, value))

    def on_variable(self, name, value):
        self.write(value)

    def on_include(self, filename):
        filename = os.path.join(self.workdir, filename)
        dirname = os.path.dirname(filename)
        before = len(self.includes)
        for fname in fnmatch.filter(os.listdir(dirname), os.path.basename(filename)):
            self.include_file(os.path.join(dirname, fname))
        if before == len(self.includes):
            warnings.warn("Not included: %s" % filename)

    def nop(self, text):
        self.write(text)

    def include_file(self, filename):
        if filename in self.includes:
            warnings.warn("Already included: %s" % filename)
        else:
            self.includes.add(filename)
            with open(filename, 'r') as stream:
                workdir = self.workdir
                self.workdir = os.path.dirname(filename)
                self.parse(stream)
                self.workdir = workdir

    def compile(self, filename):
        self.include_file(os.path.join(self.workdir, filename))
        self.output.flush()
        self.close_output and self.output.close()
        if len(self.conditions_stack):
            raise ValueError("mismatch if/endif")


def parse_arguments(argv=None):
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('input', nargs=1, help='input file')
    parser.add_argument('output', nargs='?', help='output file')
    parser.add_argument('-d', '--define', dest='defines', action='append', help='custom defines', default=list())
    return parser.parse_args(argv)


def main(argv=None):  # pragma: no cover
    args = parse_arguments(argv)
    if args.output:
        builder = Translator(open(args.output, 'w'), True)
    else:
        import sys
        builder = Translator(sys.stdout)

    for d, v in map(lambda x: x.split(':', 1), args.defines):
        builder.variables[d] = v

    builder.compile(args.input[0])

if __name__ == "__main__":
    main()
