# subsidio-reportes-pdf

Aplicativo en **Python** para generar **PDFs** a partir de archivos **CSV** de formularios y subformularios, con soporte para múltiples archivos y exportación final a ZIP.

---

## Requisitos técnicos

- Python 3.9+ (recomendado 3.10+)
- Instalar dependencias:
  ```bash
  pip install pandas reportlab tqdm
  ```

---

## Estructura recomendada de carpetas

```
subsidio-reportes-pdf/
  README.md
  subsidio-reportes-pdf.md
  generate_pdfs.py
  input/
    main/   # aquí van todos los CSV del formulario principal
    sub/    # aquí van todos los CSV de subformularios (ej: SubForm4)
  output/
    pdfs/   # PDFs generados
    subsidios_pdfs.zip  # ZIP con todos los PDFs (si se activa la opción)
```

Coloca todos los archivos CSV del formulario principal en `input/main/` y los de subformularios en `input/sub/`.

---

## Ejecución

Desde la carpeta raíz del proyecto:


### Generar TODOS los PDFs (modo recomendado)
```bash
python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs
```

### Exportar todos los PDFs a un ZIP
```bash
python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs --zip
```

### Otras opciones

- Limitar la cantidad de registros:
  ```bash
  python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs --limit 200
  ```
- Filtrar por uno o varios DUI:
  ```bash
  python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs --only "06784334-6,03934980-5"
  ```
- Incluir filas aunque estén vacías:
  ```bash
  python generate_pdfs.py --main input/main --sub input/sub --out output/pdfs --include-empty
  ```

---

## Detalles técnicos

- El script detecta si el argumento --main o --sub es una carpeta y concatena automáticamente todos los CSV encontrados.
- La unión entre formularios se realiza por la columna **`Record Link ID`**.
- El nombre del PDF se genera usando el campo **`01. Numero de Documento Único de Identidad (DUI)`**. Si está vacío, usa el `Record Link ID`.
- Si hay colisiones de nombre, se agrega el `Record Link ID` para evitar sobreescritura.
- Los CSV se leen como texto (`dtype=str`) para no perder ceros a la izquierda.

---


## Exportar PDFs a ZIP

Si usas el parámetro `--zip`, al finalizar se creará el archivo `subsidios_pdfs.zip` con todos los PDFs generados, en la carpeta `output/` (o donde indiques la salida).

---

## Mejoras futuras

- Exportación automática a ZIP.
- Soporte para múltiples subformularios (SubForm1, SubForm2, etc.).
- Personalización avanzada del nombre del PDF.
