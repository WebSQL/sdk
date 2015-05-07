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

import os
import sys
import warnings

from datetime import datetime
from functools import reduce
from importlib import machinery
from textwrap import TextWrapper
from ._interpreter import SQLTokenizer

_THIS_DIR = os.path.dirname(__file__)


class Argument:
    def __init__(self, argument):
        self.__argument = argument
        self.brief = 'the ' + ' of '.join(reversed(argument.name.split('_'))) + '({0.type}, {0.direction})'.format(argument)

    def __getattr__(self, item):
        return getattr(self.__argument, item)


class TempTable:
    def __init__(self, temptable):
        self.name = temptable.name
        self.brief = 'list of {' + ','.join('{0.name}({0.type})'.format(x) for x in temptable.columns) + '}'
        self.columns = temptable.columns


class Procedure:
    def __init__(self, proc, read_only, queries, errors):
        self.__proc = proc
        self.read_only = read_only
        self.errors = errors
        self.queries = queries
        self.module, _, self.name = proc.name.partition('.')
        if not self.name:
            self.name = self.module
            self.module = ""

        self.arguments = [Argument(x) for x in proc.arguments]
        if proc.temptable:
            self.temptable = TempTable(proc.temptable)

        action, *subject = self.name.split('_')
        if subject:
            self.brief = '%s the %s%s' % (action, ' of '.join(subject), " of the " + self.module if self.module else "")
        else:
            self.brief = '%s%s' % (action, " the " + self.module if self.module else "")

        if self.__proc.returns and self.__proc.returns.types:
            result = []
            for t, q in zip(self.__proc.returns.types, self.__proc.queries):
                if t == "array":
                    result.append([sorted(q.columns)])
                elif t == 'object':
                    result.append(set(q.columns))
            if self.__proc.returns.merge:
                result = reduce(lambda x, y: x | y, result, set())

            if len(result) == 1:
                result = result[0]

            if isinstance(result, list):
                self.result_columns = tuple(tuple(sorted(x)) for x in result)
            else:
                self.result_columns = tuple(sorted(result))
        else:
            self.result_columns = None

    @property
    def fullname(self):
        return self.__proc.name

    def __getattr__(self, item):
        return getattr(self.__proc, item)


