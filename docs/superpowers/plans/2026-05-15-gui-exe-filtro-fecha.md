# GUI + .exe + Filtro Fecha Implementation Plan

> **For agentic workers:** Use executing-plans to implement this plan task-by-task.

**Goal:** Crear una interfaz gráfica de escritorio (tkinter) que envuelve `generate_pdfs.py`, añade filtro por fecha, y se empaqueta como `.exe` portable.

**Architecture:** `gui_app.py` es una aplicación tkinter que importa funciones de `generate_pdfs.py` (sin duplicar lógica). Añade una capa de filtrado por fecha sobre la columna `Date` del CSV principal antes de llamar al motor de generación. El empaquetado con PyInstaller produce un solo `.exe`.

**Tech Stack:** Python 3.14+, tkinter (stdlib), pandas, reportlab, tqdm, PyInstaller

**Files:**
- Create: `gui_app.py` (~350 lines) — Interfaz gráfica completa
- Modify: `generate_pdfs.py` (+4 lines) — Agregar `multiprocessing.freeze_support()`
- Create: `build_exe.bat` (~10 lines) — Script para empaquetar
- Create: `docs/superpowers/plans/2026-05-15-gui-exe-filtro-fecha.md` — Este plan

---

### Task 1: Agregar `freeze_support()` a `generate_pdfs.py`

**Files:**
- Modify: `generate_pdfs.py:361` (dentro de `main()`)

- [ ] **Step 1: Agregar import y freeze_support al inicio de main()**

En `generate_pdfs.py`, justo después del docstring de `main()` y antes de cargar config, agregar:

```python
def main():
    import multiprocessing as mp
    mp.freeze_support()
    start_time = time.time()
    ...
```

Esto permite que el .exe generado por PyInstaller funcione correctamente en Windows con multiprocessing.

- [ ] **Step 2: Verificar que el script sigue funcionando**

Ejecutar:
```bash
python generate_pdfs.py --limit 5
```
Expected: genera 5 PDFs sin errores.

---

### Task 2: Crear `gui_app.py` — Interfaz gráfica tkinter

**Files:**
- Create: `gui_app.py` — Interfaz completa

- [ ] **Step 1: Estructura base de la ventana**

```python
#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
import datetime
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

class GeneradorPDFsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de PDFs - Subsidio GLP")
        self.root.geometry("700x650")
        self.root.resizable(False, False)
        self.procesando = False
        self._build_widgets()

    def _build_widgets(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── Carpeta principal ──
        ttk.Label(main_frame, text="Carpeta principal (CSVs):").grid(row=0, column=0, sticky=tk.W, pady=(0,2))
        self.main_path = tk.StringVar(value="input/main")
        ttk.Entry(main_frame, textvariable=self.main_path, width=60).grid(row=1, column=0, padx=(0,5))
        ttk.Button(main_frame, text="Examinar...", command=self._browse_main).grid(row=1, column=1)

        # ── Carpeta sub ──
        ttk.Label(main_frame, text="Carpeta subformularios (CSVs):").grid(row=2, column=0, sticky=tk.W, pady=(10,2))
        self.sub_path = tk.StringVar(value="input/sub")
        ttk.Entry(main_frame, textvariable=self.sub_path, width=60).grid(row=3, column=0, padx=(0,5))
        ttk.Button(main_frame, text="Examinar...", command=self._browse_sub).grid(row=3, column=1)

        # ── Carpeta salida ──
        ttk.Label(main_frame, text="Carpeta de salida (PDFs):").grid(row=4, column=0, sticky=tk.W, pady=(10,2))
        self.out_path = tk.StringVar(value="output/pdfs")
        ttk.Entry(main_frame, textvariable=self.out_path, width=60).grid(row=5, column=0, padx=(0,5))
        ttk.Button(main_frame, text="Examinar...", command=self._browse_out).grid(row=5, column=1)

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

if __name__ == "__main__":
    root = tk.Tk()
    app = GeneradorPDFsApp(root)
    root.mainloop()
```

- [ ] **Step 2: Agregar sección de filtro de fecha**

Después de la carpeta de salida (entre step 5 y step 6 del grid), agregar:

