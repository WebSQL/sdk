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

import os
import sys
import warnings
import itertools

from collections import defaultdict
from datetime import datetime
from functools import reduce
from importlib import machinery
from textwrap import TextWrapper
from .grammar import SQLTokenizer

_THIS_DIR = os.path.dirname(__file__)


class Argument:
    """The procedure argument description"""
    def __init__(self, argument):
        self.__argument = argument
        self.brief = 'the ' + ' of '.join(reversed(argument.name.split('_'))) + '({0.type}, {0.direction})'.format(argument)

    def __getattr__(self, item):
        return getattr(self.__argument, item)


class TempTable:
    """The temporary table description"""
    def __init__(self, temptable):
        self.name = temptable.name
        self.brief = 'list of {' + ','.join('{0.name}({0.type})'.format(x) for x in temptable.columns) + '}'
        self.columns = temptable.columns


class Procedure:
    """The procedure description"""
    def __init__(self, module, name, proc, read_only, errors, returns):
        self.module, self.name = module, name
        self.__proc = proc
        self.read_only = read_only
        self.errors = errors
        self.returns = returns

        self.arguments = [Argument(x) for x in proc.arguments]
        if proc.temptable:
            self.temptable = TempTable(proc.temptable)

        action, *subject = self.name.split('_')
        if subject:
            self.brief = '%s the %s%s' % (action, ' of '.join(subject), " of the " + self.module if self.module else "")
        else:
            self.brief = '%s%s' % (action, " the " + self.module if self.module else "")

        if self.returns:
            result = []
            named = set()
            for ret in self.returns:
                if ret.type == "array":
                    kind = lambda x: [x]
                else:
                    kind = lambda x: x

                if ret.name == "":
                    result.append(kind(tuple(sorted(ret.fields))))
                else:
                    named.add(ret.name)
                    result.append(tuple('.'.join((ret.name, x)) for x in sorted(ret.fields)))

            if self.__proc.return_mod == "union":
                columns_set = reduce(lambda x, y: x | set(y), result, set())
                if len(columns_set) != reduce(lambda x, y: x + len(y), result, 0) or len(columns_set & named) != 0:
                    duplicates = set()
                    seen = named
                    for i in itertools.chain(*result):
                        if i not in seen:
                            seen.add(i)
                        else:
                            duplicates.add(i)

                    warnings.warn("%s has duplicated fields: %s" % (self.__proc.name, ', '.join(sorted(duplicates))))
                self.result_columns = tuple(sorted(columns_set))
            else:
                if len(result) == 1:
                    self.result_columns = result[0]
                else:
                    self.result_columns = tuple(result)
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
        """write text to output stream"""
        if text is not None:
            self.stream.write(text)
            self.stream.write(eol)

    def write_doc_string(self, procedure):
        """write doc string"""
        self.write(self.syntax.doc_open())
        self.write(self.syntax.doc_brief(procedure.brief))
        self.write(self.syntax.doc_arg("connection", "the connection object"))

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

    def write_returns(self, returns, mod):
        """return formatted return value"""
        converters = {"object": self.syntax.return_object, "array": self.syntax.return_array}
        syntax = self.syntax

        def format_return(r):
            return syntax.format_result(r.name, converters[r.type])

        if not returns:
            return self.write(syntax.return_empty())

        if len(returns) == 1:
            return self.write(syntax.return_one(format_return(returns[0])))

        if mod == "union":
            self.write(syntax.return_union_open(format_return(returns[0])))

            for i in range(1, len(returns)):
                self.write(syntax.return_union_item(format_return(returns[i])))
            self.write(syntax.return_union_close())
        else:
            self.write(syntax.return_tuple_open())

            for i in range(0, len(returns)):
                self.write(syntax.return_tuple_item(format_return(returns[i])))

            self.write(syntax.return_tuple_close())

    def __enter__(self):
        pass

    def __exit__(self, *_):
        if self.stream:
            self.stream.flush()
            self.stream.close()
            self.stream.close()

    def create_api_output(self, path, module, structures, has_union):
        """open new file to write procedures"""
        self.stream = open(os.path.join(path, module + self.syntax.file_ext), "w")
        self.write(self.syntax.file_header.format(timestamp=datetime.now()))
        self.write(self.syntax.includes_for_api)
        if has_union:
            self.write(self.syntax.include_for_union)
        self.write(self.syntax.include_local_exceptions)

        if structures is not None:
            self.write(self.syntax.include_for_structures(structures))
            for kind in sorted(structures):
                for v in structures[kind]:
                    self.write("", eol="\n" * self.syntax.break_lines)
                    self.write(self.syntax.declare_structure(kind, *v))
        return self

    def create_exceptions_output(self, path):
        """open a new file to write exceptions"""
        self.stream = open(os.path.join(path, "exceptions" + self.syntax.file_ext), "w", encoding="utf8")
        self.write(self.syntax.file_header.format(timestamp=datetime.now()))
        self.write(self.syntax.includes_for_exceptions)
        return self

    def create_constants_output(self, path):
        self.stream = open(os.path.join(path, "constants" + self.syntax.file_ext), "w", encoding="utf8")
        self.write(self.syntax.file_header.format(timestamp=datetime.now()))
        return self

    @staticmethod
    def validate(procedure):
        """validate procedure description"""
        if procedure.returns:
            if procedure.return_mod == "union" and any((x.type != "object" and x.name == "") for x in procedure.returns):
                raise ValueError('SyntaxError: %s cannot union of returns with different types: %s' % (procedure.name, procedure.returns))

    def write_procedure(self, procedure):
        """handle the procedure body"""

        self.write("", eol="\n" * self.syntax.break_lines)
        args_decl = (x.name for x in procedure.arguments + ([procedure.temptable] if procedure.temptable else []))

        self.write(self.syntax.procedure_open(procedure.name, args_decl))

        self.write_doc_string(procedure)
        self.write(self.syntax.transaction_open())

        self.write(self.syntax.body_open())
        self.write(self.syntax.cursor_open())
        if procedure.temptable:
            self.write(self.syntax.temporary_table(procedure.temptable.name, procedure.temptable.columns))

        self.write(self.syntax.procedure_call(procedure.fullname, procedure.arguments))
        self.write_returns(procedure.returns, procedure.return_mod)

        self.write(self.syntax.cursor_close())
        self.write(self.syntax.body_close())

        self.write(self.syntax.transaction_close())

        self.write(self.syntax.procedure_close())

    def write_exception(self, exception):
        """write the exception class"""
        self.write("", eol="\n" * self.syntax.break_lines)
        self.write(self.syntax.exception_class(exception))

    def write_constant(self, name, value):
        """write the constant"""
        self.write(self.syntax.declare_constant(name, value))

