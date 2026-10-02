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

    def process(self, stream):
        for ttype, value in stream:
            if ttype in self.ttype and value.strip()[0] not in '"`[':
                value = self.convert(value)
            yield ttype, value


class IdentifierQuoteFilter:
    """Rewrites quoted identifiers to a uniform quote style.

    Quoted identifiers (`` `name` ``, ``"name"`` and ``[name]``) are
    recognized as a whole and re-emitted with the configured quoting
    style. The case of the quoted name is preserved, occurrences of the
    target quote character inside the name are escaped by doubling.
    Anything else -- string literals, comments, unquoted names and
    unpaired brackets -- is left untouched.
    """

    ttype = T.Name, T.String.Symbol

    #: quote style -> (opening, closing character, token type to emit)
    _STYLES = {
        'backtick': ('`', '`', T.Name),
        'double': ('"', '"', T.String.Symbol),
        'bracket': ('[', ']', T.Name),
    }

    def __init__(self, style):
        self.open, self.close, self.emit_ttype = self._STYLES[style]

    def _unquote(self, value):
        """Return the unescaped name of a quoted identifier, or None if
        `value` is not a quoted identifier."""
        if len(value) < 2:
            return None
        first, last = value[0], value[-1]
        if first == '`' and last == '`':
            return value[1:-1].replace('``', '`')
        if first == '"' and last == '"':
            return value[1:-1].replace('""', '"')
        if first == '[' and last == ']':
            return value[1:-1]
        return None

    def process(self, stream):
        for ttype, value in stream:
            if ttype in self.ttype:
                name = self._unquote(value)
                if name is not None:
                    escaped = name.replace(self.close, self.close * 2)
                    value = f'{self.open}{escaped}{self.close}'
                    ttype = self.emit_ttype
            yield ttype, value


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
