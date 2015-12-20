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

from unittest import TestCase
from wsql_sdk import grammar


class TestInterpreter(TestCase):
    def test_ids(self):
        """test the sql id syntax"""
        self.assertEqual("test", grammar._ID.parseString("test").name)
        self.assertEqual("test.test", grammar._ID.parseString("test.test").name)
        self.assertEqual("test_123", grammar._ID.parseString("test_123").name)

        self.assertEqual("test", grammar._SQL_ID.parseString("test")[0])
        self.assertEqual("test.test", grammar._SQL_ID.parseString("`test.test`")[0])
        self.assertEqual("test_123", grammar._SQL_ID.parseString("test_123")[0])

        self.assertEqual(["test", "test_123", "test.test"],
                         grammar._ID_LIST.parseString("test, test_123, test.test").asList())
        self.assertEqual(["test", "test_123", "test.test"],
                         grammar._SQL_ID_LIST.parseString("test, `test_123`, `test.test`").asList())

    def test_values(self):
        """test sql value syntax"""
        self.assertEqual("test", grammar._VALUE.parseString("test")[0])
        self.assertEqual("test(*)", grammar._VALUE.parseString("test(*)")[0])
        self.assertEqual("test(123)", grammar._VALUE.parseString("test(123)")[0])
        self.assertEqual("123", grammar._VALUE.parseString("123")[0])
        self.assertEqual("*", grammar._VALUE.parseString("*")[0])
        self.assertEqual("'test test'", grammar._VALUE.parseString("'test test'")[0])
        self.assertEqual("'test, test'", grammar._VALUE.parseString("'test, test'")[0])

        self.assertEqual(["test", "test(*)", "123", "'test, test'"],
                         grammar._VALUE_LIST.parseString("test, test(*), 123, 'test, test'").asList())

    def test_sql_argument(self):
        """the sql argument syntax"""
        self.assertEqual(["IN", "test", "VarChar(255)"],
                         grammar._SQL_ARG.parseString("In test VarChar(255)").asList())
        self.assertEqual(["OUT", "test.test", "INT"],
                         grammar._SQL_ARG.parseString("Out `test.test` INT").asList())
        self.assertEqual(["IN", "test_test", "BOOL(1)"],
                         grammar._SQL_ARG.parseString("test_test BOOL(1)").asList())

    def test_parentheses_expr(self):
        """"the the parentheses syntax"""
        self.assertEqual("(a(b(c(d))))", grammar._PARENTHESES_EXPR.parseString("(a(b(c(d))))")[0])

    def test_select_column(self):
        """test the select column syntax"""
        self.assertEqual("(SELECT * FROM A WHERE id > 0)",
                         grammar._NESTED_SELECT.parseString("(SELECT * FROM A WHERE id > 0)")[0])
        self.assertEqual("(SELECT COUNT(*) FROM A WHERE id > 0)",
                         grammar._NESTED_SELECT.parseString("(SELECT COUNT(*) FROM A WHERE id > 0)")[0])
        self.assertEqual("EXISTS(SELECT * FROM A WHERE id > 0)",
                         grammar._NESTED_CALL.parseString("EXISTS(SELECT * FROM A WHERE id > 0)")[0])
        self.assertEqual("MAX(*)",
                         grammar._NESTED_CALL.parseString("MAX(*)")[0])
        self.assertEqual("count",
                         grammar._SELECT_COLUMN.parseString("`count`").name[0])

        self.assertEqual(["count", "max", "id"],
                         [x[-1] for x in
                          grammar._SELECT_COLUMN_LIST.parseString(
                              "(SELECT COUNT(*) FROM A) AS `count`, MAX(*) AS `max`, id").columns])

    def test_define_variable(self):
        """test the define variable syntax"""
        self.assertEqual(['define', 'test', '"test"'],
                         grammar._DEFINE_VAR.parseString("#define test \"test\"").asList())

        self.assertEqual(['define', 'test', "f(w,x)"],
                         grammar._DEFINE_VAR.parseString("#define test f(w,x)").asList())

        self.assertEqual(['define', 'test', '"test1 test2"'],
                         grammar._DEFINE_VAR.parseString("#define test \"test1 test2\"").asList())

    def test_define_function(self):
        """test the define function syntax"""
        self.assertEqual(['define', 'test', ['a1', 'a2', 'a3'], 'f($a1, $a2, $a3)'],
                         grammar._DEFINE_FUNCTION.parseString("#define test(a1,a2,a3) f($a1, $a2, $a3)").asList())

    def test_undefine(self):
        """test the undefine syntax"""
        self.assertEqual(['undef', 'test'],
                         grammar._UNDEFINE.parseString("#undef test").asList())

    def test_expand_var(self):
        """test expand variable syntax"""
        self.assertEqual("test",
                         grammar._EXPAND_VAR.parseString("$test").name)

    def test_expand_func(self):
        """test expand  function syntax"""
        self.assertEqual(["test", ["a1", "\"a b\"", "f(w,x)"]],
                         grammar._EXPAND_FUNC.parseString("$test(a1, \"a b\", f(w,x))").asList())

    def test_include(self):
        """test the include syntax"""
        self.assertEqual(["include", "\"test.sql\""],
                         grammar._INCLUDE_FILE.parseString("#include \"test.sql\"").asList())

    def test_return_hint(self):
        """test return hint syntax"""
        self.assertEqual(["test", "object"], grammar._RETURN_HINT_EXPR.parseString("-- > test:object").asList())
        self.assertEqual(["object"], grammar._RETURN_HINT_EXPR.parseString("-- > object").asList())

    def test_temp_table(self):
        """test temp table syntax"""
        self.assertEqual(["test", [["c1", "INT"], ["c2", "VARCHAR(200)"]]],
                         grammar._TEMP_TABLE_EXPR.parseString("test(c1 INT, c2 VARCHAR(200));").asList())

    def test_meta(self):
        """the the procedure meta syntax"""
        self.assertEqual(["test", [["c1", "INT"], ["c2", "VARCHAR(200)"]], "returns", "union"],
                         grammar._PROCEDURE_COMMENT_FORMAT.parseString("test(c1 INT, c2 VARCHAR(200)); returns union").asList())
        self.assertEqual(["returns", "union"],
                         grammar._PROCEDURE_COMMENT_FORMAT.parseString("returns union").asList())

    def test_create_procedure(self):
        """test create procedure syntax"""
        self.assertEqual(["CREATE", "DEFINER", "=", "test", "PROCEDURE", "test",
                          [["IN", "a1", "INT"], ["IN", "a_2", "VARCHAR(255)"], ["OUT", "a.b", "BOOL"]], "COMMENT", "\"returns union\""],
                         grammar._CREATE_PROCEDURE.parseString(
                             "CREATE DEFINER = `test` PROCEDURE test(a1 INT,IN a_2 VARCHAR(255), OUT `a.b` BOOL) COMMENT \"returns union\"").asList())

    def test_select(self):
        """test the select statement syntax"""
        self.assertEqual(['SELECT',
                         ['MAX(*)', 'AS', 'a'], ['(SELECT 1 FROM Q)', 'AS', 'b'], ['c', 'AS', 'c.a'],
                         'FROM', 'T', ''],
                         grammar._SELECT_EXPR.parseString("SELECT MAX(*) AS a, (SELECT 1 FROM Q) AS b,"
                                                          "c AS `c.a` FROM T;").asList())
        self.assertEqual(['SELECT',
                          ['MAX(*)', 'AS', 'a'], ['(SELECT 1 FROM Q)', 'AS', 'b'], ['c', 'AS', 'c.a'],
                          ['INTO', 'a', 'b', 'c'], 'FROM', 'T', '', 'object'],
                         grammar._SELECT_EXPR.parseString("SELECT MAX(*) AS a, (SELECT 1 FROM Q) AS b,"
                                                          "c AS `c.a` INTO a,b,c FROM T; -- > object").asList())

    def test_insert(self):
        """test the insert statement syntax"""
        self.assertEqual(['INSERT', 'INTO', 'test', '(a,b) VALUES (1,2)'],
                         grammar._INSERT_EXPR.parseString("INSERT INTO test (a,b) VALUES (1,2);").asList())

    def test_update(self):
        """test the update statement syntax"""
        self.assertEqual(['UPDATE', 'test', 'set a=1'],
                         grammar._UPDATE_EXPR.parseString("UPDATE test set a=1;").asList())

    def test_delete(self):
        """test the delete statement syntax"""
        self.assertEqual(['DELETE', 'FROM', 'test', ''],
                         grammar._DELETE_EXPR.parseString("DELETE FROM test;").asList())

    def test_throw(self):
        """test throw syntax"""
        self.assertEqual(['CALL', '__throw', ["'test'", "'this is test message'"]],
                         grammar._THROW_EXPR.parseString("CALL __throw('test', 'this is test message');").asList())

    def test_call(self):
        """test procedure call syntax"""
        self.assertEqual(['CALL', 'proc1', "(1, 2)"],
                         grammar._CALL_EXPR.parseString("CALL proc1(1, 2);").asList())

    def test_create_table(self):
        """test create table syntax"""
        self.assertEqual(
            ['CREATE', 'TABLE', 'T1', '(\nc1 ENUM("a", "b", "c"), c2 SET("0", "1", "2")\n)'],
            grammar._CREATE_TABLE.parseString(
                'CREATE TABLE IF NOT EXISTS `T1`(\nc1 ENUM("a", "b", "c"), c2 SET("0", "1", "2")\n);'
            ).asList()
        )

    def test_column_options(self):
        """test column options declare syntax"""
        found = list(grammar._DECLARE_OPTIONS.scanString('(c1 ENUM("a", "b", "c"), c2 SET("0", "1", "2"));'))
        self.assertEqual(2, len(found))
        self.assertEqual('c1', found[0][0].name[0])
        self.assertEqual('ENUM', found[0][0].kind)
        self.assertEqual(['"a"', '"b"', '"c"'], found[0][0].options.asList()[0])
        self.assertEqual('c2', found[1][0].name[0])
        self.assertEqual('SET', found[1][0].kind)
        self.assertEqual(['"0"', '"1"', '"2"'], found[1][0].options.asList()[0])

    def test_sql_type(self):
        found = list(grammar._SQL_TYPE.scanString("BINARY(16), INT, DECIMAL(32, 16)"))
        self.assertEqual(3, len(found))
        self.assertEqual("BINARY(16)", found[0][0][0])
        self.assertEqual("INT", found[1][0][0])
        self.assertEqual("DECIMAL(32, 16)", found[2][0][0])
