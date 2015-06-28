# @copyright (c) 2002-2015 Acronis International GmbH. All rights reserved.
# since    $Id: $

__author__ = "Bulat Gaifullin (bulat.gaifullin@acronis.com)"

from unittest import TestCase

from wsql_sdk import grammar


class TestInterpreter(TestCase):
    def test_ids(self):
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
        self.assertEqual(["IN", "test", "VarChar(255)"],
                         grammar._SQL_ARG.parseString("In test VarChar(255)").asList())
        self.assertEqual(["OUT", "test.test", "INT"],
                         grammar._SQL_ARG.parseString("Out `test.test` INT").asList())
        self.assertEqual(["IN", "test_test", "BOOL(1)"],
                         grammar._SQL_ARG.parseString("test_test BOOL(1)").asList())

    def test_parentheses_expr(self):
        self.assertEqual("(a(b(c(d))))", grammar._PARENTHESES_EXPR.parseString("(a(b(c(d))))")[0])

    def test_select_column(self):
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
        self.assertEqual(['define', 'test', '"test"'],
                         grammar._DEFINE_VAR.parseString("#define test \"test\"").asList())

        self.assertEqual(['define', 'test', "f(w,x)"],
                         grammar._DEFINE_VAR.parseString("#define test f(w,x)").asList())

        self.assertEqual(['define', 'test', '"test1 test2"'],
                         grammar._DEFINE_VAR.parseString("#define test \"test1 test2\"").asList())

    def test_define_function(self):
        self.assertEqual(['define', 'test', ['a1', 'a2', 'a3'], 'f($a1, $a2, $a3)'],
                         grammar._DEFINE_FUNCTION.parseString("#define test(a1,a2,a3) f($a1, $a2, $a3)").asList())

    def test_undefine(self):
        self.assertEqual(['undef', 'test'],
                         grammar._UNDEFINE.parseString("#undef test").asList())

    def test_expand_var(self):
        self.assertEqual("test",
                         grammar._EXPAND_VAR.parseString("$test").name)

    def test_expand_func(self):
        self.assertEqual(["test", ["a1", "\"a b\"", "f(w,x)"]],
                         grammar._EXPAND_FUNC.parseString("$test(a1, \"a b\", f(w,x))").asList())

    def test_include(self):
        self.assertEqual(["include", "\"test.sql\""],
                         grammar._INCLUDE_FILE.parseString("#include \"test.sql\"").asList())

    def test_return_hint(self):
        self.assertEqual(["test", "object"], grammar._RETURN_HINT_EXPR.parseString("-- > test:object").asList())
        self.assertEqual(["object"], grammar._RETURN_HINT_EXPR.parseString("-- > object").asList())

    def test_temp_table(self):
        self.assertEqual(["test", [["c1", "INT"], ["c2", "VARCHAR(200)"]]],
                         grammar._TEMP_TABLE_EXPR.parseString("test(c1 INT, c2 VARCHAR(200));").asList())

    def test_meta(self):
        self.assertEqual(["test", [["c1", "INT"], ["c2", "VARCHAR(200)"]], "returns", "union"],
                         grammar._PROCEDURE_COMMENT_FORMAT.parseString("test(c1 INT, c2 VARCHAR(200)); returns union").asList())
        self.assertEqual(["returns", "union"],
                         grammar._PROCEDURE_COMMENT_FORMAT.parseString("returns union").asList())

    def test_create_procedure(self):
        self.assertEqual(["CREATE", "DEFINER", "=", "test", "PROCEDURE", "test",
                          [["IN", "a1", "INT"], ["IN", "a_2", "VARCHAR(255)"], ["OUT", "a.b", "BOOL"]], "COMMENT", "\"returns union\""],
                         grammar._CREATE_PROCEDURE.parseString(
                             "CREATE DEFINER = `test` PROCEDURE test(a1 INT,IN a_2 VARCHAR(255), OUT `a.b` BOOL) COMMENT \"returns union\"").asList())

    def test_select(self):
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
        self.assertEqual(['INSERT', 'INTO', 'test', '(a,b) VALUES (1,2)'],
                         grammar._INSERT_EXPR.parseString("INSERT INTO test (a,b) VALUES (1,2);").asList())

    def test_update(self):
        self.assertEqual(['UPDATE', 'test', 'set a=1'],
                         grammar._UPDATE_EXPR.parseString("UPDATE test set a=1;").asList())

    def test_delete(self):
        self.assertEqual(['DELETE', 'FROM', 'test', ''],
                         grammar._DELETE_EXPR.parseString("DELETE FROM test;").asList())

    def test_throw(self):
        self.assertEqual(['CALL', '__throw', ["'test'", "'this is test message'"]],
                         grammar._THROW_EXPR.parseString("CALL __throw('test', 'this is test message');").asList())

    def test_call(self):
        self.assertEqual(['CALL', 'proc1', "(1, 2)"],
                         grammar._CALL_EXPR.parseString("CALL proc1(1, 2);").asList())
