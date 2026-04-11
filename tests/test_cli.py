"""Tests for pubchem_lookup.cli — command-line entry point."""

import pytest
import pandas as pd
import openpyxl
from pathlib import Path
from unittest.mock import patch
from pubchem_lookup.cli import main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EXPECTED_OUTPUT_COLUMNS = [
    "Labeled Names",
    "Labeled CAS",
    "CID from Name",
    "CID from CAS #",
    "PubChem Name",
    "PubChem CAS #",
    "Other CAS #s",
    "Related CAS #s",
    "Top 5 Chem Names",
    "GHS Pictogram Names",
    "GHS Hazard Statements",
]

MOCK_PC_DATA = (
    "Test Compound", "123-45-6", "None", "None",
    "Synonym A\nSynonym B", "Irritant", "H315: Causes skin irritation"
)


def make_input_xlsx(tmp_path, rows, columns=("Name", "CAS#")):
    """Write a minimal input Excel file and return its path."""
    path = tmp_path / "input.xlsx"
    df = pd.DataFrame(rows, columns=columns)
    df.to_excel(path, index=False)
    return path


# ---------------------------------------------------------------------------
# Missing input file
# ---------------------------------------------------------------------------

def test_missing_input_file_exits(tmp_path):
    output = tmp_path / "output.xlsx"
    with pytest.raises(SystemExit) as exc:
        with patch("sys.argv", ["pubchem-lookup", "nonexistent.xlsx", str(output)]):
            main()
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# Missing required columns
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("columns, rows", [
    (("Chemical", "CAS#"), [("Acrylamide", "79-06-1")]),  # wrong name column
    (("Name", "Registry"),  [("Acrylamide", "79-06-1")]),  # wrong CAS column
    (("Chemical", "Registry"), [("Acrylamide", "79-06-1")]),  # both wrong
])
def test_missing_required_columns_exits(tmp_path, columns, rows):
    input_file = make_input_xlsx(tmp_path, rows, columns=columns)
    output = tmp_path / "output.xlsx"
    with pytest.raises(SystemExit) as exc:
        with patch("sys.argv", ["pubchem-lookup", str(input_file), str(output)]):
            main()
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# Correct output table structure
# ---------------------------------------------------------------------------

def test_output_has_correct_columns(tmp_path):
    input_file = make_input_xlsx(tmp_path, [("Acrylamide", "79-06-1")])
    output = tmp_path / "output.xlsx"

    with patch("sys.argv", ["pubchem-lookup", str(input_file), str(output)]), \
         patch("pubchem_lookup.cli.resolve_cids", return_value=([6579], [6579])), \
         patch("pubchem_lookup.cli.get_pc_data", return_value=MOCK_PC_DATA):
        main()

    df = pd.read_excel(output)
    assert list(df.columns) == EXPECTED_OUTPUT_COLUMNS


def test_output_row_count_matches_input(tmp_path):
    rows = [("Acrylamide", "79-06-1"), ("Mercury", "7439-97-6"), ("Fake Chem", "nan")]
    input_file = make_input_xlsx(tmp_path, rows)
    output = tmp_path / "output.xlsx"

    with patch("sys.argv", ["pubchem-lookup", str(input_file), str(output)]), \
         patch("pubchem_lookup.cli.resolve_cids", return_value=([6579, 23931, 0], [6579, 23931, 0])), \
         patch("pubchem_lookup.cli.get_pc_data", return_value=MOCK_PC_DATA):
        main()

    df = pd.read_excel(output)
    assert len(df) == 3


# ---------------------------------------------------------------------------
# Unmatched compounds (CID = 0) produce "Not Found" rows
# ---------------------------------------------------------------------------

def test_unmatched_compound_produces_not_found(tmp_path):
    input_file = make_input_xlsx(tmp_path, [("EPON RESIN 825", "25068-38-6")])
    output = tmp_path / "output.xlsx"

    with patch("sys.argv", ["pubchem-lookup", str(input_file), str(output)]), \
         patch("pubchem_lookup.cli.resolve_cids", return_value=([0], [0])):
        main()

    df = pd.read_excel(output)
    assert df.loc[0, "PubChem Name"] == "Not Found"


# ---------------------------------------------------------------------------
# Failed API request is caught and logged, does not crash
# ---------------------------------------------------------------------------

def test_api_failure_does_not_crash(tmp_path):
    input_file = make_input_xlsx(tmp_path, [("Acrylamide", "79-06-1")])
    output = tmp_path / "output.xlsx"

    with patch("sys.argv", ["pubchem-lookup", str(input_file), str(output)]), \
         patch("pubchem_lookup.cli.resolve_cids", return_value=([6579], [6579])), \
         patch("pubchem_lookup.cli.get_pc_data", side_effect=Exception("API timeout")):
        main()  # should not raise

    df = pd.read_excel(output)
    assert df.loc[0, "PubChem Name"] == "Error"


# ---------------------------------------------------------------------------
# Blank CAS in input still produces a valid row
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cas_value", ["", None])
def test_blank_cas_produces_valid_row(tmp_path, cas_value):
    input_file = make_input_xlsx(tmp_path, [("Unknown Chem", cas_value)])
    output = tmp_path / "output.xlsx"

    with patch("sys.argv", ["pubchem-lookup", str(input_file), str(output)]), \
         patch("pubchem_lookup.cli.resolve_cids", return_value=([0], [0])):
        main()

    df = pd.read_excel(output)
    assert len(df) == 1
    assert list(df.columns) == EXPECTED_OUTPUT_COLUMNS
