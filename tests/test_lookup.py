"""Tests for pubchem_lookup.lookup — CID resolution logic."""

import pytest
from unittest.mock import patch
from pubchem_lookup.lookup import resolve_cids


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_get_cids(mapping):
    """Return a mock for pcp.get_cids that uses a dict to simulate responses.

    mapping: {search_term: [cid, ...]}  — missing keys return [].
    """
    def _get_cids(query, namespace):
        return mapping.get(str(query), [])
    return _get_cids


# ---------------------------------------------------------------------------
# Parametrized: name-based CID resolution
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, expected_cid", [
    ("Acrylamide",   6579),   # known compound
    ("MERCURY",      23931),  # known compound
    ("FAKECHEM_XYZ", 0),      # no match → 0
])
def test_resolve_cids_by_name(name, expected_cid):
    mapping = {"Acrylamide": [6579], "MERCURY": [23931]}
    with patch("pubchem_lookup.lookup.pcp.get_cids", side_effect=make_mock_get_cids(mapping)):
        cid_from_name, _ = resolve_cids([name], ["nan"])
    assert cid_from_name[0] == expected_cid


# ---------------------------------------------------------------------------
# Parametrized: CAS-based CID resolution
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cas, expected_cid", [
    ("79-06-1",   6579),   # direct CAS match
    ("111-76-2",  8133),   # direct CAS match
    ("000-00-0",  9999),   # only matches with CAS- prefix fallback
    ("999-99-9",  0),      # no match at all → 0
])
def test_resolve_cids_by_cas(cas, expected_cid):
    mapping = {
        "79-06-1":      [6579],
        "111-76-2":     [8133],
        "CAS-000-00-0": [9999],   # only found via prefix fallback
    }
    with patch("pubchem_lookup.lookup.pcp.get_cids", side_effect=make_mock_get_cids(mapping)):
        _, cid_from_cas = resolve_cids(["dummy"], [cas])
    assert cid_from_cas[0] == expected_cid


# ---------------------------------------------------------------------------
# Edge case: blank / NaN CAS values
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cas_value", [float("nan"), "nan", None])
def test_blank_cas_returns_zero(cas_value):
    """Blank or NaN CAS should produce CID 0 without querying PubChem for CAS."""
    call_args = []
    def tracking_get_cids(query, namespace):
        call_args.append((query, namespace))
        return []

    with patch("pubchem_lookup.lookup.pcp.get_cids", side_effect=tracking_get_cids):
        _, cid_from_cas = resolve_cids(["anything"], [cas_value])

    assert cid_from_cas[0] == 0
    # CAS value must never have been passed as a query
    cas_queries = [q for q, _ in call_args if q == str(cas_value)]
    assert cas_queries == []


# ---------------------------------------------------------------------------
# Edge case: multiple chemicals processed correctly
# ---------------------------------------------------------------------------

def test_resolve_cids_multiple_chemicals():
    mapping = {"79-06-1": [6579], "111-76-2": [8133]}
    names = ["Acrylamide", "2-Butoxyethanol"]
    cas_list = ["79-06-1", "111-76-2"]
    with patch("pubchem_lookup.lookup.pcp.get_cids", side_effect=make_mock_get_cids(mapping)):
        cid_from_name, cid_from_cas = resolve_cids(names, cas_list)
    assert len(cid_from_name) == 2
    assert len(cid_from_cas) == 2
    assert cid_from_cas == [6579, 8133]


# ---------------------------------------------------------------------------
# Edge case: all unmatched compounds
# ---------------------------------------------------------------------------

def test_all_unmatched_returns_zeros():
    with patch("pubchem_lookup.lookup.pcp.get_cids", return_value=[]):
        cid_from_name, cid_from_cas = resolve_cids(
            ["FAKECHEM1", "FAKECHEM2"],
            ["000-00-0", "111-11-1"]
        )
    assert cid_from_name == [0, 0]
    assert cid_from_cas == [0, 0]