```python
        # ── Separador ──
        ttk.Separator(main_frame, orient='horizontal').grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=15)

        # ── Filtro de fecha ──
        self.filtrar_fecha = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Filtrar por fecha", variable=self.filtrar_fecha,
                        command=self._toggle_fecha).grid(row=7, column=0, sticky=tk.W)

        fecha_frame = ttk.Frame(main_frame)
        fecha_frame.grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=(5,0))
        ttk.Label(fecha_frame, text="Desde:").pack(side=tk.LEFT)
        self.fecha_desde = ttk.Combobox(fecha_frame, width=15, state="readonly")
        self.fecha_desde.pack(side=tk.LEFT, padx=(5,15))
        ttk.Label(fecha_frame, text="Hasta:").pack(side=tk.LEFT)
        self.fecha_hasta = ttk.Combobox(fecha_frame, width=15, state="readonly")
        self.fecha_hasta.pack(side=tk.LEFT, padx=(5,0))
        self._desactivar_fechas()

        # ── Separador ──
        ttk.Separator(main_frame, orient='horizontal').grid(row=9, column=0, columnspan=2, sticky=tk.EW, pady=15)
```

Y agregar los métodos:

```python
    def _toggle_fecha(self):
        if self.filtrar_fecha.get():
            self._cargar_fechas()
            self._activar_fechas()
        else:
            self._desactivar_fechas()

    def _activar_fechas(self):
        self.fecha_desde.config(state="readonly")
        self.fecha_hasta.config(state="readonly")

    def _desactivar_fechas(self):
        self.fecha_desde.config(state="disabled")
        self.fecha_hasta.config(state="disabled")
        self.fecha_desde.set("")
        self.fecha_hasta.set("")

    def _cargar_fechas(self):
        try:
            main_path = self.main_path.get()
            if not os.path.isdir(main_path):
                return
            df = read_and_concat_csvs(main_path)
            dates = pd.to_datetime(df["Date"], format="%d-%b-%Y", errors="coerce")
            valid = dates.dropna()
            if len(valid) == 0:
                return
            fechas = sorted(valid.dt.strftime("%d-%b-%Y").unique())
            self.fecha_desde["values"] = fechas
            self.fecha_hasta["values"] = fechas
            self.fecha_desde.set(fechas[0])
            self.fecha_hasta.set(fechas[-1])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las fechas:\n{e}")
```

- [ ] **Step 3: Agregar opciones (include_empty, zip, workers)**

Después del separador (row 9), agregar:

```python
        # ── Opciones ──
        self.include_empty = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Incluir campos vacíos en el PDF",
                        variable=self.include_empty).grid(row=10, column=0, sticky=tk.W)

        self.export_zip = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Exportar a ZIP al finalizar",
                        variable=self.export_zip).grid(row=11, column=0, sticky=tk.W)

        workers_frame = ttk.Frame(main_frame)
        workers_frame.grid(row=12, column=0, sticky=tk.W, pady=(5,0))
        ttk.Label(workers_frame, text="Workers (paralelismo):").pack(side=tk.LEFT)
        self.workers = tk.IntVar(value=1)
        ttk.Spinbox(workers_frame, from_=1, to=8, textvariable=self.workers,
                    width=5).pack(side=tk.LEFT, padx=(5,0))
```

- [ ] **Step 4: Agregar barra de progreso y botones**

Después de workers:

```python
        # ── Progreso ──
        self.progress = ttk.Progressbar(main_frame, mode="determinate", length=550)
        self.progress.grid(row=13, column=0, columnspan=2, pady=(20,5))

        self.lbl_status = ttk.Label(main_frame, text="Listo para generar")
        self.lbl_status.grid(row=14, column=0, columnspan=2, sticky=tk.W)

        # ── Botones ──
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=15, column=0, columnspan=2, pady=(15,0))
        self.btn_generar = ttk.Button(btn_frame, text="  GENERAR  ", command=self._iniciar_generacion)
        self.btn_generar.pack(side=tk.LEFT, padx=(0,10))
        self.btn_cancelar = ttk.Button(btn_frame, text=" CANCELAR ", command=self._cancelar, state="disabled")
        self.btn_cancelar.pack(side=tk.LEFT)
```

- [ ] **Step 5: Implementar lógica de generación**

Agregar los métodos principales:

```python
    def _iniciar_generacion(self):
        if self.procesando:
            return

        main_path = self.main_path.get()
        sub_path = self.sub_path.get()
        out_path = self.out_path.get()

        # Validaciones
        if not os.path.isdir(main_path):
            messagebox.showerror("Error", f"No existe la carpeta:\n{main_path}")
            return
        if not os.path.isdir(sub_path):
            messagebox.showerror("Error", f"No existe la carpeta:\n{sub_path}")
            return

        csv_main = [f for f in os.listdir(main_path) if f.lower().endswith('.csv')]
        csv_sub = [f for f in os.listdir(sub_path) if f.lower().endswith('.csv')]
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
```

Método principal de generación:

