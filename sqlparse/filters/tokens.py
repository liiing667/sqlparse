#
# Copyright (C) 2009-2020 the sqlparse authors and contributors
# <see AUTHORS file>
#
# This module is part of python-sqlparse and is released under
# the BSD License: https://opensource.org/licenses/BSD-3-Clause

from sqlparse import tokens as T


class _CaseFilter:
    ttype = None

    def __init__(self, case=None):
        case = case or 'upper'
        self.convert = getattr(str, case)

    def process(self, stream):
        for ttype, value in stream:
            if ttype in self.ttype:
                value = self.convert(value)
            yield ttype, value


class KeywordCaseFilter(_CaseFilter):
    ttype = T.Keyword


class IdentifierCaseFilter(_CaseFilter):
    ttype = T.Name, T.String.Symbol

    def __init__(self, case=None, skip_quoted=False):
        super().__init__(case)
        self.skip_quoted = skip_quoted

    def process(self, stream):
        for ttype, value in stream:
            if ttype in self.ttype and not self._is_quoted(value):
                value = self.convert(value)
            yield ttype, value

    def _is_quoted(self, value):
        first = value.strip()[:1]
        if first == '"':
            return True
        return self.skip_quoted and first in ('`', '[')


class IdentifierQuoteFilter:
    """Rewrites quoted identifiers with a uniform quote style.

    Quoted identifiers (`` `name` ``, ``"name"`` and ``[name]``) are
    recognized as a whole and re-emitted with the requested quote style.
    The quoted text itself, string literals and comments are left
    untouched.
    """

    _QUOTES = {
        'backtick': ('`', '`'),
        'double': ('"', '"'),
        'bracket': ('[', ']'),
    }

    def __init__(self, style):
        self.open, self.close = self._QUOTES[style]

    def process(self, stream):
        for ttype, value in stream:
            inner = self._unquote(ttype, value)
            if inner is not None:
                value = self._quote(inner)
            yield ttype, value

    @staticmethod
    def _unquote(ttype, value):
        """Return the unescaped text of a quoted identifier or None."""
        if ttype is T.Name and len(value) >= 2:
            if value[0] == '`' and value[-1] == '`':
                return value[1:-1].replace('``', '`')
            if value[0] == '[' and value[-1] == ']':
                return value[1:-1]
        elif ttype is T.String.Symbol and value[:1] == '"' \
                and value[-1:] == '"':
            return value[1:-1].replace('""', '"').replace('\\"', '"')
        return None

    def _quote(self, inner):
        if self.open == '[':
            escaped = inner.replace(']', ']]')
        else:
            escaped = inner.replace(self.close, self.close * 2)
        return f'{self.open}{escaped}{self.close}'


class TruncateStringFilter:
    def __init__(self, width, char):
        self.width = width
        self.char = char

    def process(self, stream):
        for ttype, value in stream:
            if ttype != T.Literal.String.Single:
                yield ttype, value
                continue

            if value[:2] == "''":
                inner = value[2:-2]
                quote = "''"
            else:
                inner = value[1:-1]
                quote = "'"

            if len(inner) > self.width:
                value = ''.join((quote, inner[:self.width], self.char, quote))
            yield ttype, value
