[![tests](https://github.com/Studentzipit/Project-3/actions/workflows/tests.yml/badge.svg)](https://github.com/Studentzipit/Project-3/actions/workflows/tests.yml)

# PubChem API Lookup Package

**Author:** Zachary Thompson  
**Version:** 0.2.0  
**Repository:** https://github.com/Studentzipit/Project-3


## Overview

A command-line tool that reads chemical names and CAS numbers from an Excel
file, queries the PubChem database for compound metadata and GHS hazard
information, and writes structured results to an output Excel file.


## Requirements

- Python 3.9 or higher
- The following Python packages (installed automatically via pip):
  - pubchempy
  - pandas
  - requests
  - openpyxl


## Setup

1. Clone the repository:
   ```
   git clone https://github.com/Studentzipit/Project-3.git
   cd Project-3
   ```

2. Create and activate a virtual environment (recommended):
   ```
   python -m venv .venv
   ```
   Windows: `.venv\Scripts\activate`  
   Mac/Linux: `source .venv/bin/activate`

3. Install the package and its dependencies:
   ```
   pip install -e .
   ```

4. Confirm the CLI is available:
   ```
   pubchem-lookup --help
   ```


## Input File Format

The input must be an Excel file (`.xlsx`) with the following two columns:

| Column | Description |
|--------|-------------|
| `Name` | Chemical trade name or common name (required) |
| `CAS#` | CAS registry number (may be left blank) |

Example input (`PubChem_input1.xlsx`):

| Name | CAS# |
|------|------|
| TERGITOL NP-9 | 68412-54-4 |
| ACRYLAMIDE, 99+% | 79-06-1 |
| ALUMINUM OXIDE C | 1344-28-1 |
| BUTYL CELLOSOLVE | 111-76-2 |
| DESMODUR H | 822-06-0 |
| EPON RESIN 825 | 25068-38-6 |
| ETHOXYLATED HYDROXYETHYL METHACRYLATE | |


## Usage

```
pubchem-lookup <input.xlsx> <output.xlsx>
```

Examples:
```
pubchem-lookup PubChem_input1.xlsx PubChem_output1.xlsx
pubchem-lookup PubChem_input2.xlsx PubChem_output2.xlsx
```


## Output File Format

| Column | Description |
|--------|-------------|
| Labeled Names | Chemical name from input file |
| Labeled CAS | CAS number from input file |
| CID from Name | PubChem CID resolved by chemical name |
| CID from CAS # | PubChem CID resolved by CAS number |
| PubChem Name | Official compound name from PubChem |
| PubChem CAS # | Primary CAS number registered in PubChem |
| Other CAS #s | Alternate CAS numbers (newline-separated) |
| Related CAS #s | Related CAS entries, e.g. salts or parent compounds |
| Top 5 Chem Names | Up to 5 depositor-supplied synonyms |
| GHS Pictogram Names | GHS hazard pictogram labels (e.g. Flammable, Corrosive) |
| GHS Hazard Statements | Full H-statement codes and text (e.g. H315, H330) |

Sample output row (ACRYLAMIDE, 99+%):

```
Labeled Names        : ACRYLAMIDE, 99+%
Labeled CAS          : 79-06-1
CID from Name        : 0
CID from CAS #       : 6579
PubChem Name         : Acrylamide
PubChem CAS #        : 79-06-1
Other CAS #s         : 9082-06-8
Related CAS #s       : None
Top 5 Chem Names     : ACRYLAMIDE / 79-06-1 / 2-Propenamide / prop-2-enamide / Propenamide
GHS Pictogram Names  : Acute Toxic / Health Hazard / Irritant
GHS Hazard Statements: H315: Causes skin irritation
                       H319: Causes serious eye irritation
                       H340: May cause genetic defects
                       H350: May cause cancer
                       H361: Suspected of damaging fertility
                       H372: Causes damage to organs (repeated exposure)
```


## Testing

Install dev dependencies and run the test suite:

```
pip install -e ".[dev]"
pytest tests/
```


## Not Found Cases

If a compound cannot be matched in PubChem, the output row will show:

- `PubChem Name`: Not Found
- All metadata fields: nan

Common reasons:
- Trade name or product brand not indexed in PubChem
- CAS number corresponds to a mixture (not a pure compound)
- No CAS number provided in the input file


## Project Files

```
PubChem_API.ipynb       — Interactive Jupyter notebook version
PubChem_input1.xlsx     — Test input file 1 (7 chemicals)
PubChem_input2.xlsx     — Test input file 2 (9 chemicals)
PubChem_output1.xlsx    — Results for input 1
PubChem_output2.xlsx    — Results for input 2
pyproject.toml          — Package build configuration
pubchem_lookup/
    __init__.py         — Public API exports
    lookup.py           — CID resolution by name and CAS number
    fetch.py            — PubChem REST API calls and data parsing
    cli.py              — Command-line entry point
tests/
    test_lookup.py      — 11 tests: CID resolution, blank/NaN CAS, edge cases
    test_fetch.py       — 15 tests: API parsing, GHS filtering, error handling
    test_cli.py         — 11 tests: CLI input validation, output structure
```
