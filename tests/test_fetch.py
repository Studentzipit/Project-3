"""Tests for pubchem_lookup.fetch — PubChem API calls and data parsing."""

import pytest
import requests
from unittest.mock import patch, MagicMock
from pubchem_lookup.fetch import get_pc_data, _join


# ---------------------------------------------------------------------------
# Minimal valid PubChem JSON structure for mocking
# ---------------------------------------------------------------------------

def make_api_response(
    title="Test Compound",
    cas="123-45-6",
    other_cas=None,
    rel_cas=None,
    synonyms=None,
    pictograms=None,
    hazards=None,
):
    """Build a minimal PubChem PUG View JSON payload."""
    cas_information = [
        {"Value": {"StringWithMarkup": [{"String": cas}]}}
    ]
    if other_cas:
        for c in other_cas:
            cas_information.append({
                "Name": "Other CAS",
                "Value": {"StringWithMarkup": [{"String": c}]}
            })
    if rel_cas:
        for c in rel_cas:
            cas_information.append({
                "Name": "Related CAS",
                "Value": {"StringWithMarkup": [{"String": c}]}
            })

    syn_markup = [{"String": s} for s in (synonyms or [])]

    ghs_info = []
    if pictograms:
        ghs_info.append({
            "Name": "Pictogram(s)",
            "Value": {"StringWithMarkup": [{"Markup": [{"Extra": p} for p in pictograms]}]}
        })
    if hazards:
        ghs_info.append({
            "Name": "GHS Hazard Statements",
            "Value": {"StringWithMarkup": [{"String": h} for h in hazards]}
        })

    return {
        "Record": {
            "RecordTitle": title,
            "Section": [
                {
                    "TOCHeading": "Names and Identifiers",
                    "Section": [
                        {
                            "TOCHeading": "Other Identifiers",
                            "Section": [
                                {
                                    "TOCHeading": "CAS",
                                    "Information": cas_information
                                }
                            ]
                        },
                        {
                            "TOCHeading": "Synonyms",
                            "Section": [
                                {
                                    "TOCHeading": "Depositor-Supplied Synonyms",
                                    "Information": [
                                        {"Value": {"StringWithMarkup": syn_markup}}
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    "TOCHeading": "Safety and Hazards",
                    "Section": [
                        {
                            "TOCHeading": "Hazards Identification",
                            "Section": [
                                {
                                    "TOCHeading": "GHS Classification",
                                    "Information": ghs_info
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }


def mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    if status_code >= 400:
        mock.raise_for_status.side_effect = requests.HTTPError(response=mock)
    else:
        mock.raise_for_status.return_value = None
    return mock


# ---------------------------------------------------------------------------
# Correct return structure
# ---------------------------------------------------------------------------

def test_get_pc_data_returns_seven_values():
    data = make_api_response(title="Acrylamide", cas="79-06-1")
    with patch("pubchem_lookup.fetch.requests.get", return_value=mock_response(data)):
        result = get_pc_data(6579)
    assert len(result) == 7


def test_get_pc_data_correct_name_and_cas():
    data = make_api_response(title="Acrylamide", cas="79-06-1")
    with patch("pubchem_lookup.fetch.requests.get", return_value=mock_response(data)):
        pc_name, pc_cas, *_ = get_pc_data(6579)
    assert pc_name == "Acrylamide"
    assert pc_cas == "79-06-1"


# ---------------------------------------------------------------------------
# Parametrized: GHS hazard statement filtering
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw_hazards, expected_count", [
    (["H315: Causes skin irritation", "H319: Causes eye irritation"], 2),
    (["H315: Causes skin irritation", "", "not-an-H-code"], 1),  # empty and non-H filtered out
    ([], 0),  # no hazards → 'None'
])
def test_ghs_hazard_filtering(raw_hazards, expected_count):
    data = make_api_response(hazards=raw_hazards)
    with patch("pubchem_lookup.fetch.requests.get", return_value=mock_response(data)):
        *_, ghs_haz = get_pc_data(1)
    if expected_count == 0:
        assert ghs_haz == "None"
    else:
        assert len(ghs_haz.split("\n")) == expected_count


# ---------------------------------------------------------------------------
# Parametrized: synonym deduplication and cap
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("synonyms, expected_count", [
    (["Alpha", "ALPHA", "alpha", "Beta", "Gamma", "Delta", "Epsilon"], 5),  # cap at 5, dedup case
    (["OnlyOne"], 1),
    ([], 0),
])
def test_synonym_deduplication_and_cap(synonyms, expected_count):
    data = make_api_response(synonyms=synonyms)
    with patch("pubchem_lookup.fetch.requests.get", return_value=mock_response(data)):
        *_, syns, _, _ = get_pc_data(1)
    if expected_count == 0:
        assert syns == "None"
    else:
        assert len(syns.split("\n")) == expected_count


# ---------------------------------------------------------------------------
# Edge case: failed API request raises HTTPError
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status_code", [404, 500, 503])
def test_api_error_raises_exception(status_code):
    with patch("pubchem_lookup.fetch.requests.get",
               return_value=mock_response({}, status_code=status_code)):
        with pytest.raises(requests.HTTPError):
            get_pc_data(99999)


# ---------------------------------------------------------------------------
# Edge case: other_cas and related_cas populated correctly
# ---------------------------------------------------------------------------

def test_other_cas_and_related_cas():
    data = make_api_response(
        cas="79-06-1",
        other_cas=["9082-06-8"],
        rel_cas=["9003-05-8"]
    )
    with patch("pubchem_lookup.fetch.requests.get", return_value=mock_response(data)):
        _, _, other_cas, rel_cas, *_ = get_pc_data(6579)
    assert "9082-06-8" in other_cas
    assert "9003-05-8" in rel_cas


# ---------------------------------------------------------------------------
# Unit tests: _join helper
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lst, expected", [
    ([],              "None"),
    (["only"],        "only"),
    (["a", "b", "c"], "a\nb\nc"),
])
def test_join_helper(lst, expected):
    assert _join(lst) == expected
