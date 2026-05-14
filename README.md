# subsidio-reportes-pdf

Aplicativo en **Python** para generar **PDFs** a partir de archivos **CSV** de formularios y subformularios, con soporte para multiples archivos, procesamiento en paralelo y exportacion final a ZIP.

---

## Requisitos tecnicos

- Python 3.9+ (recomendado 3.10+)
- Instalar dependencias:

  ```bash
  pip install -r requirements.txt
  ```

  > **NOTA:** Si usas entorno virtual (`.venv`), activalo primero:
  > ```bash
  > .\.venv\Scripts\Activate.ps1   # Windows
  > pip install -r requirements.txt
  > ```

---

## Estructura de carpetas

```
subsidio-reportes-pdf/
  config.json            # Configuracion predeterminada (rutas, workers, etc.)
  generate_pdfs.py       # Script principal
  requirements.txt       # Dependencias del proyecto
  input/
    main/                # CSVs del formulario principal
    sub/                 # CSVs de subformularios (ej: SubForm4)
  output/
    pdfs/                # PDFs generados
```

Coloca los archivos CSV del formulario principal en `input/main/` y los de subformularios en `input/sub/`.

---

## Como se usa

### 1. Usando config.json (recomendado)

El archivo `config.json` ya tiene las rutas por defecto (`input/main`, `input/sub`, `output/pdfs`). Solo ejecuta:

```bash
python generate_pdfs.py
```

### 2. Especificando todo manualmente

Si prefieres (o si no tienes `config.json`):

```bash
python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs
```

### 3. Con opciones extra

```bash
# Solo los primeros 200 registros
python generate_pdfs.py --limit 200

# Filtrar por DUI (uno o varios, separados por coma)
python generate_pdfs.py --only "06784334-6,03934980-5"

# Incluir campos vacios en el PDF
python generate_pdfs.py --include-empty

# Exportar a ZIP al finalizar
python generate_pdfs.py --zip

# Procesar en paralelo (acelera lotes grandes)
python generate_pdfs.py --workers 4

# Combinar todo
python generate_pdfs.py --limit 500 --workers 4 --zip
```

> **Importante:** Los argumentos por CLI tienen prioridad sobre `config.json`.
> Si pasas `--out output/otro`, se usa ese directorio, no el de `config.json`.

---

## Tabla de opciones

| Argumento | Descripcion | Valor por defecto |
|---|---|---|
| `--main` | Carpeta o archivo CSV del formulario principal | `config.json` → `paths.main` |
| `--sub` | Carpeta o archivo CSV del subformulario | `config.json` → `paths.sub` |
| `--out` | Carpeta de salida para PDFs | `config.json` → `paths.out` |
| `--limit N` | Procesar solo los primeros N registros (0 = todos) | `config.json` → `options.limit` (0) |
| `--only "DUI1,DUI2"` | Filtrar por DUI (varios separados por coma) | vacio (sin filtro) |
| `--include-empty` | Incluir campos vacios en el PDF | off |
| `--zip` | Crear un ZIP con todos los PDFs al finalizar | off |
| `--workers N` | Trabajadores en paralelo (1 = secuencial) | `config.json` → `options.workers` (1) |

---

## Workers en paralelo

Para lotes grandes (1000+ registros), usar `--workers N` divide el trabajo en N procesos paralelos:

```bash
python generate_pdfs.py --workers 4
```

**Estimacion de tiempo** para ~53.000 registros:

| Workers | Tiempo estimado |
|---|---|
| 1 (secuencial) | ~45 min |
| 4 | ~12 min |
| 8 | ~7 min |

> **En Windows:** Cada worker arranca un proceso Python independiente (~5 segundos de overhead).
> Para lotes chicos o pruebas, `--workers 1` es mas rapido.
> El modo secuencial (default) ya tiene barra de progreso con `tqdm`.

---

## Archivo de configuracion (`config.json`)

Sirve para evitar escribir los mismos argumentos en cada ejecucion.

### Ubicacion

Debe estar en la raiz del proyecto (junto a `generate_pdfs.py`).

### Contenido

```json
{
  "paths": {
    "main": "input/main",
    "sub": "input/sub",
    "out": "output/pdfs"
  },
  "options": {
    "workers": 1,
    "limit": 0
  }
}
```

### Como funciona

1. El script busca `config.json` al arrancar.
2. Si existe, usa sus valores como **predeterminados** para `--main`, `--sub`, `--out`, `--workers` y `--limit`.
3. Si ademas pasas argumentos por CLI, **los argumentos tienen prioridad** sobre `config.json`.
4. Si no existe `config.json`, los argumentos `--main`, `--sub` y `--out` son obligatorios.

### Ejemplos practicos

```bash
# Situacion 1: config.json existe con las rutas correctas
# Comando:
python generate_pdfs.py --limit 100
# Efecto: usa paths de config.json, pero solo procesa 100 registros

# Situacion 2: config.json no existe
# Comando:
python generate_pdfs.py
# Error: --main, --sub, --out son obligatorios

# Situacion 3: quieres una salida diferente por una vez
# Comando:
python generate_pdfs.py --out output/prueba --limit 10
# Efecto: sobreescribe solo --out, el resto viene de config.json
```

---

## Detalles tecnicos

- El script detecta si `--main` o `--sub` es una carpeta y concatena automaticamente todos los CSV encontrados.
- La union entre formularios se realiza por la columna **`Record Link ID`**.
- El nombre del PDF se genera usando el campo **`01. Numero de Documento Unico de Identidad (DUI)`**. Si esta vacio, usa el `Record Link ID`.
- Si hay colisiones de nombre (mismo DUI en varios registros), se agrega el `Record Link ID` para evitar sobreescritura.
- Los CSV se leen como texto (`dtype=str`) para no perder ceros a la izquierda.
- Procesamiento en paralelo via `multiprocessing` con `imap_unordered` y barra de progreso.
- El ZIP se genera **dentro** de la carpeta `--out/`, no en el directorio padre.
- `config.json` usa `json` (libreria estandar de Python, sin dependencias extra).

---

## Tests

```bash
pip install pytest
pytest tests/
```

## Errores comunes

| Error | Causa | Solucion |
|---|---|---|
| `--main, --sub, --out are required` | Falta `config.json` o no se pasaron rutas | Crear `config.json` o pasar `--main`, `--sub`, `--out` |
| `No CSV files found in folder` | La carpeta no tiene archivos `.csv` | Verificar que los CSV esten en la carpeta indicada |
| `Column 'Record Link ID' not found` | El CSV no tiene esa columna | Verificar que los archivos sean los correctos |
| `pip install` falla con "Unable to create process" | El `.venv` tiene la ruta rota | Recrear el entorno virtual (ver seccion Requisitos) |
