# -*- coding: utf-8 -*-
"""Simple line parser.

Parses a line of input one character at a time.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import re


class LineParser(object):
    """Parses a line of input one character at a time.
    Call set_line() prior to other metho calls.
    """

    def __init__(self, next_id=0):
        self._id = next_id
        self.index = 0
        self.line = ""
        self.line_number = 0

    def assert_char(self, char):
        """Raises an Error unless the current character matches"""
        if self.next_char() != char:
            self.raise_error("expected {}".format(char))
        self.ignore_whitespace()

    def assert_end_of_line(self, comment_char="!"):
        """Raises an error unless the remaining line is empty"""
        self.ignore_whitespace()
        if self.has_char() and self.peek_char() != comment_char:
            self.raise_error("left-over input")

    def has_char(self):
        return self.index < len(self.line)

    def ignore_whitespace(self):
        """Skip whitespace"""
        while self.has_char() and re.search(r"\s", self.peek_char()):
            self.next_char()

    def increment_line_number(self):
        self.line_number += 1

    def get_index(self):
        return self.index

    def next_char(self):
        """Advance to the next character. Returns None if end of line"""
        if self.has_char():
            current = self.line[self.index]
            self.index += 1
            return current
        return None

    def next_id(self):
        self._id += 1
        return self._id

    def parse_quoted_value(self):
        self.assert_char('"')
        value = self.read_until('"')
        if self.line[self.index - 1] == "\\":
            value += '"' + self.parse_quoted_value()
        else:
            self.assert_char('"')
        return value

    def parse_value(self, end_regex=r"[\s,=\!)*]"):
        """Parses a value, possibly quoted."""
        if self.peek_char() == '"':
            return self.parse_quoted_value()
        return self.read_until(end_regex)

    def peek_char(self):
        if self.has_char():
            return self.line[self.index]
        return None

    def raise_error(self, message):
        raise IOError(
            "line {}, {}: {}".format(self.line_number, message, self.line[self.index :])
        )

    def read_until(self, regex):
        """Reads until the end-of-line or the character regex is matched"""
        value = ""
        while self.has_char() and not re.search(regex, self.peek_char()):
            value += self.next_char()
        self.ignore_whitespace()
        return value

    def reset_index(self, index):
        """Reset the character index"""
        self.index = index

    def set_line(self, line):
        """Prepares a line for parsing."""
        self.line = line
        self.index = 0
