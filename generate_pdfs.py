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
  --workers 4           (procesar en paralelo; 1=secuencial, default)
  --zip                 (exportar todo a un ZIP al finalizar)
"""

import os
import re
import math
import time
import datetime
import argparse
import logging
import zipfile
import multiprocessing as mp
from typing import Any, Optional
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


DUI_COL = "01. Numero de Documento Único de Identidad (DUI)"


def load_config(path: str = "config.json") -> dict:
    if not os.path.exists(path):
        return {}
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Could not load {path}: {e}")
        return {}


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

# ── Font registration & color palette ─────────────────────────────────────

_SCRIPT_DIR = Path(__file__).parent.resolve()
_FONTS_DIR = _SCRIPT_DIR / ".agents" / "skills" / "canvas-design" / "canvas-fonts"

_FONT_BODY = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONT_MONO = "Courier"

if _FONTS_DIR.exists():
    _registered = {}
    for family, fname in [
        ("WorkSans", "WorkSans-Regular.ttf"),
        ("WorkSans-Bold", "WorkSans-Bold.ttf"),
        ("JetBrainsMono", "JetBrainsMono-Regular.ttf"),
    ]:
        fp = _FONTS_DIR / fname
        if fp.exists():
            try:
                pdfmetrics.registerFont(TTFont(family, str(fp)))
                _registered[family] = True
            except Exception:
                pass
    if "WorkSans" in _registered:
        _FONT_BODY = "WorkSans"
    if "WorkSans-Bold" in _registered:
        _FONT_BOLD = "WorkSans-Bold"
    if "JetBrainsMono" in _registered:
        _FONT_MONO = "JetBrainsMono"

NAVY = colors.HexColor("#1C4F8E")
DARK_BLUE = colors.HexColor("#0D3D6E")
WHITE = colors.white
SLATE = colors.HexColor("#4A5568")
NEAR_BLACK = colors.HexColor("#1A202C")
LIGHT_GRAY = colors.HexColor("#E1E1E1")
ROW_ALT = colors.HexColor("#F1F4F9")
GOLD = colors.HexColor("#C4953A")

# ── Style definitions ─────────────────────────────────────────────────────

TITLE_STYLE = ParagraphStyle("title", fontName=_FONT_BOLD, fontSize=16,
                              leading=20, textColor=NAVY, spaceAfter=2)
SUBTITLE_STYLE = ParagraphStyle("subtitle", fontName=_FONT_BODY, fontSize=8,
                                 leading=12, textColor=SLATE, spaceAfter=14)
LABEL_STYLE = ParagraphStyle("label", fontName=_FONT_BOLD, fontSize=9,
                              leading=14, textColor=NAVY)
VALUE_STYLE = ParagraphStyle("value", fontName=_FONT_BODY, fontSize=9,
                              leading=14, textColor=NEAR_BLACK)
H2_STYLE = ParagraphStyle("h2", fontName=_FONT_BOLD, fontSize=11,
                           leading=14, textColor=NAVY, spaceAfter=6)

def _make_table_style(num_rows: int) -> TableStyle:
    cmds = [
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LIGHT_GRAY),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, LIGHT_GRAY),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, LIGHT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, num_rows, 2):
        cmds.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))
    return TableStyle(cmds)

# ── Header / Footer callback ──────────────────────────────────────────────

def _header_footer(canvas, doc):
    canvas.saveState()
    pw, ph = doc.pagesize
    ml = doc.leftMargin
    cw = doc.width
    page_num = doc.page + 1

    # ── Header separator ──
    hy = ph - doc.topMargin
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(0.6)
    canvas.line(ml, hy, ml + cw, hy)

    canvas.setFont(_FONT_BOLD, 7)
    canvas.setFillColor(NAVY)
    canvas.drawString(ml, hy + 5, "SUBSIDIO GLP — SOLICITUD")

    canvas.setFont(_FONT_BODY, 7)
    canvas.setFillColor(SLATE)
    canvas.drawRightString(ml + cw, hy + 5,
                           datetime.date.today().strftime("%d/%m/%Y"))

    # ── Footer separator ──
    fy = doc.bottomMargin
    canvas.setStrokeColor(LIGHT_GRAY)
    canvas.setLineWidth(0.4)
    canvas.line(ml, fy, ml + cw, fy)

    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    canvas.setFont(_FONT_BODY, 7)
    canvas.setFillColor(SLATE)
    canvas.drawString(ml, fy - 12, f"Página {page_num} · {now_str}")
    canvas.drawRightString(ml + cw, fy - 12,
                           "Documento generado electrónicamente")

    canvas.restoreState()


_label_cache: dict[str, Paragraph] = {}


def label_cache_clear():
    _label_cache.clear()


def _get_label(col_name: str) -> Paragraph:
    p = _label_cache.get(col_name)
    if p is None:
        p = Paragraph(col_name, LABEL_STYLE)
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


def _col_widths(row, exclude_cols: set, total_width: float) -> tuple[float, float]:
    labels = [c for c in row.keys() if c not in exclude_cols]
    if not labels:
        return 2.2 * inch, total_width - 2.2 * inch
    max_w = max(stringWidth(c, _FONT_BOLD, 9) + 16 for c in labels)
    lw = min(max(max_w, 1.5 * inch), 3.0 * inch)
    return lw, total_width - lw


def make_pdf_for_record(main_row, sub_rows: Optional[pd.DataFrame],
                        out_path: str, include_empty: bool) -> None:
    total_w = letter[0] - 1.5 * inch  # 7.0 in

    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.75 * inch,
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )

    story = []
    story.append(Paragraph("Solicitud de Subsidio GLP", TITLE_STYLE))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY, spaceAfter=14))

    main_rows = build_table_rows(main_row, include_empty=include_empty, exclude_cols={"Record Link ID"})
    if main_rows:
        lw, vw = _col_widths(main_row, {"Record Link ID"}, total_w)
        main_table = Table(main_rows, colWidths=[lw, vw], repeatRows=0)
        main_table.setStyle(_make_table_style(len(main_rows)))
        story.append(main_table)

    if sub_rows is not None and len(sub_rows) > 0:
        story.append(Spacer(1, 18))
        story.append(PageBreak())
        story.append(Paragraph("Caracterización del grupo familiar", TITLE_STYLE))
        story.append(Paragraph("Composición y datos del núcleo familiar", SUBTITLE_STYLE))
        story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY, spaceAfter=14))

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
            if sub_table_rows:
                lw, vw = _col_widths(sub_row, exclude_sub, total_w)
                sub_table = Table(sub_table_rows, colWidths=[lw, vw])
                sub_table.setStyle(_make_table_style(len(sub_table_rows)))
                story.append(sub_table)
                story.append(Spacer(1, 12))

    doc.build(story)


_worker_lock: Any = None


def _init_worker(lock):
    global _worker_lock
    _worker_lock = lock


def _reserve_filename(output_dir: str, base: str, rid: str) -> str:
    with _worker_lock:
        filename = sanitize_filename(f"{base}.pdf")
        out_path = os.path.join(output_dir, filename)
        if os.path.exists(out_path):
            filename = sanitize_filename(f"{base}-{rid}.pdf")
            out_path = os.path.join(output_dir, filename)
        Path(out_path).touch()
    return out_path


def process_chunk(chunk_df: pd.DataFrame, sub_groups: dict, include_empty: bool,
                  output_dir: str) -> tuple[int, int]:
    label_cache_clear()
    generated = 0
    failed = 0

    for _, row in chunk_df.iterrows():
        try:
            rid = safe_text(row.get("Record Link ID", "")).strip()
            if rid == "":
                continue

            dui = safe_text(row.get(DUI_COL, "")).strip()
            base = dui if dui != "" else rid

            out_path = _reserve_filename(output_dir, base, rid)
            sub_rows = sub_groups.get(rid)
            make_pdf_for_record(row, sub_rows, out_path, include_empty)
            generated += 1
        except Exception:
            log.exception(f"Failed for RID={safe_text(row.get('Record Link ID', ''))}")
            failed += 1

    return generated, failed


def _process_chunk_wrapper(args):
    return process_chunk(*args)


def main():
    import multiprocessing as mp
    mp.freeze_support()
    start_time = time.time()

    config = load_config()
    cfg_paths = config.get("paths", {})
    cfg_opts = config.get("options", {})

    parser = argparse.ArgumentParser(description="Genera PDFs por cada registro del formulario principal")
    parser.add_argument("--main", default=cfg_paths.get("main"),
                        help="CSV o carpeta del formulario principal (default: config.json)")
    parser.add_argument("--sub", default=cfg_paths.get("sub"),
                        help="CSV o carpeta del subformulario (default: config.json)")
    parser.add_argument("--out", default=cfg_paths.get("out"),
                        help="Carpeta de salida para PDFs (default: config.json)")
    parser.add_argument("--limit", type=int, default=cfg_opts.get("limit", 0),
                        help="0=sin límite; N=solo primeros N")
    parser.add_argument("--only", default="",
                        help="Filtrar por DUI(s), separados por coma")
    parser.add_argument("--include-empty", action="store_true",
                        help="Incluir campos vacíos en el PDF")
    parser.add_argument("--zip", action="store_true",
                        help="Exportar todo a un ZIP al finalizar")
    parser.add_argument("--workers", type=int, default=cfg_opts.get("workers", 1),
                        help="Workers en paralelo (1=secuencial, N=paralelo con N workers)")
    args = parser.parse_args()

    if not args.main or not args.sub or not args.out:
        parser.error("--main, --sub, and --out are required (via CLI or config.json)")

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

    n_workers = max(1, min(args.workers, total_records))

    os.makedirs(args.out, exist_ok=True)

    generated = 0
    failed = 0
    placeholder_files: list[str] = []

    try:
        if n_workers <= 1:
            label_cache_clear()
            used_names: set[str] = set()

            with tqdm(total=total_records, desc="Generando PDFs", unit="PDF", ncols=100, colour="green") as pbar:
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
        else:
            chunks = _split_df(main_df, n_workers)
            worker_args = [(chunk, sub_groups, args.include_empty, args.out)
                           for chunk in chunks]

            log.info(f"Using {n_workers} parallel workers...")

            with mp.Manager() as manager:
                lock = manager.Lock()
                with mp.Pool(n_workers, initializer=_init_worker, initargs=(lock,)) as pool:
                    with tqdm(total=total_records, desc="Generando PDFs", unit="PDF", ncols=100, colour="green") as pbar:
                        for g, f in pool.imap_unordered(_process_chunk_wrapper, worker_args):
                            generated += g
                            failed += f
                            pbar.update(g)

    finally:
        placeholder_files = [
            os.path.join(args.out, f)
            for f in os.listdir(args.out)
            if os.path.isfile(os.path.join(args.out, f))
            and os.path.getsize(os.path.join(args.out, f)) == 0
        ]
        for pf in placeholder_files:
            try:
                os.unlink(pf)
            except Exception:
                pass

    elapsed = time.time() - start_time
    if elapsed < 60:
        time_str = f"{elapsed:.2f} seconds"
    else:
        time_str = f"{int(elapsed // 60)} min {elapsed % 60:.2f} sec"

    print()
    print(f"  OK. Generated: {generated} PDFs  |  Failed: {failed}  |  Time: {time_str}")

    if args.zip and generated > 0:
        zip_path = os.path.join(args.out, "subsidios_pdfs.zip")
        log.info(f"Creating ZIP: {zip_path} ...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for pdf_path in Path(args.out).glob("*.pdf"):
                if pdf_path.name == "subsidios_pdfs.zip":
                    continue
                zf.write(str(pdf_path), pdf_path.name)
        print(f"  ZIP: {zip_path}")

    log.info(f"Done. Generated: {generated}  |  Failed: {failed}  |  Time: {time_str}")


if __name__ == "__main__":
    main()
