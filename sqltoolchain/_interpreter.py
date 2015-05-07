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

from collections import namedtuple
from functools import reduce
from pyparsing import alphanums, CaselessKeyword, Combine, delimitedList, Group, Keyword, Literal, \
    lineEnd, lineStart, MatchFirst, nestedExpr, nums, oneOf, Or, Optional, Regex, Suppress, Word, \
    quotedString, SkipTo
import warnings


# PREPROCESSOR
_BEGIN_MACROS = lineStart + Suppress(Literal('#'))
_MACRO_IDENTIFIER = Word(alphanums + '_')
_MACRO_VALUE = Word(alphanums + "!#%&*+-./:<=>?@[\]^_~\"'`")
_MACRO_IDENTIFIERS = delimitedList(_MACRO_IDENTIFIER, combine=False)
_MACRO_VALUES = delimitedList(_MACRO_VALUE, combine=False)
_INCLUDE = _BEGIN_MACROS + CaselessKeyword("INCLUDE") + quotedString.setResultsName('filename')
_DEFINE = _BEGIN_MACROS + CaselessKeyword("DEFINE") + _MACRO_IDENTIFIER.setResultsName('name') + \
    (_MACRO_VALUE.setResultsName('value') | nestedExpr(content=_MACRO_IDENTIFIERS).setResultsName('args') + Regex(".+$").setResultsName('body'))

_EXPAND = (Suppress('${') + _MACRO_IDENTIFIER.setResultsName('name') + Suppress('}')) | \
    Or((Suppress('$') + _MACRO_IDENTIFIER.setResultsName('name'),
        (Suppress('$') + _MACRO_IDENTIFIER.setResultsName('name') + nestedExpr(content=_MACRO_VALUES, ignoreExpr=None).setResultsName('args'))))

_IF = _BEGIN_MACROS + Suppress(CaselessKeyword('IF')) + Regex(".+$").setResultsName('condition')
_ELSE = _BEGIN_MACROS + Suppress(CaselessKeyword('ELSE')) + lineEnd
_ENDIF = _BEGIN_MACROS + Suppress(CaselessKeyword("ENDIF")) + lineEnd

# ANALYSER
_SKIP_TO_END = Suppress(SkipTo(Literal(";")))
_SQL_IDENTIFIER = Suppress(Optional(Literal('`'))) + Word(alphanums + '_.') + Suppress(Optional(Literal('`')))
_SQL_IDENTIFIERS = Group(delimitedList(_SQL_IDENTIFIER))
_COLUMN = Group(_SQL_IDENTIFIER + Optional(CaselessKeyword('AS') + _SQL_IDENTIFIER))
_COLUMNS = Group(delimitedList(_COLUMN))
_EXPRESSION = (CaselessKeyword("SELECT") | CaselessKeyword("EXISTS")) + Suppress(SkipTo(CaselessKeyword("AS"))) + _SQL_IDENTIFIER
_DIRECTION = oneOf('INOUT IN OUT', caseless=True)
_TYPE = Combine(Word(alphanums + '_') + Optional('(' + Word(nums) + ')'))
_ARGUMENT = Group(Optional(_DIRECTION, default='IN') + _SQL_IDENTIFIER + _TYPE)
_ARGUMENTS = delimitedList(_ARGUMENT)
_RETURN_TYPE = CaselessKeyword("object") | CaselessKeyword("array")
_RETURN_TYPES = Group(delimitedList(_RETURN_TYPE))
_META_FORMAT = Optional(_SQL_IDENTIFIER.setResultsName('table') + nestedExpr(content=delimitedList(Group(_SQL_IDENTIFIER + _TYPE)), ignoreExpr=None).setResultsName('columns') + Suppress(Literal(';'))) + \
    Suppress(CaselessKeyword("returns")) + Optional(CaselessKeyword("merge").setResultsName('mode') + Suppress(Literal(":"))) + _RETURN_TYPES.setResultsName('returns') + lineEnd

_COMMENT = Optional(Suppress(CaselessKeyword("COMMENT")) + quotedString.setResultsName('meta'))

_PROCEDURE_TOKEN = CaselessKeyword("CREATE") + Optional(CaselessKeyword('DEFINER') + '=' + _SQL_IDENTIFIER) + \
    CaselessKeyword("PROCEDURE") + _SQL_IDENTIFIER.setResultsName('name') + \
    nestedExpr(content=_ARGUMENTS, ignoreExpr=None).setResultsName('arguments') + _COMMENT

_PROCEDURE_END_TOKEN = Suppress(Regex('END\s*\$\$'))