```python
    def _ejecutar_generacion(self):
        import time
        import zipfile
        from pathlib import Path
        from tqdm import tqdm

        start_time = time.time()
        generated = 0
        failed = 0

        try:
            main_path = self.main_path.get()
            sub_path = self.sub_path.get()
            out_path = self.out_path.get()
            include_empty = self.include_empty.get()
            export_zip = self.export_zip.get()
            n_workers = self.workers.get()

            self._actualizar_status("Leyendo archivos CSV...")
            main_df = read_and_concat_csvs(main_path)
            sub_df = read_and_concat_csvs(sub_path)

            if "Record Link ID" not in main_df.columns or "Record Link ID" not in sub_df.columns:
                raise RuntimeError("Columna 'Record Link ID' no encontrada en ambos CSVs")

            # Filtro por fecha
            if self.filtrar_fecha.get():
                desde = self.fecha_desde.get()
                hasta = self.fecha_hasta.get()
                if desde and hasta:
                    self._actualizar_status(f"Aplicando filtro de fecha: {desde} → {hasta}")
                    main_df["_date"] = pd.to_datetime(main_df["Date"], format="%d-%b-%Y", errors="coerce")
                    mask = (main_df["_date"] >= pd.to_datetime(desde, format="%d-%b-%Y")) & \
                           (main_df["_date"] <= pd.to_datetime(hasta, format="%d-%b-%Y"))
                    main_df = main_df[mask].drop(columns=["_date"])

            self._actualizar_status("Indexando subregistros...")
            sub_groups = dict(tuple(sub_df.groupby("Record Link ID", sort=False)))

            total = len(main_df)
            if total == 0:
                raise RuntimeError("No hay registros para procesar con los filtros actuales")

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
                self.lbl_status.config(text=f"Generando {idx+1}/{total}...")
                self.root.update_idletasks()

            # ZIP
            if export_zip and generated > 0:
                self._actualizar_status("Creando ZIP...")
                zip_path = os.path.join(out_path, "subsidios_pdfs.zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for pdf_path in Path(out_path).glob("*.pdf"):
                        if pdf_path.name == "subsidios_pdfs.zip":
                            continue
                        zf.write(str(pdf_path), pdf_path.name)

            # Limpiar placeholders
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
                msg += f"  |  Tiempo: {int(elapsed//60)} min {elapsed%60:.1f} seg"

            self.lbl_status.config(text=msg)
            self.progress["value"] = 0
            messagebox.showinfo("Completado", f"Proceso finalizado.\n\n{msg}")

    def _actualizar_status(self, msg):
        self.lbl_status.config(text=msg)
        self.root.update_idletasks()
```

- [ ] **Step 6: Verificar que gui_app.py arranca sin errores**

```bash
python gui_app.py
```
Expected: Ventana tkinter visible con todos los campos.

---

### Task 3: Crear `build_exe.bat`

**Files:**
- Create: `build_exe.bat`

- [ ] **Step 1: Crear script de empaquetado**

```batch
@echo off
REM build_exe.bat — Empaqueta gui_app.py como .exe portable
REM Requiere: pip install pyinstaller

echo ============================================
echo  Empaquetando Generador de PDFs...
echo ============================================
echo.

REM Activar entorno virtual si existe
if exist ".venv\Scripts\Activate.bat" (
    call .venv\Scripts\Activate.bat
)

REM Verificar pyinstaller
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

REM Limpiar builds anteriores
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

REM Empaquetar
echo.
echo Ejecutando PyInstaller...
pyinstaller --onefile --windowed --name "GenerarPDFs" ^
    --add-data ".agents\skills\canvas-design\canvas-fonts;canvas-fonts" ^
    --hidden-import tkinter ^
    --hidden-import tkinter.filedialog ^
    --hidden-import tkinter.messagebox ^
    --hidden-import pandas ^
    --hidden-import reportlab ^
    gui_app.py

echo.
if exist "dist\GenerarPDFs.exe" (
    echo ============================================
    echo  LISTO: dist\GenerarPDFs.exe
    echo ============================================
) else (
    echo ERROR: No se genero el ejecutable.
)

pause
```

- [ ] **Step 2: Verificar comando de PyInstaller**

```bash
pip install pyinstaller
```
Expected: PyInstaller instalado sin errores.

---

### Task 4: Verificación final

**Files:**
- Test: Ejecución completa

- [ ] **Step 1: Ejecutar tests existentes**

```bash
cd tests && pytest test_generate_pdfs.py -v && cd ..
```
Expected: 15 tests PASS (sin regresiones).

- [ ] **Step 2: Probar GUI manualmente con --limit 5**

Abrir `gui_app.py`, configurar rutas, marcar filtro de fecha, generar 5 PDFs de prueba.

- [ ] **Step 3: Commit final**

```bash
git add -A
git commit -m "feat: gui tkinter + filtro fecha + empaquetado .exe"
```
