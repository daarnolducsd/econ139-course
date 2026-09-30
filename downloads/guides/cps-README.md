# CPS: August 2025 Current Population Survey

This folder contains the lecture dataset and three equivalent teaching examples
for exploring labor-force status, occupations, and weekly earnings.

## Files

- `data/cps_aug_25.csv`: use with Python, R, or most other programs.
- `data/cps_aug_25.dta`: use with Stata.
- `code/analyze.py`, `code/analyze.R`, `code/analyze.do`: analysis examples.

Keep this layout after unzipping. Individual downloads can be placed in the same
`data/` and `code/` folders. Do not replace these lecture inputs with the similarly
named Problem Set 1 CSV; it is a different assignment dataset.

## Python

Requires Python 3, pandas, and matplotlib. From this folder:

```sh
python3 code/analyze.py
```

The script also works from another directory when you give its full path. It
prints frequency tables and saves `outputs/weekly_earnings.png`, then displays
its histogram when a graphical plotting backend is available.

## R

Requires R and tidyverse. From this folder:

```sh
Rscript code/analyze.R
```

Rscript locates data beside the script. In RStudio, set the working directory to
this folder and source `code/analyze.R`. The script prints tables and saves
`outputs/weekly_earnings.png`.

## Stata

In Stata, change the working directory to this folder, then run:

```stata
do code/analyze.do
```

It reads `data/cps_aug_25.dta`, displays tables and a histogram, and saves
`outputs/weekly_earnings.png`. An optional first argument specifies the topic
folder when running from elsewhere: `do "path/to/cps/code/analyze.do" "path/to/cps"`.

Keep generated figures and other results in `outputs/`; leave the data inputs unchanged.
