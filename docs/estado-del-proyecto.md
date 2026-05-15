# Estado del proyecto — subsidio-reportes-pdf

---

## Resumen

Aplicacion en Python que genera PDFs a partir de archivos CSV de formularios de subsidio GLP. Soporta formulario principal + subformularios (SubForm4), procesamiento secuencial, filtros, y exportacion a ZIP.

---

## Estado actual (Mayo 2026)

### Componentes existentes

| Componente | Archivo | Estado |
|---|---|---|
| Motor de generacion de PDFs | `generate_pdfs.py` | ✅ Estable |
| Script de doble clic | `run.ps1` | ✅ Estable |
| Interfaz grafica (tkinter) | `gui_app.py` | ✅ Estable |
| Empaquetado a .exe | `build_exe.bat` | ✅ Listo |
| Tests | `tests/test_generate_pdfs.py` | ✅ 24 tests pasando |
| Plan de implementacion | `docs/superpowers/plans/2026-05-15-gui-exe-filtro-fecha.md` | ✅ Completado |
| Filosofia de diseno | `docs/diseno-filosofia.md` | ✅ Documentado |
| Mejoras futuras | `docs/mejoras-futuras.md` | ✅ Documentado |

### Capacidades actuales

- Lectura de multiples CSVs desde carpetas (`input/main/`, `input/sub/`)
- Union de formularios por columna `Record Link ID`
- Generacion de PDFs con diseno institucional (tipografia WorkSans, paleta azul/dorado)
- Filtro por fecha con calendario popup nativo (formato `dd-mmm-aaaa`)
- Filtro por DUI
- Opcion de incluir campos vacios
- Exportacion a ZIP
- Barra de progreso en tiempo real
- Numeracion de paginas, header/footer automaticos
- Validacion de archivos de entrada antes de procesar

### Modos de ejecucion

| Modo | Como se ejecuta | Usuario objetivo |
|---|---|---|
| CLI directo | `python generate_pdfs.py --main ... --sub ... --out ...` | Tecnico |
| Script run.ps1 | Doble clic en `run.ps1` | Usuario final con Python |
| GUI grafica | `python gui_app.py` o `dist/GenerarPDFs.exe` | Usuario final sin conocimientos tecnicos |

---

## Impases encontrados

### 1. Ejecucion de `.ps1` con doble clic

**Problema:** Windows no ejecuta `.ps1` al hacer doble clic, lo abre en un editor de texto.

**Solucion actual:** El usuario debe hacer clic derecho → "Ejecutar con PowerShell". Para una experiencia verdaderamente de un clic, se necesita un `.bat` wrapper o empaquetar a `.exe`.

**Estado:** No resuelto del todo. El `.exe` portatil resuelve esto definitivamente.

### 2. Locale de fechas con `pd.to_datetime`

**Problema:** `pd.to_datetime(..., format="%d-%b-%Y")` depende del locale del sistema operativo. En algunas configuraciones de Windows, `%b` no reconoce meses en espanol (`abr`, `sep`, etc.), lanzando:
```
time data "30-abr-2026" doesn't match format "%d-%b-%Y"
```

**Solucion:** Se creo un parser manual `parsear_fecha()` con mapeo `MESES = {"ene":1, "feb":2, ..., "dic":12}`, eliminando toda dependencia del locale del sistema. Las comparaciones de fecha se hacen con objetos `datetime.date` directamente, sin pasar por `pd.to_datetime`.

**Estado:** Resuelto.

### 3. Selector de fecha tipo Combobox

**Problema:** El filtro de fecha usaba `ttk.Combobox` con valores predefinidos del CSV, pero no permitia seleccion visual de fechas (no hay un date picker nativo en tkinter).

**Solucion:** Se reemplazo por `ttk.Entry` de solo lectura con un boton `📅` que abre un calendario popup 100% tkinter (sin dependencias externas). El calendario permite navegar meses con ◀ ▶, seleccionar un dia, o ir al dia de hoy.

**Estado:** Resuelto.

### 4. Paralelismo con multiprocessing

