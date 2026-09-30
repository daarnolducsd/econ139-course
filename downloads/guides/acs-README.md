# ACS: Healthcare, Medicare, and Labor Supply

This folder contains the prepared ACS healthcare dataset and teaching examples
that summarize insurance coverage and labor-force participation by age.

## Files

- `data/acs_clean_healthcare.csv`: use with Python or R.
- `data/acs_clean_healthcare.dta`: use with Stata.
- `data/acs_clean_healthcare.xlsx`: Excel version from the preparation workflow;
  that workflow caps Excel at the first 99,999 observations. Use CSV or DTA for
  the complete teaching sample.
- `code/acs_healthcare.py`, `.R`, `.do`: the analysis examples.

Keep the `data/` and `code/` folders when unzipping. Individual downloads should
be placed in the same layout. Analysis scripts do not overwrite the inputs.

## Python

Requires Python 3, pandas, and plotly. From this folder:

```sh
python3 code/acs_healthcare.py
```

The script locates data relative to itself and works from other directories too.
It saves three interactive HTML figures in `outputs/`: `has_insurance.html`,
`has_medicare.html`, and `in_labor_force.html`. Open those files in a browser.

## R

Requires R and tidyverse. From this folder:

```sh
Rscript code/acs_healthcare.R
```

Rscript locates data beside the script. In RStudio, set the working directory to
this folder and source `code/acs_healthcare.R`. It saves three PNG figures in
`outputs/`: `has_insurance.png`, `has_medicare.png`, and `in_labor_force.png`.

## Stata

Change Stata's working directory to this folder, then run:

```stata
do code/acs_healthcare.do
```

The script saves the same three PNG figures in `outputs/`. An optional first
argument specifies the topic folder when running from elsewhere:
`do "path/to/acs/code/acs_healthcare.do" "path/to/acs"`.

Keep generated figures and other results in `outputs/`; leave the data inputs unchanged.
