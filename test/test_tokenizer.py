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

from unittest import TestCase
from sqltoolchain import _interpreter


_TEST_PROCEDURE1 = """
CREATE PROCEDURE `test_procedure1` (IN `varchar` VARCHAR(255), OUT b boolEAN)
 COMMENT 'returns object, object, object, object, object, object'
BEGIN
  SELECT
   2
  INTO
   a
  FROM
   b
  where
   3;

  SELECT 1;
  SELECT 3 AS a;

  SELECT `a` FROM `b` WHERE t
  UNION
    SELECT `a` FROM `c` WHERE y;

  SELECT (EXISTS(SELECT 1 FROM t WHERE y)) AS a;
  SELECT a FROM b a JOIN i WHERE j IN (SELECT y FROM d);

  SELECT a,b,c AS d FROM y WHERE i ORDER BY u;
END$$

SELECT 2 INTO a2 FROM t2 WHERE k=1;
"""

_TEST_PROCEDURE2 = """
CREATE PROCEDURE `test_procedure2` ()
 COMMENT "args (c1 INT, c2 BINARY(255)); returns array"
BEGIN
    INSERT
     INTO
      l
        (a,b)
         VALUES(1,2);
     UPDATE
         k
         SET
         b=1
         WHERE
         j=1;
     DELETE
        FROM l
        WHERE
        j=1;
    SELECT a FROM b;
END$$

UPDATE k SET l = 2 WHERE b=1;
"""

_TEST_PROCEDURE3 = """
CREATE PROCEDURE `test_procedure3` ()
 COMMENT "args (c1 INT, c2 BINARY(255)); returns merge: object, object, object"
BEGIN
    CALL __test_procedure3(1);
    CALL __test_procedure3(2);
    CALL __throw("TestError1", "test message1")
    SELECT a FROM b;
END$$

CALL __test_procedure3(1);

CREATE PROCEDURE `__test_procedure3` ()
BEGIN
    DELETE FROM e where i=1;
    SELECT c FROM d;
    CALL __throw("TestError2", "test message2")
END$$

"""

_TEST_PROCEDURE_INVALID1 = """
CREATE PROCEDURE `test_invalid1` ()
 COMMENT "args (c1 INT, c2 BINARY(255)); returns object, object, dict"
BEGIN
END$$
"""

_TEST_PROCEDURE_INVALID2 = """
CREATE PROCEDURE `test_invalid2` ()
 COMMENT "args (c1 INT, c2 BINARY(255)); returns object, object"
BEGIN
END$$
CREATE PROCEDURE `test_invalid2` ()
 COMMENT "args (c1 INT, c2 BINARY(255)); returns object, object"
BEGIN
END$$
"""


class TestTokenizer(TestCase):
    """
    Test the procedure analyzer of interpreter
    """
    def setUp(self):
        self.tokenizer = _interpreter.SQLTokenizer()

    def test_scan_select(self):
        """ test scan select statement in procedures """
        self.tokenizer.parse(_TEST_PROCEDURE1)
        self.assertEqual(1, len(self.tokenizer._procedures))
        procedure = self.tokenizer._procedures['test_procedure1']
        self.assertEqual('test_procedure1', procedure.name)
        self.assertEqual(6, len(procedure.queries))
        self.assertEqual(0, len(procedure.modifiers))
        self.assertTrue(self.tokenizer.is_read_only(procedure))
        self.assertEqual(('1',), procedure.queries[0].columns)
        self.assertEqual(('a', 'b', 'd'), procedure.queries[5].columns)
        for i in range(1, 5):
            self.assertEqual(('a',), procedure.queries[1].columns)

    def test_scan_write_statement(self):
        """ test scan statements that modify data like insert,update,delete """
        self.tokenizer.parse(_TEST_PROCEDURE2)
        self.assertEqual(1, len(self.tokenizer._procedures))
        procedure = self.tokenizer._procedures['test_procedure2']
        self.assertEqual('test_procedure2', procedure.name)
        self.assertFalse(self.tokenizer.is_read_only(procedure))
        self.assertEqual(3, len(procedure.modifiers))

    def test_scan_call_hierarchy(self):
        """ test scan procedures call hierarchy and properly handle results """
        self.tokenizer.parse(_TEST_PROCEDURE3)
        self.assertEqual(2, len(self.tokenizer._procedures))
        p3 = self.tokenizer._procedures['test_procedure3']
        self.assertEqual(['__test_procedure3', '__test_procedure3'], p3.children)
        p4 = self.tokenizer._procedures['__test_procedure3']
        self.assertFalse(self.tokenizer.is_read_only(p3))
        self.assertFalse(self.tokenizer.is_read_only(p4))
        self.assertEqual(3, len(self.tokenizer.queries(p3)))
        self.assertEqual(1, len(self.tokenizer.queries(p4)))
        self.assertEqual({"test_procedure3", "__test_procedure3"}, set(str(x) for x in self.tokenizer.procedures()))

    def test_scan_errors(self):
        """ test scan errors """
        self.tokenizer.parse(_TEST_PROCEDURE3)
        errors = self.tokenizer.errors(None)
        self.assertEqual({"TestError1", "TestError2"}, errors)
        errors = self.tokenizer.errors(self.tokenizer._procedures["test_procedure3"])
        self.assertEqual({"TestError1", "TestError2"}, errors)
        errors = self.tokenizer.errors(self.tokenizer._procedures["__test_procedure3"])
        self.assertEqual({"TestError2"}, errors)

    def test_parse_meta(self):
        """ test parse meta """
        self.tokenizer.parse(_TEST_PROCEDURE1)
        proc = self.tokenizer._procedures["test_procedure1"].returns.types
        self.assertEqual(6, len(self.tokenizer._procedures["test_procedure1"].returns.types))
        self.assertTrue(any(x == "object" for x in proc))

        self.tokenizer.reset()
        self.assertRaisesRegex(ValueError, "SyntaxError: procedure test_invalid1",
                               self.tokenizer.parse, _TEST_PROCEDURE_INVALID1)

    def test_error_if_duplicate(self):
        """ test raise error if there is 2 procedures with same name"""
        self.assertRaisesRegex(ValueError, "The procedure test_invalid2 already defined",
                               self.tokenizer.parse, _TEST_PROCEDURE_INVALID2)