**Problema:** Se intento implementar workers paralelos (>1) en la GUI usando `multiprocessing.Pool`. Sin embargo:
- La barra de progreso saltaba en bloques grandes (cada salto = un worker completo terminaba su lote)
- Requeria modificar `generate_pdfs.py` (agregar `progress_queue` opcional)
- La complejidad no justificaba el beneficio para el usuario final

**Solucion:** Se simplifico a solo modo secuencial (workers=1). El paralelismo sigue disponible via CLI (`generate_pdfs.py --workers N`) para usuarios tecnicos que necesiten procesar lotes grandes rapidamente.

**Estado:** Paralelismo eliminado de la GUI, disponible solo en CLI.

### 5. Pickle de lambda en multiprocessing

**Problema:** Al usar `pool.apply_async(lambda a: process_chunk(*a), ...)`, Python no puede serializar (pickle) funciones lambda para enviarlas a los procesos hijos en Windows.

**Solucion:** Usar siempre funciones definidas a nivel de modulo (`_process_chunk_wrapper`) que si son picklables.

**Estado:** Resuelto (aunque el paralelismo ya no se usa en la GUI).

### 6. Empaquetado con PyInstaller y dependencias offline

**Problema:** El script `build_exe.bat` originalmente instalaba PyInstaller si no estaba presente, requiriendo conexion a internet en cada build.

**Solucion:** Se agrego `pyinstaller` a `requirements.txt`, instalando una sola vez junto con las demas dependencias. El `build_exe.bat` ahora solo verifica que este presente y aborta con mensaje claro si no.

**Estado:** Resuelto.

---

## Futuro del proyecto

### Corto plazo

- [ ] **Ejecutable `.exe` portable** — Ejecutar `build_exe.bat` para generar `dist/GenerarPDFs.exe`. Un solo archivo que funciona sin Python ni dependencias. Ideal para distribucion a usuarios finales.
- [ ] **Pruebas en maquina limpia** — Probar el `.exe` en una computadora sin Python para verificar que todo funciona.

### Mediano plazo

- [ ] **Rediseno del PDF** — Ajustar el diseno visual de los PDFs usando la filosofia documentada en `docs/diseno-filosofia.md`.
- [ ] **Validador de CSVs previo** — Antes de procesar, verificar columnas esperadas, encoding, duplicados, filas vacias. Esto evitaria frustraciones tras minutos de procesamiento.
- [ ] **Informe HTML de resultado** — Al finalizar, generar un `.html` con resumen visual: cantidad de PDFs, fallos, tiempo, lista de archivos, enlace al ZIP.

### Largo plazo

- [ ] **Soporte para mas subformularios** — Actualmente solo maneja SubForm4. Ampliar a otros tipos de subformularios.
- [ ] **Interfaz web local** — Servidor Flask con drag & drop de CSVs, barra de progreso en navegador, descarga de ZIP.
- [ ] **Modo "watch"** — Monitorear la carpeta `input/` y procesar automaticamente cuando aparezcan nuevos CSVs.

### Decisiones arquitectonicas pendientes

- **GUI vs Web:** La GUI tkinter actual funciona y es suficiente. Para una experiencia mas moderna, una interfaz web (Flask) ofreceria mejor UX, pero requiere mas mantenimiento y dependencias.
- **Un solo .exe vs instalador:** `--onefile` genera un solo archivo portable pero mas lento al iniciar. `--onedir` + instalador (InnoSetup/InstallForge) ofrece mejor experiencia de instalacion.
- **Soporte a otros formatos:** Actualmente solo CSV. Podria ampliarse a Excel (`.xlsx`) usando `openpyxl` o `xlrd`.

---

## Documentacion relacionada

| Documento | Contenido |
|---|---|
| `docs/uso-cli.md` | Uso del script por linea de comandos |
| `docs/uso-run-script.md` | Uso del script de doble clic `run.ps1` |
| `docs/uso-gui.md` | Uso de la interfaz grafica `gui_app.py` |
| `docs/diseno-filosofia.md` | Filosofia de diseno de los PDFs |
| `docs/mejoras-futuras.md` | Catalogo de mejoras propuestas |
| `docs/superpowers/plans/2026-05-15-gui-exe-filtro-fecha.md` | Plan de implementacion |
