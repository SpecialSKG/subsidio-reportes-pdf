#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera PDFs por cada registro del formulario principal, uniendo subregistros de SubForm4.

Nombre de PDF: por defecto usa el campo '01. Numero de Documento Único de Identidad (DUI)'.
Si el DUI viene vacío, usa 'Record Link ID' como fallback.

Requisitos:
  pip install pandas reportlab

Uso básico:
  python generate_pdfs.py --main "SolicituddesubsidioGLPv3_Records_1.csv" \
                              --sub  "SolicituddesubsidioGLPv3_SubForm4_Records_1.csv" \
                              --out  "out_pdfs"

Opcional:
  --limit 100           (solo primeros 100)
  --only "06784334-6"   (filtrar por DUI; acepta varios separados por coma)
  --include-empty       (incluye filas aunque vengan vacías)
"""

import os
import re
import math
import time
import argparse
import pandas as pd
from tqdm import tqdm
import zipfile

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


def safe_text(x):
    if x is None:
        return ""
    # pandas a veces mete NaN float
    if isinstance(x, float) and math.isnan(x):
        return ""
    s = str(x)
    if s.lower() == "nan":
        return ""
    return s


def sanitize_filename(name):
    name = safe_text(name).strip()
    if name == "":
        name = "sin_nombre"
    # Windows-safe
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    return name


def build_table_rows(row_dict, include_empty, exclude_cols):
    rows = []
    for k in row_dict.keys():  # respeta orden original del dict (pandas mantiene orden de columnas)
        if k in exclude_cols:
            continue
        val = safe_text(row_dict.get(k)).strip()
        if val == "" and not include_empty:
            continue

        label = Paragraph(f"<b>{k}</b>", LABEL_STYLE)
        value = Paragraph(val.replace("\n", "<br/>"), VALUE_STYLE)
        rows.append([label, value])
    return rows


def make_pdf_for_record(main_row, sub_rows, out_path, include_empty):
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

    # Principal
    main_rows = build_table_rows(
        main_row,
        include_empty=include_empty,
        exclude_cols={"Record Link ID"}
    )

    main_table = Table(main_rows, colWidths=[2.8 * inch, 4.2 * inch], repeatRows=0)
    main_table.setStyle(TABLE_STYLE)
    story.append(main_table)

    # SubForm4
    if sub_rows is not None and len(sub_rows) > 0:
        story.append(PageBreak())
        story.append(Paragraph("SubForm4 - Subregistros", TITLE_STYLE))
        story.append(Paragraph("Entradas asociadas al subformulario (agrupadas por #).", SUBTITLE_STYLE))

        # orden por S.No. si existe
        if "S.No." in sub_rows.columns:
            try:
                sub_rows = sub_rows.assign(_sno=pd.to_numeric(sub_rows["S.No."], errors="coerce")) \
                                 .sort_values("_sno") \
                                 .drop(columns=["_sno"])
            except Exception:
                pass

        exclude_sub = {"Record Link ID"}
        sub_records = sub_rows.to_dict(orient="records")

        for i, sub_row in enumerate(sub_records, start=1):
            sno = safe_text(sub_row.get("S.No.")).strip()
            head = f"#{i}" + (f" (S.No.: {sno})" if sno != "" else "")
            story.append(Paragraph(head, H2_STYLE))

            sub_table_rows = build_table_rows(
                sub_row,
                include_empty=include_empty,
                exclude_cols=exclude_sub
            )
            sub_table = Table(sub_table_rows, colWidths=[2.8 * inch, 4.2 * inch])
            sub_table.setStyle(TABLE_STYLE)
            story.append(sub_table)
            story.append(Spacer(1, 12))

    doc.build(story)


def main():
    # Iniciar medición de tiempo
    start_time = time.time()
    

    parser = argparse.ArgumentParser()
    parser.add_argument("--main", required=True, help="CSV/carpeta del formulario principal")
    parser.add_argument("--sub", required=True, help="CSV/carpeta del subformulario (SubForm4)")
    parser.add_argument("--out", required=True, help="Carpeta de salida para PDFs")
    parser.add_argument("--limit", type=int, default=0, help="0 = sin límite; si no, genera solo N registros")
    parser.add_argument("--only", default="", help="Filtrar por DUI (col 01...), varios separados por coma")
    parser.add_argument("--include-empty", action="store_true", help="Incluye filas aunque el valor venga vacío")
    parser.add_argument("--zip", action="store_true", help="Exporta todos los PDFs generados a un archivo ZIP al finalizar")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)


    def read_and_concat_csvs(path):
        if os.path.isdir(path):
            csv_files = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith('.csv')]
            if not csv_files:
                raise RuntimeError(f"No se encontraron archivos CSV en la carpeta: {path}")
            dfs = [pd.read_csv(f, dtype=str, keep_default_na=False, low_memory=False) for f in csv_files]
            return pd.concat(dfs, ignore_index=True)
        else:
            return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)

    print("📂 Leyendo archivos CSV...")
    main_df = read_and_concat_csvs(args.main)
    sub_df = read_and_concat_csvs(args.sub)

    # Llave de unión
    if "Record Link ID" not in main_df.columns or "Record Link ID" not in sub_df.columns:
        raise RuntimeError("No encuentro la columna 'Record Link ID' en ambos CSV.")

    # Filtro por DUI si aplica
    only_duis = [x.strip() for x in args.only.split(",") if x.strip() != ""]
    dui_col = "01. Numero de Documento Único de Identidad (DUI)"
    if len(only_duis) > 0 and dui_col in main_df.columns:
        main_df = main_df[main_df[dui_col].astype(str).str.strip().isin(only_duis)]

    # Indexar subform por Record Link ID
    # (groupby es rápido y evita hacer filtros N veces)
    sub_groups = dict(tuple(sub_df.groupby("Record Link ID", sort=False)))

    # Determinar cuántos PDFs se generarán
    total_records = len(main_df)
    if args.limit > 0:
        total_records = min(total_records, args.limit)
    
    print(f"📊 Total de registros a procesar: {total_records}")
    print(f"📝 Generando PDFs en: {args.out}")
    print()


    count = 0
    pdf_files = []
    # Usar tqdm para barra de progreso
    with tqdm(total=total_records, desc="Generando PDFs", unit="PDF", ncols=100, colour="green") as pbar:
        for _, row in main_df.iterrows():
            rid = safe_text(row.get("Record Link ID")).strip()
            if rid == "":
                continue

            dui = safe_text(row.get(dui_col)).strip()

            # Nombre de PDF:
            # - Por defecto: DUI (según requerimiento actual)
            # - Fallback: Record Link ID si el DUI viene vacío
            base = dui if dui != "" else rid
            filename = f"{base}.pdf"
            filename = sanitize_filename(filename)

            # Evitar sobreescritura si existe el mismo DUI más de una vez
            out_path = os.path.join(args.out, filename)
            if os.path.exists(out_path):
                filename = sanitize_filename(f"{base}-{rid}.pdf")
                out_path = os.path.join(args.out, filename)

            sub_rows = sub_groups.get(rid)
            make_pdf_for_record(row.to_dict(), sub_rows, out_path, include_empty=args.include_empty)

            pdf_files.append(out_path)
            count += 1
            pbar.update(1)
            
            if args.limit > 0 and count >= args.limit:
                break

    # Exportar a ZIP si se solicita
    if args.zip and pdf_files:
        zip_name = os.path.join(os.path.dirname(args.out), "subsidios_pdfs.zip")
        print(f"\n🗜️  Comprimiendo PDFs en: {zip_name} ...")
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for pdf in pdf_files:
                arcname = os.path.relpath(pdf, args.out)
                zipf.write(pdf, arcname)
        print(f"✅ ZIP creado: {zip_name}")

    # Calcular tiempo total
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Formatear tiempo
    if elapsed_time < 60:
        time_str = f"{elapsed_time:.2f} segundos"
    else:
        minutes = int(elapsed_time // 60)
        seconds = elapsed_time % 60
        time_str = f"{minutes} minuto(s) y {seconds:.2f} segundos"
    

    print()
    print(f"✅ Listo. PDFs generados: {count} en: {args.out}")
    if args.zip and pdf_files:
        print(f"🗜️  ZIP generado en: {os.path.join(os.path.dirname(args.out), 'subsidios_pdfs.zip')}")
    print(f"⏱️  Tiempo total de ejecución: {time_str}")



# ====== estilos globales (para no recrearlos por PDF) ======
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


if __name__ == "__main__":
    main()
