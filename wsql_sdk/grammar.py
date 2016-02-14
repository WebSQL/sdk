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

from collections import defaultdict, namedtuple
from functools import reduce
from pyparsing import alphanums, CaselessKeyword, Combine, delimitedList, Group, Keyword, Literal, \
    lineEnd, lineStart, MatchFirst, nestedExpr, nums, oneOf, Optional, Regex, Suppress, Word, \
    quotedString, SkipTo, Forward, White
import warnings


def _sql_identifier(expr):
    return Suppress(Optional('`')) + expr + Suppress(Optional('`'))


def _macros(expr):
    return lineStart + Suppress(Literal("#")) + expr


def _sql_comment(expr):
    return lineStart + Suppress(Literal("-- ")) + expr


def _select_hint(expr):
    return Suppress(Literal("-- >")) + expr

# keywords
_DEFINE = _macros(CaselessKeyword("define"))
_UNDEF = _macros(CaselessKeyword("undef"))
_INCLUDE = _macros(CaselessKeyword("include"))
_IF = _macros(CaselessKeyword("if"))
_ELSE = _macros(CaselessKeyword("else"))
_ENDIF = _macros(CaselessKeyword("endif"))

_AS = CaselessKeyword("AS")
_CALL = CaselessKeyword("CALL")
_COMMENT = CaselessKeyword("COMMENT")
_CREATE = CaselessKeyword("CREATE")
_DEFINER = CaselessKeyword("DEFINER")
_PROCEDURE = CaselessKeyword("PROCEDURE")
_TABLE = CaselessKeyword("TABLE")
_INTO = CaselessKeyword("INTO")
_FROM = CaselessKeyword("FROM")
_ENUM = CaselessKeyword("ENUM")
_SET = CaselessKeyword("SET")
_SELECT = CaselessKeyword("SELECT").setResultsName("command")
_DELETE = CaselessKeyword("DELETE").setResultsName("command")
_INSERT = CaselessKeyword("INSERT").setResultsName("command")
_UPDATE = CaselessKeyword("UPDATE").setResultsName("command")
IF_NOT_EXISTS = Group("IF") + CaselessKeyword("NOT") + CaselessKeyword("EXISTS")

_THROW = _sql_identifier(Keyword("__throw"))
_RETURNS = CaselessKeyword("returns")
_SQL_EOL = Literal(";")


_ID = Word(alphanums + "_.").setResultsName("name")
_ID_LIST = delimitedList(_ID, combine=False)
_VALUE = (Combine(_ID + Literal("(") + SkipTo(")", include=True)) |
          Word(alphanums + "$!#%&*+-./:<=>?@[\]^_~`") | quotedString).setResultsName("value")
_VALUE_LIST = delimitedList(_VALUE, combine=False)

_SQL_DIRECTION = oneOf('INOUT IN OUT', caseless=True)
_SQL_TYPE = Combine(Word(alphanums + '_') + Optional('(' + delimitedList(Word(nums + ' '), combine=True) + ')'))
_SQL_ID = _sql_identifier(_ID)
_SQL_ID_LIST = delimitedList(_SQL_ID, combine=False)
_SKIP_TO_END = SkipTo(_SQL_EOL)
_PARENTHESES_EXPR = Forward()
_PARENTHESES_EXPR << Combine("(" + SkipTo(")", ignore=_PARENTHESES_EXPR, include=True))
_NESTED_SELECT = Combine("(" + _SELECT + SkipTo(")", include=True, ignore=_PARENTHESES_EXPR))
_NESTED_CALL = Combine(_SQL_ID + Literal("(") + SkipTo(Literal(")"), include=True))
_SELECT_COLUMN = (_NESTED_SELECT | _NESTED_CALL | _SQL_ID.setResultsName("name")) + \
    Optional(_AS + _SQL_ID.setResultsName("alias"))

_TABLE_NAME = _SQL_ID.setResultsName("table")
_PROCEDURE_NAME = _sql_identifier(Word(alphanums + "_.:").setResultsName("name")).setResultsName('name')

_SELECT_COLUMN_LIST = delimitedList(Group(_SELECT_COLUMN), combine=False).setResultsName("columns")
_SQL_ARG = Optional(_SQL_DIRECTION, default='IN') + _SQL_ID + _SQL_TYPE
_SQL_ARGS = delimitedList(Group(_SQL_ARG), combine=False)

_RETURN_TYPE = oneOf("object array", caseless=True).setResultsName("type")

