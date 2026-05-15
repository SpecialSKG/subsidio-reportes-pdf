# Uso por CLI — `generate_pdfs.py`

Ejecucion directa desde terminal con argumentos. Requiere conocimientos basicos de linea de comandos.

---

## Requisitos

- Python 3.9+ instalado y en el PATH
- Dependencias instaladas:
  ```bash
  pip install -r requirements.txt
  ```
- Archivos CSV en las carpetas correspondientes

---

## Sintaxis basica

```bash
python generate_pdfs.py --main "ruta/carpeta_principal" --sub "ruta/carpeta_sub" --out "ruta/salida"
```

---

## Argumentos

| Argumento | Descripcion | Requerido |
|---|---|---|
| `--main` | Carpeta o archivo CSV del formulario principal | Si (o en config.json) |
| `--sub` | Carpeta o archivo CSV del subformulario | Si (o en config.json) |
| `--out` | Carpeta de salida para los PDFs | Si (o en config.json) |
| `--limit N` | Procesar solo los primeros N registros (0 = todos) | No |
| `--only "DUI1,DUI2"` | Filtrar por DUI (varios separados por coma) | No |
| `--include-empty` | Incluir campos vacios en el PDF | No |
| `--zip` | Crear un ZIP con todos los PDFs al finalizar | No |
| `--workers N` | Trabajadores en paralelo (1 = secuencial) | No |

---

## Ejemplos

```bash
# Uso completo con rutas manuales
python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs

# Solo los primeros 200 registros
python generate_pdfs.py --limit 200

# Filtrar por DUIs especificos
python generate_pdfs.py --only "06784334-6,03934980-5"

# Incluir campos vacios
python generate_pdfs.py --include-empty

# Exportar a ZIP al finalizar
python generate_pdfs.py --zip

# Procesar en paralelo con 4 workers
python generate_pdfs.py --workers 4

# Combinar opciones
python generate_pdfs.py --limit 500 --workers 4 --zip --include-empty
```

---

## Usando config.json

Si existe `config.json` en la raiz del proyecto con las rutas, los argumentos `--main`, `--sub` y `--out` se vuelven opcionales:

```bash
# Usa las rutas de config.json
python generate_pdfs.py

# Sobreescribe solo la salida
python generate_pdfs.py --out output/otra_carpeta
```

Contenido tipico de `config.json`:

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

> **Nota:** Los argumentos por CLI tienen prioridad sobre `config.json`.

---

## Detalles tecnicos

- Los CSV se leen como texto (`dtype=str`) para conservar ceros a la izquierda.
- La union entre formularios se realiza por la columna **`Record Link ID`**.
- El nombre del PDF se genera usando el campo **`01. Numero de Documento Unico de Identidad (DUI)`**.
- Si hay colisiones de nombre, se agrega el `Record Link ID` como sufijo.
- El ZIP se genera dentro de la carpeta `--out`.

---

## Workers en paralelo

Para lotes grandes (1000+ registros):

```bash
python generate_pdfs.py --workers 4
```

Estimacion para ~53.000 registros:

| Workers | Tiempo estimado |
|---|---|
| 1 (secuencial) | ~45 min |
| 4 | ~12 min |
| 8 | ~7 min |

> En Windows cada worker arranza un proceso Python independiente (~5 segundos de overhead).

---

## Solucion de problemas

| Error | Causa | Solucion |
|---|---|---|
| `--main, --sub, --out are required` | Falta `config.json` o no se pasaron rutas | Crear `config.json` o pasar los argumentos |
| `No CSV files found in folder` | La carpeta no tiene archivos `.csv` | Verificar que los CSV esten en la carpeta indicada |
| `Column 'Record Link ID' not found` | El CSV no tiene esa columna | Verificar que los archivos sean los correctos |
