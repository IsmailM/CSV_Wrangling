#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Detect normal forms of CSV files.

Author: Gertjan van den Burg
Copyright (c) 2018 - The Alan Turing Institute
License: See the LICENSE file.

"""

import itertools
import json
import sys
import regex

from common.encoding import get_encoding
from common.load import load_file
from common.escape import is_potential_escapechar
from common.utils import pairwise

DELIMS = set([",", ";", "|", "\t"])


def is_quoted_cell(cell, quotechar):
    if len(cell) < 2:
        return False
    return cell[0] == quotechar and cell[-1] == quotechar


def is_any_quoted_cell(cell):
    return is_quoted_cell(cell, "'") or is_quoted_cell(cell, '"')


def is_any_partial_quoted_cell(cell):
    if len(cell) < 1:
        return False
    return (
        cell[0] == '"' or cell[0] == "'" or cell[-1] == '"' or cell[-1] == "'"
    )


def is_empty_quoted(cell, quotechar):
    return len(cell) == 2 and is_quoted_cell(cell, quotechar)


def is_empty_unquoted(cell):
    return cell == ""


def is_any_empty(cell):
    return (
        is_empty_unquoted(cell)
        or is_empty_quoted(cell, "'")
        or is_empty_quoted(cell, '"')
    )


def has_delimiter(string, delim):
    return delim in string


def has_nested_quotes(string, quotechar):
    return quotechar in string[1:-1]


def maybe_has_escapechar(data, encoding, delim, quotechar):
    if not delim in data and not quotechar in data:
        return False
    for u, v in pairwise(data):
        if v in [delim, quotechar] and is_potential_escapechar(u, encoding):
            return True
    return False


def strip_trailing_crnl(data):
    while data.endswith("\n"):
        data = data.rstrip("\n")
    while data.endswith("\r"):
        data = data.rstrip("\r")
    return data


def every_row_has_delim(rows, delim):
    for row in rows:
        if not has_delimiter(row, delim):
            return False
    return True


def is_elementary(cell):
    return not (
        regex.fullmatch("[a-zA-Z0-9\.\_\&\-\@\+\%\(\)\ \/]+", cell) is None
    )


def multiple_cell_per_row(rows, delim, quotechar=None):
    for row in rows:
        if len(split_row(row, delim, quotechar=quotechar)) == 1:
            return False
    return True


def even_rows(rows, delim, quotechar=None):
    cells_per_row = set()
    for row in rows:
        cells_per_row.add(len(split_row(row, delim, quotechar)))
    return len(cells_per_row) == 1


def more_than_one_row(rows):
    return len(rows) > 1


def split_file(data):
    data = strip_trailing_crnl(data)
    if "\r\n" in data:
        return data.split("\r\n")
    if "\n" in data:
        return data.split("\n")
    if "\r" in data:
        return data.split("\r")
    return data


def split_row(row, delim, quotechar):
    # no nested quotes
    if quotechar is None or not quotechar in row:
        return row.split(delim)

    cells = []
    current_cell = ""
    in_quotes = False
    for c in row:
        if c == delim and not in_quotes:
            cells.append(current_cell)
            current_cell = ""
        elif c == quotechar:
            in_quotes = not in_quotes
            current_cell += c
        else:
            current_cell += c
    if current_cell:
        cells.append(current_cell)
    return cells


def form_escape_wrapper(form_func):
    def wrapped(data, encoding, delim, quotechar):
        if maybe_has_escapechar(data, encoding, delim, quotechar):
            return (False, "maybe_escape")
        return form_func(data, encoding, delim, quotechar)

    return wrapped


@form_escape_wrapper
def is_form_1(data, encoding, delim, quotechar):
    # All cells quoted, no empty cells, no nested quotes, more than one column
    is_form_1.ID = 1

    rows = split_file(data)

    if not every_row_has_delim(rows, delim):
        return (False, "no_delim")
    if not multiple_cell_per_row(rows, delim, quotechar=quotechar):
        return (False, "single_cell")
    if not even_rows(rows, delim, quotechar=quotechar):
        return (False, "uneven_rows")
    if not more_than_one_row(rows):
        return (False, "single_row")

    for row in rows:
        cells = split_row(row, delim, quotechar)

        for cell in cells:
            # No empty cells
            if is_any_empty(cell):
                return (False, "empty_cell")

            # All cells must be quoted
            if not is_quoted_cell(cell, quotechar):
                return (False, "unquoted_cell")

            # No quotes inside quotes
            if has_nested_quotes(cell, quotechar):
                return (False, "nested_quotes")

    return (True, None)


@form_escape_wrapper
def is_form_2(data, encoding, delim, quotechar):
    # Nothing quoted, no empty
    is_form_2.ID = 2

    # Form 13 and this one shouldn't overlap
    if is_form_13(data, encoding, delim, quotechar)[0]:
        return (False, "form_13")

    # Form 18 and this shouldn't overlap
    if is_form_18(data, encoding, delim, quotechar)[0]:
        return (False, "form_18")

    # Form 17 and this shouldn't overlap
    if is_form_17(data, encoding, delim, quotechar)[0]:
        return (False, "form_17")

    rows = split_file(data)

    if not every_row_has_delim(rows, delim):
        return (False, "no_delim")
    if not multiple_cell_per_row(rows, delim, quotechar=None):
        return (False, "single_cell")
    if not even_rows(rows, delim, quotechar=None):
        return (False, "uneven_rows")
    if not more_than_one_row(rows):
        return (False, "single_row")

    for row in rows:
        cells = split_row(row, delim, None)

        for cell in cells:
            # No empty unquoted cells
            if is_empty_unquoted(cell):
                return (False, "empty_unquoted")

            # All cells must be unquoted
            if is_any_quoted_cell(cell):
                return (False, "quoted_cell")

            # All cells must not be partially quoted
            if is_any_partial_quoted_cell(cell):
                return (False, "partial_quoted_cell")

            # Cells have to be elementary
            if not is_elementary(cell):
                return (False, "non_elementary")

    return (True, None)


@form_escape_wrapper
def is_form_3(data, encoding, delim, quotechar):
    # all unquoted, at least one empty delimiter-filled row
    is_form_3.ID = 3

    rows = split_file(data)

    if not every_row_has_delim(rows, delim):
        return (False, "no_delim")
    if not multiple_cell_per_row(rows, delim, quotechar=None):
        return (False, "single_cell")
    if not even_rows(rows, delim):
        return (False, "uneven_rows")
    if not more_than_one_row(rows):
        return (False, "single_row")

    # we've already asserted that it is the same for the entire file
    cells_per_row = len(rows[0].split(delim))
    expected = delim * (cells_per_row - 1)

    empty_delimited_row_count = 0
    for row in rows:
        cells = split_row(row, delim, None)

        for cell in cells:
            # All cells must be unquoted
            if is_any_quoted_cell(cell):
                return (False, "quoted_cell")

            # All cells must be elementary
            if not is_elementary(cell):
                return (False, "non_elementary")

        if row == expected:
            empty_delimited_row_count += 1

    if empty_delimited_row_count == 0:
        return (False, "no_empty_rows")

    return (True, None)


@form_escape_wrapper
def is_form_4(data, encoding, delim, quotechar):
    # all unquoted, except the ones with the delimiter in the cell, no empty
    # cells. Must have at least one quoted with delimiter in cell.
    # No quoted rows
    is_form_4.ID = 4

    # Form 18 and this shouldn't overlap
    if is_form_18(data, encoding, delim, quotechar)[0]:
        return (False, "form_18")

    # Form 17 and this shouldn't overlap
    if is_form_17(data, encoding, delim, quotechar)[0]:
        return (False, "form_17")

    rows = split_file(data)

    if not every_row_has_delim(rows, delim):
        return (False, "no_delim")
    if not multiple_cell_per_row(rows, delim, quotechar=quotechar):
        return (False, "single_cell")
    if not even_rows(rows, delim, quotechar=quotechar):
        return (False, "uneven_rows")
    if not more_than_one_row(rows):
        return (False, "single_row")

    found_quoted_with_delim = False

    for row in rows:
        if is_quoted_cell(row, quotechar) and not quotechar in row[1:-1]:
            return (False, "quoted_row")

        cells = split_row(row, delim, quotechar)
        for cell in cells:
            # All cells must be unquoted unless they contain the delimiter
            if is_quoted_cell(cell, quotechar):
                if not has_delimiter(cell, delim):
                    return (False, "quoted_no_delim")
                else:
                    found_quoted_with_delim = True

            # No cells must be empty
            if is_any_empty(cell):
                return (False, "empty_cell")

            # All unquoted cells must be elementary
            if (not is_quoted_cell(cell, quotechar)) and not is_elementary(
                cell
            ):
                return (False, "non_elementary")

    if not found_quoted_with_delim:
        return (False, "no_quoted_w_delim")

    return (True, None)


@form_escape_wrapper
def is_form_5(data, encoding, delim, quotechar):
    # Anthony Bowden's files.
    is_form_5.ID = 5
    if data.startswith(";Originally developed by Anthony Bowden"):
        return (True, None)
    if '"' in data:
        return (False, "unexpected")
    if "'" in data:
        idxs = [i for i, c in enumerate(data) if c == "'"]
        if not len(idxs) == 2:
            return (False, "unexpected")
        if not data[idxs[0] : idxs[1] + 1] == "'Readme.txt'":
            return (False, "unexpected")
    return (False, "not_railsim")


@form_escape_wrapper
def is_form_6(data, encoding, delim, quotechar):
    # No quotes, no delim, single column
    is_form_6.ID = 6
    rows = split_file(data)

    if not more_than_one_row(rows):
        return (False, "single_row")

    for row in rows:
        cell = row[:]
        if is_any_quoted_cell(cell):
            return (False, "quoted_cell")

        search = regex.compile(r"[^A-Za-z0-9.\_&-]").search
        if search(cell):
            return (False, "non_elementary")

    return (True, None)


@form_escape_wrapper
def is_form_7(data, encoding, delim, quotechar):
    # all rows quoted, no nested quotes
    # basically form 2 but with quotes around each row
    is_form_7.ID = 7

    rows = split_file(data)

    if not every_row_has_delim(rows, delim):
        return (False, "no_delim")
    if not more_than_one_row(rows):
        return (False, "single_row")

    for row in rows:
        if not (row[0] == quotechar and row[-1] == quotechar):
            return (False, "not_quoted")

    newrows = []
    for row in rows:
        newrows.append(row[1:-1])

    return is_form_2("\n".join(newrows), encoding, delim, quotechar)


@form_escape_wrapper
def is_form_8(data, encoding, delim, quotechar):
    # some quoted, some not quoted, no empty, no nested quotes
    is_form_8.ID = 8

    # Form 4 and this one shouldn't overlap
    if is_form_4(data, encoding, delim, quotechar)[0]:
        return (False, "form_4")

    # Form 13 and this one shouldn't overlap
    if is_form_13(data, encoding, delim, quotechar)[0]:
        return (False, "form_13")

    # Form 18 and this shouldn't overlap
    if is_form_18(data, encoding, delim, quotechar)[0]:
        return (False, "form_18")

    # Form 17 and this shouldn't overlap
    if is_form_17(data, encoding, delim, quotechar)[0]:
        return (False, "form_17")

    rows = split_file(data)

    if not every_row_has_delim(rows, delim):
        return (False, "no_delim")
    if not multiple_cell_per_row(rows, delim, quotechar=quotechar):
        return (False, "single_cell")
    if not even_rows(rows, delim, quotechar=quotechar):
        return (False, "uneven_rows")
    if not more_than_one_row(rows):
        return (False, "single_row")

    quoted_cells = 0
    unquoted_cells = 0

    for row in rows:
        cells = split_row(row, delim, quotechar)
        for cell in cells:
            if is_any_empty(cell):
                return (False, "empty_cell")

            if is_quoted_cell(cell, quotechar):
                quoted_cells += 1
            elif not is_any_quoted_cell(cell):
                unquoted_cells += 1
                if not is_elementary(cell):
                    return (False, "non_elementary")

    if quoted_cells == 0 or unquoted_cells == 0:
        return (False, "not quoted/unquoted mix")

    return (True, None)


@form_escape_wrapper
def is_form_9(data, encoding, delim, quotechar):
    # Single column, each cell quoted
    # basically form_7 + form_6
    is_form_9.ID = 9

    rows = split_file(data)

    if not more_than_one_row(rows):
        return (False, "single_row")

    for row in rows:
        if not is_quoted_cell(row, quotechar):
            return (False, "not_quoted")

        search = regex.compile(r"[^A-Za-z0-9.\_&\- ]").search
        if search(row[1:-1]):
            return (False, "non_elementary")

    return (True, None)


@form_escape_wrapper
def is_form_10(data, encoding, delim, quotechar):
    # All cells quoted, quoted empty allowed, no nested quotes
    is_form_10.ID = 10

    rows = split_file(data)

    if not every_row_has_delim(rows, delim):
        return (False, "no_delim")
    if not multiple_cell_per_row(rows, delim, quotechar=quotechar):
        return (False, "single_cell")
    if not even_rows(rows, delim, quotechar=quotechar):
        return (False, "uneven_rows")
    if not more_than_one_row(rows):
        return (False, "single_row")

    quoted_empty_count = 0

    for row in rows:
        cells = split_row(row, delim, quotechar)
        for cell in cells:
            # Unquoted empty not allowed
            if is_empty_unquoted(cell):
                return (False, "empty_unquoted")

            if is_empty_quoted(cell, quotechar):
                quoted_empty_count += 1

            # All cells must be quoted
            if not is_quoted_cell(cell, quotechar):
                return (False, "unquoted_cell")

            # No quotes inside quotes
            if has_nested_quotes(cell, quotechar):
                return (False, "nested_quotes")

    if quoted_empty_count == 0:
        return (False, "no_empty")

    return (True, None)


@form_escape_wrapper
def is_form_11(data, encoding, delim, quotechar):
    # All unquoted, at most 1 empty per row, at least 1 empty per file
    is_form_11.ID = 11

    # Form 13 and this one shouldn't overlap
    if is_form_13(data, encoding, delim, quotechar)[0]:
        return (False, "form_13")

    # Form 17 and this shouldn't overlap
    if is_form_17(data, encoding, delim, quotechar)[0]:
        return (False, "form_17")

    rows = split_file(data)

    if not every_row_has_delim(rows, delim):
        return (False, "no_delim")
    if not multiple_cell_per_row(rows, delim, quotechar=None):
        return (False, "single_cell")
    if not even_rows(rows, delim):
        return (False, "uneven_rows")
    if not more_than_one_row(rows):
        return (False, "single_row")

    total_empty = 0
    for row in rows:
        cells = split_row(row, delim, None)
        num_empty = 0
        for cell in cells:
            if is_empty_unquoted(cell):
                num_empty += 1
                continue

            if is_any_quoted_cell(cell):
                return (False, "quoted_cell")

            if is_any_partial_quoted_cell(cell):
                return (False, "partial_quoted_cell")

            if not is_elementary(cell):
                return (False, "non_elementary")

        if num_empty > 1:
            return (False, "many_empty")
        total_empty += num_empty

    if total_empty == 0:
        return (False, "no_empty")

    return (True, None)


@form_escape_wrapper
def is_form_12(data, encoding, delim, quotechar):
    """
    This should match the following regex (once?/multiple times?)

        ',(male|female),([a-zA-Z0-9]+@[a-zA-Z0-9]+.com)'

    There are about 600 files of this sort in the Github working set, they are 
    not "elementary" which is why they're not picked up. Either create a form 
    for this or expand what we know to be elementary.

    """
    is_form_12.ID = 12

    if '"' in data or "'" in data:
        return (False, "has_quote")

    matches = regex.findall(
        ",(male|female),([a-zA-Z0-9]+@[a-zA-Z0-9]+.com)", data
    )
    if len(matches) > 0:
        return (True, None)
    return (False, "no_match")


@form_escape_wrapper
def is_form_13(data, encoding, delim, quotechar):
    """
    This matches the usagedata.csv file from Eclipse. This is often committed 
    to a git repository.
    """
    is_form_13.ID = 13
    if not data.startswith("what,kind,bundleId,bundleVersion,description,time"):
        return (False, "no_match")

    if quotechar == "":
        if '"' in data:
            return (False, "has_quote")
    elif quotechar == '"':
        if not '"' in data:
            return (False, "has_no_quote")

    return (True, None)


@form_escape_wrapper
def is_form_14(data, encoding, delim, quotechar):
    """
    This matches files that start with:

        Format is tab separated

    These files never have quotes (in the current training set)
    """
    is_form_14.ID = 14
    if data.startswith("Format is tab separated"):
        return (True, None)
    return (False, "no_match")


@form_escape_wrapper
def is_form_15(data, encoding, delim, quotechar):
    """
    Files that start with "Fornecedor;"
    These files never have quotes (in the current training set)
    """
    is_form_15.ID = 15
    if data.startswith("Fornecedor;"):
        return (True, None)
    return (False, "no_match")


@form_escape_wrapper
def is_form_17(data, encoding, delim, quotechar):
    """
    Matches certain government expense report files (about 600 in the working 
    set)
    """
    is_form_17.ID = 17
    m = regex.match(
        "^Department Family,Entity,Date,Expense Type,Expense Area,"
        "Supplier,Transaction Number,Amount,VAT Registration Number",
        data,
        regex.IGNORECASE,
    )
    if not m:
        return (False, "no_match")
    if "','" in data:
        return (False, "single_quote")
    if quotechar == '"':
        if not ('",' in data or ',"' in data):
            return (False, "no_qoute")
    elif quotechar == "":
        if '"' in data:
            return (False, "has_quote")
    else:
        return (False, "unexpected_quote")
    return (True, None)


@form_escape_wrapper
def is_form_18(data, encoding, delim, quotechar):
    """
    Certain government data file
    """
    is_form_18.ID = 18
    m = regex.match("^CPS outcomes by principal offence", data)
    if not m:
        return (False, "no_match")
    if "','" in data:
        return (False, "single_quote")
    if quotechar == '"':
        if not ('",' in data or ',"' in data):
            return (False, "no_quote")
    elif quotechar == "":
        if '"' in data:
            return (False, "has_quote")
    else:
        return (False, "unexpected_quote")
    return (True, None)


@form_escape_wrapper
def is_form_19(data, encoding, delim, quotechar):
    """
    Certain government data file
    """
    is_form_19.ID = 19
    m = regex.match("^RecordKey,SurveyKey,SurveyName", data)
    if not m:
        return (False, "no_match")
    if "','" in data:
        return (False, "single_quote")
    if quotechar == '"':
        if not ('",' in data or ',"' in data):
            return (False, "no_quote")
    elif quotechar == "":
        if '"' in data:
            return (False, "has_quote")
    else:
        return (False, "unexpected_quote")
    return (True, None)


def dict_product(dicts):
    # https://stackoverflow.com/a/40623158/1154005
    return (dict(zip(dicts, x)) for x in itertools.product(*dicts.values()))


def record_form(form_id, filename, config):
    form_file = "./form_%i.json" % form_id
    data = {k: v for k, v in config.items()}
    data["filename"] = filename
    with open(form_file, "a") as fid:
        fid.write(json.dumps(data) + "\n")


def detect_form(filename, record_result=True, verbose=True):
    option_dict_1 = {"delim": DELIMS, "quotechar": ['"', "'"]}
    option_dict_2 = {"delim": DELIMS, "quotechar": [""]}
    option_dict_4 = {"delim": [""], "quotechar": ['"', "'"]}

    forms = [
        (is_form_1, option_dict_1),
        (is_form_2, option_dict_2),
        (is_form_4, option_dict_1),
        (is_form_5, {"delim": [","], "quotechar": [""]}),
        (is_form_6, {"delim": [""], "quotechar": [""]}),
        (is_form_7, option_dict_1),
        (is_form_8, option_dict_1),
        (is_form_9, option_dict_4),
        (is_form_10, option_dict_1),
        (is_form_11, option_dict_2),
        (is_form_12, {"delim": [","], "quotechar": [""]}),
        (is_form_13, {"delim": [","], "quotechar": ['"', ""]}),
        (is_form_14, {"delim": ["\t"], "quotechar": [""]}),
        (is_form_15, {"delim": [";"], "quotechar": [""]}),
        (is_form_17, {"delim": [","], "quotechar": ["", '"']}),
        (is_form_18, {"delim": [","], "quotechar": ["", '"']}),
        (is_form_19, {"delim": [","], "quotechar": ["", '"']}),
    ]

    encoding = get_encoding(filename)
    data = load_file(filename, encoding=encoding)
    if data is None:
        return "FAIL", {}

    detected_forms = []
    for form_func, options in forms:
        for opt in dict_product(options):
            status, error = form_func(data, encoding, **opt)
            if status:
                # if the form passed, then it doesn't have a potential
                # escapechar
                opt["escapechar"] = ""

                if record_result:
                    record_form(form_func.ID, filename, opt)
                detected_forms.append((form_func.ID, opt))
            elif verbose:
                print(
                    "Not form %s with params %r because %s"
                    % (form_func.ID, opt, error)
                )

    if len(detected_forms) == 0:
        if record_result:
            record_form(0, filename, {})
        if verbose:
            print("%s\t%s" % ("NONE", filename))
        return None, {}
    elif len(detected_forms) == 1:
        if verbose:
            print("%s\t%s" % ("FORM_%02i" % detected_forms[0][0], filename))
        return detected_forms[0]
    else:
        raise ValueError(
            "Can't have multiple forms for a single file: %s (%r)"
            % (filename, detected_forms)
        )


if __name__ == "__main__":
    if not len(sys.argv) == 2:
        print("Usage: %s filename" % sys.argv[0])
        raise SystemExit(1)

    filename = sys.argv[1]
    form_id, params = detect_form(filename, record_result=False, verbose=True)
    print(form_id, params)