# expressions
_DEFINE_FUNCTION = _DEFINE + _ID + nestedExpr(content=_ID_LIST, ignoreExpr=None).setResultsName("args") + \
    Suppress(White()) + Regex(".*$").setResultsName("body")

_DEFINE_VAR = _DEFINE + _ID + SkipTo(lineEnd, include=True).setResultsName("value")
_UNDEFINE = _UNDEF + _ID
_INCLUDE_FILE = _INCLUDE + quotedString.setResultsName("filename")
_EXPAND_VAR = Suppress('$') + _ID
_EXPAND_FUNC = Suppress('$') + _ID + nestedExpr(content=_VALUE_LIST, ignoreExpr=None).setResultsName("args")

_IF_EXPR = _IF + SkipTo(lineEnd, include=True).setResultsName("condition")
_ELSE_EXPR = _ELSE + lineEnd
_ENDIF_EXPR = _ENDIF + lineEnd

_RETURN_HINT_EXPR = _select_hint(Optional(_ID + Suppress(Literal(":"))) + _RETURN_TYPE).setResultsName("hint")
_TEMP_TABLE_EXPR = _SQL_ID.setResultsName('table') + \
    nestedExpr(content=delimitedList(Group(_SQL_ID + _SQL_TYPE)), ignoreExpr=None).setResultsName('columns') +\
    Suppress(Literal(';'))

_PROCEDURE_COMMENT_FORMAT = Optional(_TEMP_TABLE_EXPR) + Optional(_RETURNS + oneOf("union", caseless=True).setResultsName("mode")) + lineEnd

_CREATE_PROCEDURE = _CREATE + Optional(_DEFINER + '=' + _SQL_ID) + _PROCEDURE + _PROCEDURE_NAME + \
    nestedExpr(content=_SQL_ARGS, ignoreExpr=None).setResultsName('args') + Optional(_COMMENT + quotedString.setResultsName("comment"))

_END_PROCEDURE = Regex('END\s*\$\$')

_DECLARE_CURSOR = CaselessKeyword('DECLARE') + _SQL_ID + CaselessKeyword('CURSOR') + CaselessKeyword('FOR') + _SKIP_TO_END
_SELECT_EXPR = _SELECT + _SELECT_COLUMN_LIST + Optional(Group(_INTO + _SQL_ID_LIST).setResultsName("into")) + \
    Optional(_FROM + _TABLE_NAME) + _SKIP_TO_END + Suppress(_SQL_EOL) + Optional(_RETURN_HINT_EXPR)

_INSERT_EXPR = _INSERT + _INTO + _TABLE_NAME + _SKIP_TO_END
_UPDATE_EXPR = _UPDATE + _TABLE_NAME + _SKIP_TO_END
_DELETE_EXPR = _DELETE + _FROM + _TABLE_NAME + _SKIP_TO_END

_THROW_EXPR = _CALL + _THROW + nestedExpr(content=_VALUE_LIST, ignoreExpr=None).setResultsName("args")

_CALL_EXPR = _CALL + _PROCEDURE_NAME + _SKIP_TO_END

_CONSTANT = _sql_comment(Keyword("CONSTANT")) + _ID + SkipTo(lineEnd, include=True).setResultsName("value")

_CREATE_TABLE = _CREATE + _TABLE + Suppress(Optional(IF_NOT_EXISTS)) + _SQL_ID.setResultsName('name') + \
    SkipTo(";").setResultsName('body')

_DECLARE_OPTIONS = _SQL_ID.setResultsName('name') + (_ENUM | _SET).setResultsName('kind') + \
    nestedExpr(content=delimitedList(quotedString, ',', combine=False), ignoreExpr=None).setResultsName('options')


