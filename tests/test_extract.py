from __future__ import annotations

from pathlib import Path

from trinetra.genai.extract import (
    DEMO_SOURCE,
    FormExtractor,
    is_demo_request,
    parse_fields,
)

SAMPLE_TEXT = """
CREDIT APPRAISAL SUMMARY
Borrower name: Northwind Metals Pvt Ltd
Sector: Steel Fabrication
Sanctioned exposure: Rs 9.2 Cr
Bureau score: 641
Loan-to-value: 0.82
Limit utilisation: 0.71
Overdue accounts: 2
Delinquencies (6m): 1
Bureau enquiries: 3
Promoter age: 51
Credit history: 132 months
"""


def test_parse_fields_reads_labelled_values() -> None:
    parsed = parse_fields(SAMPLE_TEXT)
    assert parsed["name"] == "Northwind Metals Pvt Ltd"
    assert parsed["sector"] == "Steel Fabrication"
    assert parsed["exposureCr"] == 9.2
    assert parsed["PERFORM_CNS.SCORE"] == 641
    assert parsed["ltv"] == 0.82
    assert parsed["primary_utilization"] == 0.71
    assert parsed["PRI.OVERDUE.ACCTS"] == 2
    assert parsed["DELINQUENT.ACCTS.IN.LAST.SIX.MONTHS"] == 1
    assert parsed["NO.OF_INQUIRIES"] == 3
    assert parsed["age_years"] == 51
    assert parsed["credit_history_months"] == 132


def test_parse_fields_returns_only_found_keys() -> None:
    parsed = parse_fields("Bureau score: 700\nnothing else labelled here")
    assert parsed == {"PERFORM_CNS.SCORE": 700}


def test_parse_fields_empty_text() -> None:
    assert parse_fields("") == {}
    assert parse_fields("   \n  ") == {}


def test_parse_fields_drops_out_of_range_values() -> None:
    parsed = parse_fields("Bureau score: 1200\nLoan-to-value: 5.0")
    assert "PERFORM_CNS.SCORE" not in parsed
    assert "ltv" not in parsed


def test_parse_fields_ignores_non_numeric() -> None:
    assert parse_fields("Bureau score: high") == {}


def test_is_demo_request_matches_filename_and_flag() -> None:
    assert is_demo_request("acme_appraisal.pdf", False) is True
    assert is_demo_request("sample-borrower.png", False) is True
    assert is_demo_request("statement.pdf", True) is True
    assert is_demo_request("statement.pdf", False) is False
    assert is_demo_request(None, False) is False


def test_extractor_returns_demo_fixture_for_sample(tmp_path: Path) -> None:
    document = tmp_path / "unused.pdf"
    document.write_bytes(b"not read for demo path")
    result = FormExtractor().extract(document, filename="sample-acme.pdf", demo=False)
    assert result.source == DEMO_SOURCE
    assert result.service_available is False
    assert result.fields["name"] == "Acme Textiles Pvt Ltd"
    assert result.fields["PERFORM_CNS.SCORE"] == 612


def test_extractor_degrades_when_ocr_unconfigured(tmp_path: Path) -> None:
    document = tmp_path / "statement.pdf"
    document.write_bytes(b"content")

    class _Offline:
        available = False

    result = FormExtractor(ocr=_Offline()).extract(document, filename="statement.pdf")
    assert result.fields == {}
    assert result.service_available is False
    assert "offline" in result.message.lower()


def test_extractor_parses_live_ocr_text(tmp_path: Path) -> None:
    document = tmp_path / "statement.pdf"
    document.write_bytes(b"content")

    class _Live:
        available = True

        def extract(self, _: Path) -> str:
            return SAMPLE_TEXT

    result = FormExtractor(ocr=_Live()).extract(document, filename="statement.pdf")
    assert result.source == "ocr"
    assert result.service_available is True
    assert result.fields["name"] == "Northwind Metals Pvt Ltd"
    assert "review" in result.message.lower()


def test_extractor_handles_ocr_failure(tmp_path: Path) -> None:
    document = tmp_path / "statement.pdf"
    document.write_bytes(b"content")

    class _Broken:
        available = True

        def extract(self, _: Path) -> str:
            raise RuntimeError("gpu instance stopped")

    result = FormExtractor(ocr=_Broken()).extract(document, filename="statement.pdf")
    assert result.fields == {}
    assert result.service_available is False


def test_extractor_reports_no_fields_when_text_unlabelled(tmp_path: Path) -> None:
    document = tmp_path / "statement.pdf"
    document.write_bytes(b"content")

    class _Blank:
        available = True

        def extract(self, _: Path) -> str:
            return "a page with no recognised labels at all"

    result = FormExtractor(ocr=_Blank()).extract(document, filename="statement.pdf")
    assert result.fields == {}
    assert result.service_available is True
    assert "no form fields" in result.message.lower()
