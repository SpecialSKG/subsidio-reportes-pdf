#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
import time
import zipfile
import datetime
from pathlib import Path

import pandas as pd

from generate_pdfs import (
    read_and_concat_csvs,
    make_pdf_for_record,
    build_table_rows,
    safe_text,
    sanitize_filename,
    DUI_COL,
    label_cache_clear,
)


class CalendarPopup:
    MONTHS = ["ene", "feb", "mar", "abr", "may", "jun",
              "jul", "ago", "sep", "oct", "nov", "dic"]
    DAYS = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]

    def __init__(self, parent, callback):
        self.callback = callback
        self.win = tk.Toplevel(parent)
        self.win.title("Seleccionar fecha")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()

        today = datetime.date.today()
        self.yr = today.year
        self.mo = today.month

        top = ttk.Frame(self.win, padding="8")
        top.pack()

        btn_frame = ttk.Frame(top)
        btn_frame.pack(pady=(0, 6))
        ttk.Button(btn_frame, text=" ◀ ", command=self._prev_month).pack(side=tk.LEFT)
        self.lbl_title = ttk.Label(btn_frame, text="", width=18, anchor=tk.CENTER,
                                   font=("TkDefaultFont", 10, "bold"))
        self.lbl_title.pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text=" ▶ ", command=self._next_month).pack(side=tk.LEFT)

        cal_frame = ttk.Frame(top)
        cal_frame.pack()

        for i, d in enumerate(self.DAYS):
            ttk.Label(cal_frame, text=d, width=4, anchor=tk.CENTER,
                      font=("TkDefaultFont", 8, "bold")).grid(row=0, column=i, padx=1, pady=1)

        self.day_buttons = []
        for r in range(6):
            row_btns = []
            for c in range(7):
                b = ttk.Button(cal_frame, width=4, command=lambda rr=r, cc=c: self._pick_day(rr, cc))
                b.grid(row=r + 1, column=c, padx=1, pady=1)
                row_btns.append(b)
            self.day_buttons.append(row_btns)

        btn_ok = ttk.Frame(top)
        btn_ok.pack(pady=(8, 0))
        ttk.Button(btn_ok, text="Hoy", command=self._pick_today).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_ok, text="Cancelar", command=self.win.destroy).pack(side=tk.LEFT)

        self._update()

    def _prev_month(self):
        if self.mo == 1:
            self.mo = 12
            self.yr -= 1
        else:
            self.mo -= 1
        self._update()

    def _next_month(self):
        if self.mo == 12:
            self.mo = 1
            self.yr += 1
        else:
            self.mo += 1
        self._update()

    def _update(self):
        import calendar
        self.lbl_title.config(
            text=f"{self.MONTHS[self.mo - 1].capitalize()} {self.yr}"
        )
        cal = calendar.monthcalendar(self.yr, self.mo)
        for r in range(6):
            for c in range(7):
                btn = self.day_buttons[r][c]
                if r < len(cal) and cal[r][c] != 0:
                    day = cal[r][c]
                    btn.config(text=str(day), state="normal")
                    btn.day = day
                else:
                    btn.config(text="", state="disabled")
                    btn.day = None

    def _pick_day(self, r, c):
        btn = self.day_buttons[r][c]
        if btn.day is not None:
            d = datetime.date(self.yr, self.mo, btn.day)
            self.callback(d)
            self.win.destroy()

    def _pick_today(self):
        self.callback(datetime.date.today())
        self.win.destroy()


MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
         "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}

MESES_LISTA = ["ene", "feb", "mar", "abr", "may", "jun",
               "jul", "ago", "sep", "oct", "nov", "dic"]

def parsear_fecha(s):
    if not s or not isinstance(s, str):
        return None
    partes = s.strip().split("-")
    if len(partes) != 3:
        return None
    try:
        dia = int(partes[0])
        mes = MESES.get(partes[1].lower())
        anio = int(partes[2])
        if mes is None:
            return None
        return datetime.date(anio, mes, dia)
    except (ValueError, KeyError):
        return None


class GeneradorPDFsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de PDFs - Subsidio GLP")
        self.root.geometry("720x620")
        self.root.resizable(False, False)
        self.procesando = False
        self.fecha_min = None
        self.fecha_max = None
        self._fecha_desde_date = None
        self._fecha_hasta_date = None
        self._build_widgets()

    def _build_widgets(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── Carpeta principal ──
        ttk.Label(main_frame, text="Carpeta principal (CSVs):").grid(
            row=0, column=0, sticky=tk.W, pady=(0, 2)
        )
        self.main_path = tk.StringVar(value="input/main")
        f = ttk.Frame(main_frame)
        f.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 5))
        ttk.Entry(f, textvariable=self.main_path, width=55).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(f, text="Examinar...", command=self._browse_main).pack(side=tk.LEFT)

        # ── Carpeta sub ──
        ttk.Label(main_frame, text="Carpeta subformularios (CSVs):").grid(
            row=2, column=0, sticky=tk.W, pady=(0, 2)
        )
        self.sub_path = tk.StringVar(value="input/sub")
        f = ttk.Frame(main_frame)
        f.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 5))
        ttk.Entry(f, textvariable=self.sub_path, width=55).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(f, text="Examinar...", command=self._browse_sub).pack(side=tk.LEFT)

        # ── Carpeta salida ──
        ttk.Label(main_frame, text="Carpeta de salida (PDFs):").grid(
            row=4, column=0, sticky=tk.W, pady=(0, 2)
        )
        self.out_path = tk.StringVar(value="output/pdfs")
        f = ttk.Frame(main_frame)
        f.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=(0, 5))
        ttk.Entry(f, textvariable=self.out_path, width=55).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(f, text="Examinar...", command=self._browse_out).pack(side=tk.LEFT)

        # ── Separador ──
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=6, column=0, columnspan=2, sticky=tk.EW, pady=12
        )

        # ── Filtro de fecha ──
        self.filtrar_fecha = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            main_frame,
            text="Filtrar por fecha",
            variable=self.filtrar_fecha,
            command=self._toggle_fecha,
        ).grid(row=7, column=0, sticky=tk.W)

        fecha_frame = ttk.Frame(main_frame)
        fecha_frame.grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        ttk.Label(fecha_frame, text="Desde:").pack(side=tk.LEFT)
        self.fecha_desde = tk.StringVar()
        self._entry_desde = ttk.Entry(fecha_frame, textvariable=self.fecha_desde,
                                       width=14, state="readonly")
        self._entry_desde.pack(side=tk.LEFT, padx=(5, 2))
        self._entry_desde.bind("<Button-1>", lambda e: self._abrir_calendario("desde"))
        self._btn_desde = ttk.Button(fecha_frame, text="\U0001F4C5", width=3,
                                      command=lambda: self._abrir_calendario("desde"))
        self._btn_desde.pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(fecha_frame, text="Hasta:").pack(side=tk.LEFT)
        self.fecha_hasta = tk.StringVar()
        self._entry_hasta = ttk.Entry(fecha_frame, textvariable=self.fecha_hasta,
                                       width=14, state="readonly")
        self._entry_hasta.pack(side=tk.LEFT, padx=(5, 2))
        self._entry_hasta.bind("<Button-1>", lambda e: self._abrir_calendario("hasta"))
        self._btn_hasta = ttk.Button(fecha_frame, text="\U0001F4C5", width=3,
                                      command=lambda: self._abrir_calendario("hasta"))
        self._btn_hasta.pack(side=tk.LEFT)
        self._desactivar_fechas()

        # ── Separador ──
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=9, column=0, columnspan=2, sticky=tk.EW, pady=12
        )

        # ── Opciones ──
        self.include_empty = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            main_frame,
            text="Incluir campos vac\u00edos en el PDF",
            variable=self.include_empty,
        ).grid(row=10, column=0, sticky=tk.W)

        self.export_zip = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            main_frame,
            text="Exportar a ZIP al finalizar",
            variable=self.export_zip,
        ).grid(row=11, column=0, sticky=tk.W)

        workers_frame = ttk.Frame(main_frame)
        workers_frame.grid(row=12, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Label(workers_frame, text="Workers: 1 (secuencial)").pack(side=tk.LEFT)

        # ── Progreso total ──
        self.progress = ttk.Progressbar(
            main_frame, mode="determinate", length=600
        )
        self.progress.grid(row=13, column=0, columnspan=2, pady=(20, 5))

        self.lbl_status = ttk.Label(main_frame, text="Listo para generar")
        self.lbl_status.grid(row=14, column=0, columnspan=2, sticky=tk.W)

        # ── Botones ──
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=15, column=0, columnspan=2, pady=(15, 0))
        self.btn_generar = ttk.Button(
            btn_frame, text="  GENERAR  ", command=self._iniciar_generacion
        )
        self.btn_generar.pack(side=tk.LEFT, padx=(0, 10))
        self.btn_cancelar = ttk.Button(
            btn_frame, text=" CANCELAR ", command=self._cancelar, state="disabled"
        )
        self.btn_cancelar.pack(side=tk.LEFT)

    # ── Selectores de carpeta ─────────────────────────────────────

    def _browse_main(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta principal")
        if path:
            self.main_path.set(path)

    def _browse_sub(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta de subformularios")
        if path:
            self.sub_path.set(path)

    def _browse_out(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if path:
            self.out_path.set(path)

    # ── Filtro de fecha ───────────────────────────────────────────

    @staticmethod
    def _fmt_fecha(d):
        return f"{d.day:02d}-{MESES_LISTA[d.month - 1]}-{d.year}"

    def _toggle_fecha(self):
        if self.filtrar_fecha.get():
            self._cargar_fechas()
        else:
            self._desactivar_fechas()

    def _abrir_calendario(self, campo):
        CalendarPopup(self.root, lambda d: self._set_fecha(campo, d))

    def _set_fecha(self, campo, date_obj):
        var = self.fecha_desde if campo == "desde" else self.fecha_hasta
        var.set(self._fmt_fecha(date_obj))
        if campo == "desde":
            self._fecha_desde_date = date_obj
        else:
            self._fecha_hasta_date = date_obj

    def _activar_fechas(self):
        for w in self._fecha_widgets():
            w.configure(state="readonly" if isinstance(w, ttk.Entry) else "normal")

    def _desactivar_fechas(self):
        for w in self._fecha_widgets():
            w.configure(state="disabled")
        self.fecha_desde.set("")
        self.fecha_hasta.set("")
        self._fecha_desde_date = None
        self._fecha_hasta_date = None

    def _fecha_widgets(self):
        return [self._entry_desde, self._btn_desde, self._entry_hasta, self._btn_hasta]

    def _cargar_fechas(self):
        try:
            main_path = self.main_path.get()
            if not os.path.isdir(main_path):
                return
            df = read_and_concat_csvs(main_path)
            if "Date" not in df.columns:
                messagebox.showwarning("Advertencia",
                    "El CSV principal no tiene una columna 'Date'")
                return
            fechas = df["Date"].dropna().apply(parsear_fecha).dropna()
            if len(fechas) == 0:
                messagebox.showinfo("Sin fechas",
                    "No se encontraron fechas validas en la columna 'Date'")
                return
            self.fecha_min = fechas.min()
            self.fecha_max = fechas.max()
            self._set_fecha("desde", self.fecha_min)
            self._set_fecha("hasta", self.fecha_max)
            self._activar_fechas()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las fechas:\n{e}")

    # ── Generación ────────────────────────────────────────────────

    def _iniciar_generacion(self):
        if self.procesando:
            return

        main_path = self.main_path.get()
        sub_path = self.sub_path.get()
        out_path = self.out_path.get()

        if not os.path.isdir(main_path):
            messagebox.showerror("Error", f"No existe la carpeta:\n{main_path}")
            return
        if not os.path.isdir(sub_path):
            messagebox.showerror("Error", f"No existe la carpeta:\n{sub_path}")
            return

        csv_main = [f for f in os.listdir(main_path) if f.lower().endswith(".csv")]
        csv_sub = [f for f in os.listdir(sub_path) if f.lower().endswith(".csv")]
        if not csv_main:
            messagebox.showerror("Error", f"No hay CSVs en:\n{main_path}")
            return
        if not csv_sub:
            messagebox.showerror("Error", f"No hay CSVs en:\n{sub_path}")
            return

        os.makedirs(out_path, exist_ok=True)

        self.procesando = True
        self.btn_generar.config(state="disabled")
        self.btn_cancelar.config(state="normal")
        self.lbl_status.config(text="Iniciando...")
        self.progress["value"] = 0

        thread = threading.Thread(target=self._ejecutar_generacion, daemon=True)
        thread.start()

    def _cancelar(self):
        if self.procesando:
            self.procesando = False
            self.lbl_status.config(text="Cancelando...")

    def _ejecutar_generacion(self):
        start_time = time.time()
        generated = 0
        failed = 0

        try:
            main_path = self.main_path.get()
            sub_path = self.sub_path.get()
            out_path = self.out_path.get()
            include_empty = self.include_empty.get()
            export_zip = self.export_zip.get()

            self._actualizar_status("Leyendo archivos CSV...")
            main_df = read_and_concat_csvs(main_path)
            sub_df = read_and_concat_csvs(sub_path)

            if "Record Link ID" not in main_df.columns or "Record Link ID" not in sub_df.columns:
                raise RuntimeError("Columna 'Record Link ID' no encontrada en ambos CSVs")

            if self.filtrar_fecha.get():
                desde = self._fecha_desde_date
                hasta = self._fecha_hasta_date
                if desde and hasta:
                    self._actualizar_status(
                        f"Aplicando filtro de fecha: {self._fmt_fecha(desde)} \u2192 {self._fmt_fecha(hasta)}"
                    )
                    main_df["_date"] = main_df["Date"].apply(parsear_fecha)
                    mask = (
                        main_df["_date"].notna()
                        & (main_df["_date"] >= desde)
                        & (main_df["_date"] <= hasta)
                    )
                    main_df = main_df[mask].drop(columns=["_date"])

            self._actualizar_status("Indexando subregistros...")
            sub_groups = dict(tuple(sub_df.groupby("Record Link ID", sort=False)))

            total = len(main_df)
            if total == 0:
                raise RuntimeError(
                    "No hay registros para procesar con los filtros actuales"
                )

            self._actualizar_status(f"Generando {total} PDFs...")
            self.progress["maximum"] = total

            label_cache_clear()
            used_names = set()
            for idx, (_, row) in enumerate(main_df.iterrows()):
                if not self.procesando:
                    break
                rid = safe_text(row.get("Record Link ID", "")).strip()
                if rid == "":
                    self.progress["value"] = idx + 1
                    self.root.update_idletasks()
                    continue
                dui = safe_text(row.get(DUI_COL, "")).strip()
                base = dui if dui != "" else rid
                filename = sanitize_filename(f"{base}.pdf")
                filepath = os.path.join(out_path, filename)
                if filename in used_names or os.path.exists(filepath):
                    filename = sanitize_filename(f"{base}-{rid}.pdf")
                    filepath = os.path.join(out_path, filename)
                used_names.add(filename)
                try:
                    sub_rows = sub_groups.get(rid)
                    make_pdf_for_record(row, sub_rows, filepath, include_empty)
                    generated += 1
                except Exception:
                    failed += 1
                self.progress["value"] = idx + 1
                self.lbl_status.config(text=f"Generando {idx + 1}/{total}...")
                self.root.update_idletasks()

            if export_zip and generated > 0:
                self._actualizar_status("Creando ZIP...")
                zip_path = os.path.join(out_path, "subsidios_pdfs.zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for pdf_path in Path(out_path).glob("*.pdf"):
                        if pdf_path.name == "subsidios_pdfs.zip":
                            continue
                        zf.write(str(pdf_path), pdf_path.name)

            for f in os.listdir(out_path):
                fp = os.path.join(out_path, f)
                if os.path.isfile(fp) and os.path.getsize(fp) == 0:
                    try:
                        os.unlink(fp)
                    except Exception:
                        pass

        except Exception as e:
            self._actualizar_status(f"ERROR: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            elapsed = time.time() - start_time
            self.procesando = False
            self.btn_generar.config(state="normal")
            self.btn_cancelar.config(state="disabled")

            msg = f"Generados: {generated}  |  Fallidos: {failed}"
            if elapsed < 60:
                msg += f"  |  Tiempo: {elapsed:.1f} seg"
            else:
                m = int(elapsed // 60)
                s = elapsed % 60
                msg += f"  |  Tiempo: {m} min {s:.1f} seg"

            self.lbl_status.config(text=msg)
            self.progress["value"] = 0
            messagebox.showinfo("Completado", f"Proceso finalizado.\n\n{msg}")

    def _actualizar_status(self, msg):
        self.lbl_status.config(text=msg)
        self.root.update_idletasks()


if __name__ == "__main__":
    import multiprocessing as mp
    mp.freeze_support()
    root = tk.Tk()
    app = GeneradorPDFsApp(root)
    root.mainloop()
