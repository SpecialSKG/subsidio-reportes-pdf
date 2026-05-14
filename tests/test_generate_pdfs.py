import pytest
import pandas as pd
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generate_pdfs import (
    safe_text,
    sanitize_filename,
    build_table_rows,
    make_pdf_for_record,
    read_and_concat_csvs,
    _split_df,
    DUI_COL,
)


class TestSafeText:
    def test_none(self):
        assert safe_text(None) == ""

    def test_nan_float(self):
        assert safe_text(float("nan")) == ""

    def test_nan_string(self):
        assert safe_text("nan") == ""
        assert safe_text("NAN") == ""
        assert safe_text("NaN") == ""

    def test_normal_string(self):
        assert safe_text("hello") == "hello"

    def test_number(self):
        assert safe_text(42) == "42"

    def test_empty_string(self):
        assert safe_text("") == ""


class TestSanitizeFilename:
    def test_normal(self):
        assert sanitize_filename("hello.pdf") == "hello.pdf"

    def test_windows_chars(self):
        assert sanitize_filename("a:b*c") == "a_b_c"

    def test_empty_fallback(self):
        assert sanitize_filename("") == "sin_nombre"

    def test_none(self):
        assert sanitize_filename(None) == "sin_nombre"

    def test_strip_whitespace(self):
        assert sanitize_filename("  name  ").startswith("name")


class TestBuildTableRows:
    def test_basic(self):
        row = pd.Series({"Name": "John", "Age": "30", "Skip": ""})
        result = build_table_rows(row, include_empty=False, exclude_cols={"Skip"})
        assert len(result) == 2

    def test_include_empty(self):
        row = pd.Series({"Name": "John", "Skip": ""})
        result = build_table_rows(row, include_empty=True, exclude_cols=set())
        assert len(result) == 2

    def test_exclude_col(self):
        row = pd.Series({"Name": "John", "Record Link ID": "123"})
        result = build_table_rows(row, include_empty=False, exclude_cols={"Record Link ID"})
        assert len(result) == 1

    def test_accepts_dict(self):
        row = {"Name": "John", "Age": "30"}
        result = build_table_rows(row, include_empty=False, exclude_cols=set())
        assert len(result) == 2

    def test_newline_in_value(self):
        row = pd.Series({"Notes": "line1\nline2"})
        result = build_table_rows(row, include_empty=True, exclude_cols=set())
        assert "<br/>" in str(result[0][1])


class TestSplitDf:
    def test_even_split(self):
        df = pd.DataFrame({"a": range(10)})
        chunks = _split_df(df, 5)
        assert len(chunks) == 5
        assert sum(len(c) for c in chunks) == 10

    def test_uneven_split(self):
        df = pd.DataFrame({"a": range(7)})
        chunks = _split_df(df, 3)
        assert len(chunks) == 3
        assert sum(len(c) for c in chunks) == 7

    def test_more_chunks_than_rows(self):
        df = pd.DataFrame({"a": range(3)})
        chunks = _split_df(df, 10)
        assert len(chunks) == 3
        assert sum(len(c) for c in chunks) == 3


class TestMakePdfForRecord:
    def test_basic_pdf_generation(self):
        main_row = pd.Series({
            "Record Link ID": "123",
            DUI_COL: "00000000-0",
            "Name": "Test User",
        })
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            out_path = f.name

        try:
            make_pdf_for_record(main_row, sub_rows=None, out_path=out_path, include_empty=False)
            assert os.path.exists(out_path)
            assert os.path.getsize(out_path) > 0
        finally:
            os.unlink(out_path)

    def test_pdf_with_subrecords(self):
        main_row = pd.Series({
            "Record Link ID": "123",
            DUI_COL: "00000000-0",
            "Name": "Test",
        })
        sub_rows = pd.DataFrame([
            {"Record Link ID": "123", "S.No.": "1", "SubField": "A"},
            {"Record Link ID": "123", "S.No.": "2", "SubField": "B"},
        ])

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            out_path = f.name

        try:
            make_pdf_for_record(main_row, sub_rows=sub_rows, out_path=out_path, include_empty=False)
            assert os.path.exists(out_path)
            assert os.path.getsize(out_path) > 0
        finally:
            os.unlink(out_path)


class TestReadConcatCsvs:
    def test_read_single_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("a,b\n1,2\n3,4\n")
            path = f.name
        try:
            df = read_and_concat_csvs(path)
            assert df.shape == (2, 2)
            assert list(df.columns) == ["a", "b"]
        finally:
            os.unlink(path)

    def test_read_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(2):
                path = os.path.join(tmpdir, f"file{i}.csv")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"a,b\n{i},0\n")
            df = read_and_concat_csvs(tmpdir)
            assert df.shape == (2, 2)

    def test_missing_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(RuntimeError, match="No CSV files"):
                read_and_concat_csvs(tmpdir)
