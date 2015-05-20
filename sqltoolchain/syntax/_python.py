# @copyright (c) 2002-2015 Acronis International GmbH. All rights reserved.
# since    $Id: $

__author__ = "Bulat Gaifullin (bulat.gaifullin@acronis.com)"


def doc_open():
    """start doc-string"""
    return '    """'


def doc_close():
    """start doc-string"""
    return '    """'


def doc_arg(name, brief):
    """argument of doc_string"""
    return "    :param {0}: {1})".format(name, brief)


def doc_brief(brief):
    """format brief for doc-string"""
    return "    " + brief


def doc_errors(errors):
    """format errors for doc-string"""
    return "    :raises: {0}".format(', '.join(errors))


def doc_return(returns):
    """format return for doc-string"""
    return "    :return {0}".format(repr(returns).replace("\'", '"'))


def format_result(name, result):
    if name:
        return '{{"{0}": {1}}}'.format(name, result)
    return result


def return_empty():
    """return empty value"""
    pass


def return_one(result):
    """return one statement"""
    return "            return " + result


def return_tuple_open():
    """tuple of statements, open statement"""
    return "            return ("


def return_tuple_item(item):
    """tuple of statements, next statement"""
    return "                {0},".format(item)


def return_tuple_close():
    """tuple of statements, close statement"""
    return "            )"


def return_union_open(first):
    """union of statements, open statement"""
    return "            __result = " + first


def return_union_item(item):
    """union of statements, next statement"""
    return "            __result.update({0})".format(item)


def return_union_close():
    """union of statements, close statement"""
    return "            return __result"


def exception_class(name):
    """declare exception class"""
    return "class {0}(UserError):\n    pass".format(name)
