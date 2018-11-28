#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Definitions for a Dialect object.

Author: Gertjan van den Burg
Copyright (c) 2018 - The Alan Turing Institute
License: See the LICENSE file.

"""


import sys

from functools import total_ordering

ATTRIBUTES = ["delimiter", "quotechar", "escapechar"]


@total_ordering
class Dialect(object):
    def __init__(self, delimiter, quotechar, escapechar):
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.escapechar = escapechar

    def validate(self):
        if self.delimiter is None or len(self.delimiter) > 1:
            raise ValueError(
                "Delimiter should be zero or one characters, got: %r"
                % self.delimiter
            )
        if self.quotechar is None or len(self.quotechar) > 1:
            raise ValueError(
                "Quotechar should be zero or one characters, got: %r"
                % self.quotechar
            )
        if self.escapechar is None or len(self.escapechar) > 1:
            raise ValueError(
                "Escapechar should be zero or one characters, got: %r"
                % self.escapechar
            )
        if self.quotechar in ["Q", "A"]:
            print(
                "Warning: quotechar is 'Q' or 'A', probably a mistake.",
                file=sys.stderr,
            )

    @classmethod
    def from_dict(cls, d):
        d = cls(d["delimiter"], d["quotechar"], d["escapechar"])
        return d

    def to_dict(self):
        self.validate()
        d = dict(delimiter=self.delimiter, quotechar=self.quotechar, 
                escapechar=self.escapechar)
        return d

    def __repr__(self):
        return "(%r, %r, %r)" % (
            self.delimiter,
            self.quotechar,
            self.escapechar,
        )

    def __key(self):
        return (self.delimiter, self.quotechar, self.escapechar)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if not isinstance(other, Dialect):
            return False
        return self.__key() == other.__key()

    def __lt__(self, other):
        if not isinstance(other, Dialect):
            return -1
        return self.__key() < other.__key()