_SELECT_TOKEN = CaselessKeyword("SELECT").setResultsName('op') + \
    (_COLUMNS | _EXPRESSION).setResultsName('columns') + \
    Optional(CaselessKeyword("INTO") + _SQL_IDENTIFIERS.setResultsName('into')) + \
    Optional(CaselessKeyword("FROM") + _SQL_IDENTIFIER.setResultsName('table')) + _SKIP_TO_END

_INSERT_TOKEN = CaselessKeyword("INSERT").setResultsName('op') + CaselessKeyword("INTO") + \
    _SQL_IDENTIFIER.setResultsName('table') + _SKIP_TO_END

_UPDATE_TOKEN = CaselessKeyword("UPDATE").setResultsName('op') + _SQL_IDENTIFIER.setResultsName('table') + _SKIP_TO_END

_DELETE_TOKEN = CaselessKeyword("DELETE").setResultsName('op') + CaselessKeyword("FROM") + \
    _SQL_IDENTIFIER.setResultsName('table') + _SKIP_TO_END

_THROW_TOKEN = Suppress(CaselessKeyword("CALL")) + CaselessKeyword("__throw") + \
    nestedExpr(content=quotedString.setResultsName('error_class') + Suppress(',') + quotedString, ignoreExpr=None)

_CALL_TOKEN = CaselessKeyword("CALL") + _SQL_IDENTIFIER.setResultsName('procedure') + _SKIP_TO_END


class MacrosTokenizer:
    """Preprocessor statements tokenizer"""

    grammar = \
        _INCLUDE.setResultsName('include') | \
        _DEFINE.setResultsName('define') | \
        _EXPAND.setResultsName('expand') | \
        _IF.setResultsName('if') | \
        _ELSE.setResultsName('else') | \
        _ENDIF.setResultsName('endif')

    function_class = namedtuple('Function', ('args', 'body', 'ast'))

    def __init__(self):
        """constructor"""
        self.suppress = False
        self.conditions_stack = list()
        self.functions = dict()
        self.variables = dict()

    def reset(self):
        self.suppress = False
        self.conditions_stack.clear()
        self.functions.clear()
        self.variables.clear()

    def _handle_define(self, line, token):
        """define macros"""
        if self.suppress:
            return

        if token.args:
            args = token.args[0]
            keywords = MatchFirst([Keyword('$' + x).setResultsName(x) for x in args])
            macros = self.function_class(args, token.body, list(keywords.scanString(token.body)))
            if token.name in self.functions:
                warnings.warn('%d: macros %s already defined!' % (line, token.name))
            self.functions[token.name] = macros
        else:
            if token.name in self.variables:
                warnings.warn('%d: macros %s already defined!' % (line, token.name))
            self.variables[token.name] = token.value

    def _handle_expand(self, line, token):
        """handle define macros"""

        if self.suppress:
            return

        if token.args:
            macros = self.functions[token.name]
            args = dict(zip(macros.args, token.args[0]))
            if len(args) != len(macros.args):
                raise ValueError("%d: invalid number of parameters for %s, expected %s" % (line, token.name, macros.args))
            self.on_function(macros.ast, macros.body, args)
        else:
            self.on_variable(token.name, self.variables[token.name])

    def _handle_include(self, _, token):
        """include file"""
        if not self.suppress:
            self.on_include(token.filename.strip("'\""))

    def _handle_if(self, _, token):
        """main way of condition"""
        if not self.suppress:
            self.conditions_stack.append(self.suppress)
            self.suppress = not eval(token.condition, self.variables)

    def _handle_else(self, *_):
        """alternative way of condition"""
        self.suppress = not self.suppress

    def _handle_endif(self, line, _):
        """end of condition"""
        try:
            self.suppress = self.conditions_stack.pop()
        except IndexError:
            raise ValueError("%d: mismatch if/endif" % line) from None

    def on_function(self, ast, body, args):
        """callback to catch function"""
        pass

    def on_variable(self, name, value):
        """callback to catch variable"""
        pass

    def on_include(self, filename):
        """callback to catch include"""
        pass

    def nop(self, text):
        """do nothing"""
        pass

    def parse(self, stream):
        """parse the stream"""
        current = ''

        for line, text in enumerate(map(lambda x: x.rstrip('\n '), stream)):
            if not text:
                continue

            if text[-1] == '\\':
                current += text[:-1]
                continue

            current += text + '\n'
            start = 0
            tokens = self.grammar.scanString(current)
            for token in tokens:
                if not self.suppress:
                    self.nop(current[start:token[1]])
                getattr(self, '_handle_' + token[0].getName())(line, token[0])
                start = token[2]

            if not self.suppress:
                self.nop(current[start:])
            current = ''

        if len(self.conditions_stack):
            raise ValueError("mismatch if/endif")