class MacrosTokenizer:
    """Preprocessor statements tokenizer"""

    _expand = \
        _EXPAND_FUNC.setResultsName("expand_function") | \
        _EXPAND_VAR.setResultsName('expand_var')

    grammar = \
        _INCLUDE_FILE.setResultsName('include') | \
        _DEFINE_FUNCTION.setResultsName('define') | \
        _DEFINE_VAR.setResultsName('define') | \
        _UNDEFINE.setResultsName('undefine') | \
        _IF_EXPR.setResultsName('if') | \
        _ELSE_EXPR.setResultsName('else') | \
        _ENDIF_EXPR.setResultsName('endif') | \
        _expand

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

    def _expand_var(self, target):
        """expand the macros"""
        name = target.name
        if name in self.variables:
            return self.variables[name]
        return '$' + name

    def _expand_function(self, target):
        """expand the macro function"""
        macros = self.functions[target.name]
        args = (x.startswith('$') and self.variables.get(x[1:], x) or x for x in target.args[0])
        args = dict(zip(macros.args, args))
        if len(args) != len(macros.args):
            raise ValueError("invalid number of parameters for %s, expected %s" % (target.name, macros.args))

        start = 0
        buffer = ''
        for t in macros.ast:
            buffer += macros.body[start:t[1]]
            buffer += args[t[0].getName()]
            start = t[2]
        return buffer + macros.body[start:]

    def _recurisve_expand(self, value):
        """recursive expand macros"""
        buffer = ''
        start = 0
        for t in self._expand.scanString(value):
            buffer += value[start:t[1]]
            buffer += getattr(self, '_' + t[0].getName())(t[0])
            start = t[2]
        return buffer + value[start:]

    def _handle_define(self, line, token):
        """define macro function"""
        if self.suppress:
            return

        if token.args:
            args = token.args[0]
            keywords = MatchFirst([Keyword('$' + x).setResultsName(x) for x in args])
            body = self._recurisve_expand(token.body)
            macros = self.function_class(args, body, list(keywords.scanString(body)))
            if token.name in self.functions:
                warnings.warn('%d: macros %s already defined!' % (line, token.name))
            self.functions[token.name] = macros
        else:
            if token.name in self.variables:
                warnings.warn('%d: macros %s already defined!' % (line, token.name))

            value = self.variables[token.name] = self._recurisve_expand(token.value)
            if not token.name.startswith("_"):
                self.on_constant(token.name, value)

    def _handle_undefine(self, line, token):
        """undefine the function or variable"""
        if self.suppress:
            return

        if token.name in self.variables:
            del self.variables[token.name]
        elif token.name in self.functions:
            del self.functions[token.name]
        else:
            warnings.warn('%d: macros %s is not defined!' % (line, token.name))

    def _handle_expand_function(self, line, token):
        """handle expand macro function"""

        if self.suppress:
            return

        macros = self.functions[token.name]
        if len(macros.body) == 0:
            return
        expanded_args = (x.startswith('$') and self.variables.get(x[1:], x) or x for x in token.args[0])
        args = dict(zip(macros.args, expanded_args))
        if len(args) != len(macros.args):
            raise ValueError("%d: invalid number of parameters for %s, expected %s" % (line, token.name, macros.args))

        self.on_function(macros.ast, macros.body, args)

    def _handle_expand_var(self, _, token):
        """handle expand macro variable"""
        if not self.suppress:
            if token.name in self.variables:
                self.on_variable(token.name, self.variables[token.name])
            else:
                warnings.warn("Undefined variable: %s" % token.name)
                self.on_variable(token.name, "$" + token.name)

    def _handle_include(self, _, token):
        """include file"""
        if not self.suppress:
            self.on_include(token.filename.strip("'\""))

    def _handle_if(self, _, token):
        """main way of condition"""
        if not self.suppress:
            self.conditions_stack.append(self.suppress)
            try:
                self.suppress = not eval(token.condition, {'defined': lambda x: x in self.variables}, self.variables)
            except Exception as e:
                raise RuntimeError("Failed to evaluate expression: {0}, details: {1}".format(token.condition, e))

    def _handle_else(self, *_):
        """alternative way of condition"""
        self.suppress = not self.suppress

    def _handle_endif(self, line, _):
        """end of condition"""
        try:
            self.suppress = self.conditions_stack.pop()
        except IndexError:
            raise ValueError("%d: mismatch if/endif" % line) from None

    def on_constant(self, name, value):
        """callback to catch constants"""
        pass

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


class _Procedure:
    """Procedure abstraction"""

    argument_class = namedtuple('Argument', ('direction', 'name', 'type'))
    command_class = namedtuple('Command', ('op', 'table', 'columns'))
    temptable_class = namedtuple('TempTable', ('name', 'columns'))
    column_class = namedtuple('Column', ('name', 'type'))
    returns_class = namedtuple('Return', ('name', 'type', 'fields'))

    def __init__(self, name, arguments, comment):
        self.name = name
        self.arguments = [self.argument_class(*x) for x in arguments if x]
        self.queries = list()
        self.modifiers = list()
        self.children = list()
        self.read_only = None
        self.errors = set()
        self.temptable = None
        self.returns = list()
        self.return_mod = None

        if comment:
            try:
                hint = _PROCEDURE_COMMENT_FORMAT.parseString(comment.strip("'\""))
                self.return_mod = hint.mode
                if hint.table:
                    self.temptable = self.temptable_class(hint.name, tuple(self.column_class(*x) for x in hint.columns[0]))
            except Exception as e:
                raise ValueError('SyntaxError: procedure %s, comment %s: %s' % (name, comment, e))

    def add_read_command(self, *args):
        """handle new read command"""
        self.queries.append(self.command_class(*args))

    def add_write_command(self, *args):
        """handle new write command"""
        self.modifiers.append(self.command_class(*args))
        self.read_only = False

    def add_return(self, *args):
        self.returns.append(self.returns_class(*args))

    def __repr__(self):
        return self.name