_LANGUAGES_FOLDER = "_lang"


def create_builder(name):
    """load builder by syntax"""
    loader = machinery.SourceFileLoader(".".join((_LANGUAGES_FOLDER, name)), os.path.join(_THIS_DIR, _LANGUAGES_FOLDER, name + ".py"))
    return Builder(loader.load_module())


def get_languages():
    return [x.partition('.')[0] for x in os.listdir(os.path.join(_THIS_DIR, _LANGUAGES_FOLDER)) if not x.startswith('_')]


def load_input(source):
    """load the input"""
    if isinstance(source, str):  # pragma: no cover
        with open(source, 'r', encoding='utf8') as stream:
            return stream.read()
    else:
        data = source.read()
        if isinstance(data, bytes):
            return data.decode("utf8")
        return data


def parse_arguments(argv=None):
    from argparse import ArgumentParser

    available_language = get_languages()

    parser = ArgumentParser()
    parser.add_argument('input', nargs='?', help='source file, by default input stream', default=sys.stdin)
    parser.add_argument('-o', '--outdir', help='output dir', default=os.curdir)
    parser.add_argument('-l', '--language', help='the language', choices=available_language, required=True)
    parser.add_argument('--sep', help='the module separator', default='.', choices=['.', '::'])
    return parser.parse_args(argv)


def process(args):
    """generate code according to specified parameters"""

    tokenizer = SQLTokenizer()
    tokenizer.parse(load_input(args.input))

    builder = create_builder(args.language)

    modules = defaultdict(list)
    module_needs_union = set()
    for p in tokenizer.procedures():
        module, _, name = p.name.partition(args.sep)
        if len(name) == 0:
            name = module
            module = ""

        if name.startswith("_") or module.startswith("_"):
            continue

        builder.validate(p)
        procedure = Procedure(module, name, p, tokenizer.is_read_only(p),
                              sorted(tokenizer.errors(p)), tokenizer.returns(p))

        module_name = procedure.module or "__init__"
        modules[module_name].append(procedure)
        if p.return_mod == "union":
            module_needs_union.add(module_name)

    count = 0
    for module_name in modules:
        with builder.create_api_output(
                args.outdir, module_name, tokenizer.structures(module_name),
                module_name in module_needs_union):
            for p in sorted(modules[module_name], key=lambda x: x.name):
                builder.write_procedure(p)
                count += 1

    exceptions = tokenizer.errors()
    if len(exceptions) > 0:
        with builder.create_exceptions_output(args.outdir):
            for e in sorted(exceptions):
                builder.write_exception(e)

    constants = tokenizer.constants()
    if len(constants) > 0:
        with builder.create_constants_output(args.outdir):
            for n, v in sorted(constants):
                builder.write_constant(n, v)

    return count


def main(argv=None):  # pragma: no cover
    count = process(parse_arguments(argv))
    print("Total: %s" % count, file=sys.stderr)


if __name__ == '__main__':
    main()