class _Procedure:
    """Procedure abstraction"""

    argument_class = namedtuple('Argument', ('direction', 'name', 'type'))
    command_class = namedtuple('Command', ('op', 'table', 'columns'))
    temptable_class = namedtuple('TempTable', ('name', 'columns'))
    column_class = namedtuple('Column', ('name', 'type'))
    returns_class = namedtuple('Returns', ('merge', 'types'))

    def __init__(self, name, arguments, meta):
        self.name = name
        self.arguments = [self.argument_class(*x) for x in arguments]
        self.queries = list()
        self.modifiers = list()
        self.children = list()
        self.read_only = None
        self.errors = set()
        self.temptable = None
        self.returns = None

        if meta:
            try:
                meta = _META_FORMAT.parseString(meta.strip("'\""))
                self.returns = self.returns_class(meta.mode == 'merge', tuple(meta.returns))
                if meta.table:
                    self.temptable = self.temptable_class(meta.table[0], tuple(self.column_class(*x) for x in meta.columns[0]))

            except Exception as e:
                raise ValueError('SyntaxError: procedure %s, meta %s: %s' % (name, meta, e))
        else:
            self.meta = None

    def add_read_command(self, *args):
        """handle new read command"""
        self.queries.append(self.command_class(args[0], args[1], tuple(x[-1] for x in args[2])))

    def add_write_command(self, *args):
        """handle new write command"""
        self.modifiers.append(self.command_class(*args))
        self.read_only = False

    def __repr__(self):
        return self.name


class SQLTokenizer:
    """The sql statement tokenizer"""
    procedure_class = _Procedure

    def __init__(self):
        self._grammar = \
            _PROCEDURE_TOKEN.copy().setParseAction(self.on_begin_procedure) | \
            _PROCEDURE_END_TOKEN.copy().setParseAction(self.on_end_procedure) | \
            _SELECT_TOKEN.copy().setParseAction(self.on_select) | \
            _INSERT_TOKEN.copy().setParseAction(self.on_insert) | \
            _UPDATE_TOKEN.copy().setParseAction(self.on_update) | \
            _DELETE_TOKEN.copy().setParseAction(self.on_delete) | \
            _THROW_TOKEN.copy().setParseAction(self.on_error) | \
            _CALL_TOKEN.copy().setParseAction(self.on_call)

        self._procedures = dict()
        self._current = None

    def reset(self):
        self._procedures.clear()
        self._current = None

    def on_begin_procedure(self, tokens):
        """begin of procedure handler"""
        self._current = self.procedure_class(tokens.name[0], tokens.arguments[0], tokens.meta)
        if self._current.name in self._procedures:
            raise ValueError('The procedure %s already defined!' % self._current)
        self._procedures[self._current.name] = self._current

    def on_end_procedure(self, _):
        """end of procedure handler"""
        self._current = None

    def on_select(self, tokens):
        """select statement handler"""
        if self._current and not tokens.into:
            self._current.add_read_command(tokens.op, tokens.table and tokens.table[0], tokens.columns)

    def on_insert(self, tokens):
        """insert statement handler"""
        if self._current:
            self._current.add_write_command(tokens.op, tokens.table, [])

    on_update = on_insert
    on_delete = on_insert

    def on_error(self, tokens):
        """raise keyword handler"""
        if self._current:
            self._current.errors.add(tokens[1].error_class.strip("'\""))

    def on_call(self, tokens):
        """call keyword handler"""
        if self._current:
            self._current.children.append(tokens[1])

    def parse(self, text):
        """
        parse the input text
        :param text: the sql statements
        """
        for _ in self._grammar.scanString(text):
            pass

    def procedures(self):
        """
        enumerate all of procedures
        :return: the enumerator of all procedures
        """
        return self._procedures.values()

    def errors(self, procedure=None):
        """
        get procedure errors recursively
        :param procedure: optional, start procedure
        :return the set of errors
        :rtype set
        """
        if procedure is None:
            return reduce(lambda x, y: x | y.errors, self._procedures.values(), set())

        errors = procedure.errors.copy()
        for child in set(procedure.children):
            errors |= self.errors(self._procedures[child])
        return errors

    def queries(self, procedure):
        """
        recursively return all queries that performed in specified procedure
        :param procedure: the procedure object
        :return: the list of all queries
        """
        queries = procedure.queries[:]
        for child in (self._procedures[x] for x in procedure.children):
            queries.extend(self.queries(child))
        return queries

    def is_read_only(self, procedure):
        """recursively determine that procedure read-only or not"""
        if procedure.read_only is not None:
            return procedure.read_only

        for child in (self._procedures[x] for x in procedure.children):
            if self.is_read_only(child) is False:
                procedure.read_only = False
                return False

        procedure.read_only = True
        return True