class SQLTokenizer:
    """The sql statement tokenizer"""
    procedure_class = _Procedure

    def __init__(self):
        self._grammar = \
            _CREATE_PROCEDURE.copy().setParseAction(self.on_begin_procedure) | \
            _END_PROCEDURE.copy().setParseAction(self.on_end_procedure) | \
            _DECLARE_CURSOR.copy() | \
            _SELECT_EXPR.copy().setParseAction(self.on_select) | \
            _INSERT_EXPR.copy().setParseAction(self.on_insert) | \
            _UPDATE_EXPR.copy().setParseAction(self.on_update) | \
            _DELETE_EXPR.copy().setParseAction(self.on_delete) | \
            _THROW_EXPR.copy().setParseAction(self.on_error) | \
            _CALL_EXPR.copy().setParseAction(self.on_call) | \
            _CONSTANT.copy().setParseAction(self.on_constant) | \
            _CREATE_TABLE.copy().setParseAction(self.on_table)

        self._procedures = dict()
        self._constants = list()
        self._structures = dict()
        self._current = None

    @staticmethod
    def _column_name(column):
        if column.alias:
            return column.alias[0]
        if column.name:
            return column.name[0].rpartition('.')[-1]
        return str(column)

    def reset(self):
        self._procedures.clear()
        self._current = None

    def on_begin_procedure(self, tokens):
        """catch the begin of procedure"""
        self._current = self.procedure_class(tokens.name[0], tokens.args[0], tokens.comment)
        if self._current.name in self._procedures:
            raise ValueError('The procedure %s already defined!' % self._current)
        self._procedures[self._current.name] = self._current

    def on_end_procedure(self, _):
        """catch the end of procedure"""
        self._current = None

    def on_select(self, tokens):
        """catch the select statement"""
        if self._current and not tokens.into:
            columns = tuple(self._column_name(x) for x in tokens.columns)
            self._current.add_read_command(tokens.op, tokens.table and tokens.table[0], columns)
            return_hint = tokens.hint
            if return_hint:
                name = return_hint.name
                rtype = return_hint.type
            else:
                name = ""
                rtype = ""

            self._current.add_return(name, rtype or "object", columns)

    def on_insert(self, tokens):
        """catch the modify statement"""
        if self._current:
            self._current.add_write_command(tokens.op, tokens.table, [])

    on_update = on_insert
    on_delete = on_insert

    def on_error(self, tokens):
        """catch the raising of the exception"""
        if self._current:
            self._current.errors.add(tokens.args[0][0].strip("'\""))

    def on_constant(self, token):
        """catch constants"""
        self._constants.append((token.name, token.value))

    def on_table(self, tokens):
        """catch the table"""
        table_name = tokens.name.name
        structures = defaultdict(list)
        for t in _DECLARE_OPTIONS.scanString(tokens.body):
            t = t[0]
            structures[t.kind].append((t.name.name, sorted(x.strip('"\'') for x in t.options[0])))

        if len(structures) > 0:
            self._structures[table_name] = structures

    def on_call(self, tokens):
        """catch the procedure call"""
        if self._current:
            self._current.children.append(tokens[1])

    def parse(self, text):
        """
        parse the input text
        :param text: the sql statements
        """
        for _ in self._grammar.scanString(text):
            pass

    def constants(self):
        """
        :return: the list of constants
        """
        return self._constants

    def structures(self, name):
        """
        :return: the list of enums
        """
        if name in self._structures:
            return self._structures[name]

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

    def returns(self, procedure):
        """
        get procedure returns recursively
        :param procedure: optional, start procedure
        :return the set of errors
        :rtype set
        """
        returns = list(procedure.returns)
        for child in procedure.children:
            returns.extend(self.returns(self._procedures[child]))
        return returns

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