class Builder:
    def __init__(self, syntax):
        self.syntax = syntax
        self.stream = None

    def write(self, text, eol="\n"):
        if text is not None:
            self.stream.write(text)
            self.stream.write(eol)

    def write_doc_string(self, procedure):
        """write doc string"""
        self.write(self.syntax.doc_open())
        self.write(self.syntax.doc_brief(procedure.brief))

        for arg in procedure.arguments:
            self.write(self.syntax.doc_arg(arg.name, arg.brief))
        if procedure.temptable:
            self.write(self.syntax.doc_arg(procedure.temptable.name, procedure.temptable.brief))
        if procedure.result_columns:
            for i in TextWrapper(initial_indent="",
                                 subsequent_indent=self.syntax.doc_indent,
                                 width=100).wrap(self.syntax.doc_return(procedure.result_columns)):
                self.write(i)

        if procedure.errors:
            self.write(self.syntax.doc_errors(procedure.errors))
        self.write(self.syntax.doc_close(), eol='\n\n')

    def write_returns(self, returns):
        """return formatted return value"""
        converters = {"object": self.syntax.return_object, "array": self.syntax.return_array}

        if not returns or not returns.types:
            return self.write(self.syntax.return_empty())

        if len(returns.types) == 1:
            return self.write(self.syntax.return_single(converters[returns.types[0]]))

        if returns.merge:
            self.write(self.syntax.return_merge_open(converters[returns.types[0]]))

            for i in range(1, len(returns.types)):
                self.write(self.syntax.return_merge_item(converters[returns.types[i]]))
            self.write(self.syntax.return_merge_close())
        else:
            self.write(self.syntax.return_multi_open())

            for i in range(0, len(returns.types)):
                self.write(self.syntax.return_multi_item(converters[returns.types[i]]))

            self.write(self.syntax.return_multi_close())

    def __enter__(self):
        pass

    def __exit__(self, *_):
        if self.stream:
            self.stream.flush()
            self.stream.close()
            self.stream.close()

    def create_api_output(self, path, module):
        """open new file to write procedures"""
        self.stream = open(os.path.join(path, module + self.syntax.file_ext), "w")
        self.write(self.syntax.file_header.format(timestamp=datetime.now()))
        self.write(self.syntax.includes_for_api)
        return self

    def create_exceptions_output(self, path):
        """open a new file to write exceptions"""
        self.stream = open(os.path.join(path, "exceptions" + self.syntax.file_ext), "w", encoding="utf8")
        self.write(self.syntax.file_header.format(timestamp=datetime.now()))
        self.write(self.syntax.includes_for_exceptions)
        return self

    @staticmethod
    def validate(procedure):
        """validate procedure description"""
        if procedure.returns:
            if len(procedure.returns.types) != len(procedure.queries):
                    warnings.warn("%s returns does not match queries: %s != %s" % (procedure.name, len(procedure.returns.types), len(procedure.queries)))

            if procedure.returns.merge and any((x != "object") for x in procedure.returns.types):
                    raise ValueError('SyntaxError: %s cannot merge of returns with different types: %s' % (procedure.name, procedure.returns.types))
        elif procedure.queries:
                warnings.warn("%s returns does not match queries: 0 != %s" % (procedure.name, len(procedure.queries)))

    def write_procedure(self, procedure):
        """handle the procedure body"""

        self.write("", eol="\n" * self.syntax.break_lines)
        args_decl = (x.name for x in procedure.arguments + ([procedure.temptable] if procedure.temptable else []))

        self.write(self.syntax.procedure_open(procedure.name, args_decl))

        self.write_doc_string(procedure)
        if not procedure.read_only:
            self.write(self.syntax.transaction_open())

        self.write(self.syntax.body_open())
        self.write(self.syntax.cursor_open())
        if procedure.temptable:
            self.write(self.syntax.temporary_table(procedure.temptable.name, procedure.temptable.columns))

        self.write(self.syntax.procedure_call(procedure.fullname, procedure.arguments))
        self.write_returns(procedure.returns)

        self.write(self.syntax.cursor_close())
        self.write(self.syntax.body_close())

        if not procedure.read_only:
            self.write(self.syntax.transaction_close())

        self.write(self.syntax.procedure_close())

    def write_exception(self, exception):
        """write the exception class"""
        self.write("", eol="\n" * self.syntax.break_lines)
        self.write(self.syntax.exception_class(exception))


def create_builder(name):
    """load builder by name"""
    loader = machinery.SourceFileLoader("syntax." + name, os.path.join(_THIS_DIR, 'syntax', name + ".py"))
    return Builder(loader.load_module())


def load_input(source):
    if isinstance(source, str):  # pragma: no cover
        with open(source, 'r', encoding='utf8') as stream:
            return stream.read()
    else:
        return source.read().decode('utf8')


def parse_arguments(argv=None):
    from argparse import ArgumentParser

    available_syntax = [x.partition('.')[0] for x in os.listdir(os.path.join(_THIS_DIR, 'syntax')) if not x.startswith('_')]

    parser = ArgumentParser()
    parser.add_argument('-i', '--input', help='source file, by default input stream', default=sys.stdin)
    parser.add_argument('-o', '--outdir', help='output dir', default='.')
    parser.add_argument('-s', '--syntax', help='the syntax', choices=available_syntax, required=True)
    return parser.parse_args(argv)


def process(args):
    tokenizer = SQLTokenizer()
    tokenizer.parse(load_input(args.input))

    builder = create_builder(args.syntax)

    modules = {}
    for p in tokenizer.procedures():
        if not p.name.startswith('_'):
            builder.validate(p)
            procedure = Procedure(p, tokenizer.is_read_only(p), tokenizer.queries(p), tokenizer.errors(p))
            modules.setdefault(procedure.module or "__init__", []).append(procedure)

    count = 0
    for module in modules:
        with builder.create_api_output(args.outdir, module):
            for p in sorted(modules[module], key=lambda x: x.name):
                builder.write_procedure(p)
                count += 1

    with builder.create_exceptions_output(args.outdir):
        for e in tokenizer.errors():
            builder.write_exception(e)
    return count


def main(argv=None):  # pragma: no cover
    count = process(parse_arguments(argv))
    print("Total: %s" % count, file=sys.stderr)


if __name__ == '__main__':
    main()
