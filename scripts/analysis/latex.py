#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Code for compiling latex from Python.

Based on: https://github.com/GjjvdBurg/labella.py

Author: Gertjan van den Burg
Copyright (c) 2018 - The Alan Turing Institute
License: See the LICENSE file.

"""

import os
import shutil
import subprocess
import tabulate
import tempfile


def compile_latex(fname, tmpdirname, silent=True):
    compiler = "latexmk"
    compiler_args = [
        "--pdf",
        "--outdir=" + tmpdirname,
        "--interaction=nonstopmode",
        fname,
    ]
    command = [compiler] + compiler_args
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
    except (OSError, IOError) as e:
        raise (e)
    except subprocess.CalledProcessError as e:
        print(e.output.decode())
        raise (e)
    else:
        if not silent:
            print(output.decode())


def build_latex_doc(tex, output_name=None, silent=True):
    with tempfile.TemporaryDirectory() as tmpdirname:
        basename = "labella_text"
        fname = os.path.join(tmpdirname, basename + ".tex")
        with open(fname, "w") as fid:
            fid.write(tex)

        compile_latex(fname, tmpdirname, silent=silent)

        pdfname = os.path.join(tmpdirname, basename + ".pdf")
        if output_name:
            shutil.copy2(pdfname, output_name)


def build_latex_table(table, headers, floatfmt="g", missingval=""):
    list_of_lists, headers = table, headers
    cols = list(zip(*list_of_lists))
    coltypes = list(map(tabulate._column_type, cols))
    cols = [
        [tabulate._format(v, ct, floatfmt, missingval) for v in c]
        for c, ct in zip(cols, coltypes)
    ]
    n_cols = len(cols)

    data_rows = table
    text_rows = list(zip(*cols))

    text = []
    text.append("\\begin{tabular}{l%s}" % ("r" * n_cols))
    #text.append("\\hline")
    text.append(" & ".join(headers) + "\\\\")
    text.append("\\hline")
    for data_row, text_row in zip(data_rows, text_rows):
        text_row = list(text_row)
        max_val = max([x for x in data_row if isinstance(x, float)])
        max_idx = [i for i, v in enumerate(data_row) if v == max_val]
        for idx in max_idx:
            text_row[idx] = "\\textbf{" + text_row[idx] + "}"
        text.append(" & ".join(text_row) + "\\\\")
    text.append("\\hline")
    text.append("\\end{tabular}")

    return "\n".join(text)
