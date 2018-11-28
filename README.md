# CSV Wrangling

This is the repository for reproducing the experiments in the paper:

[**Wrangling Messy CSV files by Detecting Row and Type Patterns**](TODO)

by [G.J.J. van den Burg](https://gertjanvandenburg.com), [A. Nazabal](TODO) 
and [C. Sutton](TODO).

## Introduction

Our experiments are made reproducible through the use of [GNU Make](TODO). See 
below for the full requirements.

There are two ways to reproduce our results:

1. You can reproduce the figures, tables, and constants from the raw 
   experimental results included in this repository. This will not re-run the 
   experiments but will regenerate the output used in the paper. The command 
   for this is:

       make output

2. You can fully reproduce our experiments by downloading the data and 
   rerunning the detection methods on all the files. This might take a while 
   depending on the speed of your machine and the number of cores available. 
   Total wall-clock computation time for a single core is estimated at 11 
   days. The following command will do all of this.

       make full

   If you'd like to use multiple cores, you can use:

       make -j X full

   where X is the desired number of cores.


## Data

There are two datasets that are used in the experiments. Because we don't own 
the rights to all these files, we can't package these files and make them 
available in a single download. We can however provide URLs to the files and 
add a download script, which is what we do here. The data can be downloaded 
with:

    make data

If you wish to change the download location of the data, please edit the 
``DATA_DIR`` variable in the Makefile.


## Requirements

- Python 3.x with the packages in the ``requirements.txt`` file. These can be 
  installed with: ``pip install --user -r requirements.txt``.

- R with the external packages installable through: 
  ``install.packages(c('devtools', 'rjson', 'data.tree', 'RecordLinkage', 
  'readr', 'tibble'))``.

- A working [LaTeX](TODO) installation is needed for creating the figures, as 
  well as a working [LaTeXMK](TODO) installation.
