#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera PDFs por cada registro del formulario principal, uniendo subregistros de SubForm4.

Nombre de PDF: por defecto usa el campo '01. Numero de Documento Único de Identidad (DUI)'.
Si el DUI viene vacío, usa 'Record Link ID' como fallback.

Requisitos:
  pip install pandas reportlab tqdm

Uso básico:
  python generate_pdfs.py --main "SolicituddesubsidioGLPv3_Records_1.csv" \
                              --sub  "SolicituddesubsidioGLPv3_SubForm4_Records_1.csv" \
                              --out  "out_pdfs"

Opcional:
  --limit 100           (solo primeros 100)
  --only "06784334-6"   (filtrar por DUI; acepta varios separados por coma)
  --include-empty       (incluye filas aunque vengan vacías)
  --workers 4           (procesar en paralelo con 4 workers; 0 = auto)
  --zip                 (exportar todo a un ZIP al finalizar)
"""

import os
import re
import math
import time
import argparse
import logging
import zipfile
import shutil
import multiprocessing as mp
from typing import Any, Optional
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


DUI_COL = "01. Numero de Documento Único de Identidad (DUI)"


def safe_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    s = str(x)
    if s.lower() == "nan":
        return ""
    return s


def sanitize_filename(name: str) -> str:
    name = safe_text(name).strip()
    if name == "":
        name = "sin_nombre"
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    return name


def read_and_concat_csvs(path: str) -> pd.DataFrame:
    if os.path.isdir(path):
        csv_files = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith('.csv')]
        if not csv_files:
            raise RuntimeError(f"No CSV files found in folder: {path}")
        dfs = [pd.read_csv(f, dtype=str, keep_default_na=False, low_memory=False) for f in csv_files]
        return pd.concat(dfs, ignore_index=True)
    return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)


def _split_df(df: pd.DataFrame, n: int) -> list[pd.DataFrame]:
    n = max(1, min(n, len(df)))
    chunks = []
    chunk_size = max(1, len(df) // n)
    for i in range(n):
        start = i * chunk_size
        chunks.append(df.iloc[start:start + chunk_size] if i < n - 1 else df.iloc[start:])
    return chunks


_styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle("title", parent=_styles["Title"], fontSize=16, leading=20, spaceAfter=8)
SUBTITLE_STYLE = ParagraphStyle("subtitle", parent=_styles["Normal"], fontSize=10, leading=12, textColor=colors.grey, spaceAfter=12)
LABEL_STYLE = ParagraphStyle("label", parent=_styles["Normal"], fontSize=10, leading=12)
VALUE_STYLE = ParagraphStyle("value", parent=_styles["Normal"], fontSize=10, leading=12)
H2_STYLE = ParagraphStyle("h2", parent=_styles["Heading2"], spaceAfter=6)

TABLE_STYLE = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
])

_label_cache: dict[str, Paragraph] = {}


def _get_label(col_name: str) -> Paragraph:
    p = _label_cache.get(col_name)
    if p is None:
        p = Paragraph(f"<b>{col_name}</b>", LABEL_STYLE)
        _label_cache[col_name] = p
    return p


def build_table_rows(row, include_empty: bool, exclude_cols: set) -> list:
    rows = []
    for col_name, val in row.items():
        if col_name in exclude_cols:
            continue
        s = safe_text(val).strip()
        if s == "" and not include_empty:
            continue
        rows.append([_get_label(col_name), Paragraph(s.replace("\n", "<br/>"), VALUE_STYLE)])
    return rows


def make_pdf_for_record(main_row, sub_rows: Optional[pd.DataFrame],
                        out_path: str, include_empty: bool) -> None:
    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch
    )

    story = []
    story.append(Paragraph("Solicitud De Subsidio GLP - V3 Report", TITLE_STYLE))
    story.append(Paragraph("Form: Solicitud para aplicar al subsidio del GLP - v3", SUBTITLE_STYLE))

    main_rows = build_table_rows(main_row, include_empty=include_empty, exclude_cols={"Record Link ID"})
    main_table = Table(main_rows, colWidths=[2.8 * inch, 4.2 * inch], repeatRows=0)
    main_table.setStyle(TABLE_STYLE)
    story.append(main_table)

    if sub_rows is not None and len(sub_rows) > 0:
        story.append(PageBreak())
        story.append(Paragraph("SubForm4 - Subregistros", TITLE_STYLE))
        story.append(Paragraph("Entradas asociadas al subformulario (agrupadas por #).", SUBTITLE_STYLE))

        if "S.No." in sub_rows.columns:
            try:
                sub_rows = sub_rows.assign(_sno=pd.to_numeric(sub_rows["S.No."], errors="coerce")) \
                                   .sort_values("_sno") \
                                   .drop(columns=["_sno"])
            except Exception:
                pass

        exclude_sub = {"Record Link ID"}

        for i, (_, sub_row) in enumerate(sub_rows.iterrows(), start=1):
            sno = safe_text(sub_row.get("S.No.", "")).strip()
            head = f"#{i}" + (f" (S.No.: {sno})" if sno != "" else "")
            story.append(Paragraph(head, H2_STYLE))

            sub_table_rows = build_table_rows(sub_row, include_empty=include_empty, exclude_cols=exclude_sub)
            sub_table = Table(sub_table_rows, colWidths=[2.8 * inch, 4.2 * inch])
            sub_table.setStyle(TABLE_STYLE)
            story.append(sub_table)
            story.append(Spacer(1, 12))

    doc.build(story)


def process_chunk(chunk_df: pd.DataFrame, sub_groups: dict, include_empty: bool,
                  output_dir: str, worker_id: int) -> tuple[int, int]:
    label_cache_clear()
    worker_dir = os.path.join(output_dir, f".tmp_{worker_id}")
    os.makedirs(worker_dir, exist_ok=True)

    generated = 0
    failed = 0

    for _, row in chunk_df.iterrows():
        try:
            rid = safe_text(row.get("Record Link ID", "")).strip()
            if rid == "":
                continue

            dui = safe_text(row.get(DUI_COL, "")).strip()
            base = dui if dui != "" else rid
            filename = sanitize_filename(f"{base}.pdf")
            out_path = os.path.join(worker_dir, filename)

            if os.path.exists(out_path):
                filename = sanitize_filename(f"{base}-{rid}.pdf")
                out_path = os.path.join(worker_dir, filename)

            sub_rows = sub_groups.get(rid)
            make_pdf_for_record(row, sub_rows, out_path, include_empty)
            generated += 1
        except Exception:
            log.exception(f"Failed for RID={safe_text(row.get('Record Link ID', ''))}")
            failed += 1

    return generated, failed


def _collect_results(output_dir: str, n_workers: int, create_zip: bool):
    if create_zip:
        zip_path = os.path.join(os.path.dirname(output_dir), "subsidios_pdfs.zip")
        log.info(f"Creating ZIP: {zip_path} ...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for i in range(n_workers):
                worker_dir = os.path.join(output_dir, f".tmp_{i}")
                if not os.path.isdir(worker_dir):
                    continue
                for pdf_path in Path(worker_dir).iterdir():
                    if pdf_path.suffix.lower() == ".pdf":
                        zf.write(str(pdf_path), pdf_path.name)

        for i in range(n_workers):
            shutil.rmtree(os.path.join(output_dir, f".tmp_{i}"), ignore_errors=True)
        log.info(f"ZIP created: {zip_path}")
    else:
        log.info("Moving PDFs to output directory...")
        seen: set[str] = set()
        for i in range(n_workers):
            worker_dir = os.path.join(output_dir, f".tmp_{i}")
            if not os.path.isdir(worker_dir):
                continue
            for pdf_path in Path(worker_dir).iterdir():
                if pdf_path.suffix.lower() != ".pdf":
                    continue
                dst = os.path.join(output_dir, pdf_path.name)
                if pdf_path.name in seen or os.path.exists(dst):
                    dst = os.path.join(output_dir, f"{pdf_path.stem}_{i}{pdf_path.suffix}")
                seen.add(os.path.basename(dst))
                shutil.move(str(pdf_path), dst)
            shutil.rmtree(worker_dir, ignore_errors=True)


def _create_zip(source_dir: str, target_dir: str):
    zip_path = os.path.join(os.path.dirname(target_dir), "subsidios_pdfs.zip")
    log.info(f"Creating ZIP: {zip_path} ...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for pdf_path in Path(source_dir).glob("*.pdf"):
            zf.write(str(pdf_path), pdf_path.name)
    log.info(f"ZIP created: {zip_path}")


def label_cache_clear():
    _label_cache.clear()


def main():
    start_time = time.time()

    parser = argparse.ArgumentParser(description="Genera PDFs por cada registro del formulario principal")
    parser.add_argument("--main", required=True, help="CSV o carpeta del formulario principal")
    parser.add_argument("--sub", required=True, help="CSV o carpeta del subformulario")
    parser.add_argument("--out", required=True, help="Carpeta de salida para PDFs")
    parser.add_argument("--limit", type=int, default=0, help="0=sin límite; N=solo primeros N")
    parser.add_argument("--only", default="", help="Filtrar por DUI(s), separados por coma")
    parser.add_argument("--include-empty", action="store_true", help="Incluir campos vacíos en el PDF")
    parser.add_argument("--zip", action="store_true", help="Exportar todo a un ZIP al finalizar")
    parser.add_argument("--workers", type=int, default=0,
                        help="Workers en paralelo (0 = CPU count, 1 = secuencial)")
    args = parser.parse_args()

    log.info("Reading CSV files...")
    main_df = read_and_concat_csvs(args.main)
    sub_df = read_and_concat_csvs(args.sub)

    if "Record Link ID" not in main_df.columns or "Record Link ID" not in sub_df.columns:
        raise RuntimeError("Column 'Record Link ID' not found in both CSVs.")

    only_duis = [x.strip() for x in args.only.split(",") if x.strip()]
    if only_duis and DUI_COL in main_df.columns:
        main_df = main_df[main_df[DUI_COL].astype(str).str.strip().isin(only_duis)]

    log.info("Indexing sub-records by Record Link ID...")
    sub_groups = dict(tuple(sub_df.groupby("Record Link ID", sort=False)))

    total_records = len(main_df)
    if args.limit > 0 and args.limit < total_records:
        total_records = args.limit
        main_df = main_df.iloc[:total_records]

    log.info(f"Records to process: {total_records}")

    if total_records == 0:
        log.warning("No records to process.")
        return

    n_workers = max(1, args.workers if args.workers > 0 else mp.cpu_count())
    n_workers = min(n_workers, total_records)

    os.makedirs(args.out, exist_ok=True)

    if n_workers <= 1:
        generated = 0
        failed = 0
        label_cache_clear()
        used_names: set[str] = set()

        with tqdm(total=total_records, desc="Generating PDFs", unit="PDF", ncols=100, colour="green") as pbar:
            for _, row in main_df.iterrows():
                try:
                    rid = safe_text(row.get("Record Link ID", "")).strip()
                    if rid == "":
                        pbar.update(1)
                        continue

                    dui = safe_text(row.get(DUI_COL, "")).strip()
                    base = dui if dui != "" else rid
                    filename = sanitize_filename(f"{base}.pdf")
                    out_path = os.path.join(args.out, filename)

                    if filename in used_names or os.path.exists(out_path):
                        filename = sanitize_filename(f"{base}-{rid}.pdf")
                        out_path = os.path.join(args.out, filename)

                    used_names.add(filename)
                    sub_rows = sub_groups.get(rid)
                    make_pdf_for_record(row, sub_rows, out_path, args.include_empty)
                    generated += 1
                except Exception:
                    log.exception(f"Failed for RID={safe_text(row.get('Record Link ID', ''))}")
                    failed += 1

                pbar.update(1)

        if args.zip and generated > 0:
            _create_zip(args.out, args.out)

    else:
        chunks = _split_df(main_df, n_workers)
        worker_args = [(chunk, sub_groups, args.include_empty, args.out, i)
                       for i, chunk in enumerate(chunks)]

        log.info(f"Using {n_workers} parallel workers...")

        with mp.Pool(n_workers) as pool:
            results = pool.starmap(process_chunk, worker_args)

        generated = sum(r[0] for r in results)
        failed = sum(r[1] for r in results)

        _collect_results(args.out, n_workers, args.zip)

    elapsed = time.time() - start_time
    if elapsed < 60:
        time_str = f"{elapsed:.2f} seconds"
    else:
        time_str = f"{int(elapsed // 60)} min {elapsed % 60:.2f} sec"

    log.info(f"Done. Generated: {generated}  |  Failed: {failed}  |  Time: {time_str}")
    if args.zip:
        log.info(f"ZIP: {os.path.join(os.path.dirname(args.out), 'subsidios_pdfs.zip')}")


if __name__ == "__main__":
    main()
