#!/bin/python3
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

import fnmatch
import os
import warnings
from ._interpreter import MacrosTokenizer


class Preprocessor(MacrosTokenizer):
    def __init__(self, output, close_output=False):
        super().__init__()
        self.output = output
        self.close_output = close_output
        self.includes = set()
        self.workdir = os.curdir

    def on_function(self, ast, body, args):
        start = 0
        for t in ast:
            self.output.write(body[start:t[1]])
            self.output.write(args[t[0].getName()])
            start = t[2]

        self.output.write(body[start:])

    def on_variable(self, name, value):
        self.output.write(value)

    def on_include(self, filename):
        filename = os.path.join(self.workdir, filename)
        dirname = os.path.dirname(filename)
        before = len(self.includes)
        for fname in fnmatch.filter(os.listdir(dirname), os.path.basename(filename)):
            self.include_file(os.path.join(dirname, fname))
        if before == len(self.includes):
            warnings.warn("There is no include files: %s" % filename)

    def nop(self, text):
        self.output.write(text)

    def include_file(self, filename):
        if filename in self.includes:
            raise RuntimeError('Recursion detected: %s' % filename)
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


def parse_arguments(argv=None):
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-i', '--input', help='input file', required=True)
    parser.add_argument('-o', '--output', help='output file, by default write stdout')
    return parser.parse_args(argv)


def main(argv=None):  # pragma: no cover
    args = parse_arguments(argv)
    if args.output:
        builder = Preprocessor(open(args.output, 'w'), True)
    else:
        import sys
        builder = Preprocessor(sys.stdout)

    builder.compile(args.input)

if __name__ == "__main__":
    main()
