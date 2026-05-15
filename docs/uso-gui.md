# Uso con GUI — `gui_app.py`

Interfaz grafica de escritorio con ventanas, botones y calendario. No requiere conocimientos de terminal.

---

## Requisitos

- Python 3.9+ instalado
- Dependencias instaladas:
  ```bash
  pip install -r requirements.txt
  ```
- Archivos CSV en las carpetas correspondientes

---

## Como se ejecuta

```bash
python gui_app.py
```

O si prefieres un ejecutable portable:
```bash
build_exe.bat
```
Esto genera `dist/GenerarPDFs.exe` que funciona sin Python instalado.

---

## Pantalla principal

```
┌──────────────────────────────────────────────────────────────┐
│  Generador de PDFs - Subsidio GLP                            │
├──────────────────────────────────────────────────────────────┤
│  Carpeta principal (CSVs):      [input/main______] [Examinar]│
│  Carpeta subformularios (CSVs): [input/sub_______] [Examinar]│
│  Carpeta de salida (PDFs):      [output/pdfs______] [Examinar]│
│ ──────────────────────────────────────────────────────────── │
│  ☐ Filtrar por fecha                                         │
│  Desde: [________] 📅   Hasta: [________] 📅                  │
│ ──────────────────────────────────────────────────────────── │
│  ☐ Incluir campos vacios en el PDF                           │
│  ☐ Exportar a ZIP al finalizar                               │
│  Workers: 1 (secuencial)                                      │
│                                                              │
│  [████████████████░░░░░░░░░░░░░░░░░]  45%                    │
│  Generando 24506/53076...                                     │
│                                                              │
│  [  GENERAR  ]  [ CANCELAR ]                                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Campos

### Carpetas
Tres campos para seleccionar las carpetas de trabajo. Usa el boton **Examinar** o escribe la ruta directamente.

| Campo | Descripcion | Default |
|---|---|---|
| Carpeta principal | CSVs del formulario principal | `input/main` |
| Carpeta subformularios | CSVs de subformularios | `input/sub` |
| Carpeta de salida | Donde se guardaran los PDFs | `output/pdfs` |

### Filtro por fecha
1. Marca **"Filtrar por fecha"**
2. Se cargaran automaticamente las fechas disponibles desde los CSVs
3. Haz clic en el campo de fecha o en el boton **📅** para abrir el calendario
4. Navega con las flechas **◀ ▶** y selecciona un dia
5. Usa **"Hoy"** para la fecha actual o **"Cancelar"** para cerrar

> El formato de fecha es `dd-mmm-aaaa` (ej: `24-sep-2025`).

### Opciones

| Opcion | Descripcion |
|---|---|
| Incluir campos vacios | Muestra todas las columnas del CSV aunque esten vacias |
| Exportar a ZIP | Genera un archivo `subsidios_pdfs.zip` con todos los PDFs |
| Workers | Siempre en 1 (secuencial). No requiere configuracion. |

---

## Botones

| Boton | Accion |
|---|---|
| **GENERAR** | Inicia la generacion de PDFs. Se deshabilita mientras procesa. |
| **CANCELAR** | Detiene la generacion en curso. Los PDFs ya generados se conservan. |

---

## Barra de progreso

Muestra en tiempo real:
- Progreso total de la generacion
- Cuantos PDFs se han generado vs el total
- Estado actual ("Leyendo archivos...", "Generando...", etc.)

Al finalizar, muestra un resumen con:
- Cantidad de PDFs generados
- Cantidad de fallos (si los hubo)
- Tiempo total transcurrido

---

## Para empaquetar como .exe

```bash
build_exe.bat
```

Esto crea `dist/GenerarPDFs.exe`, un ejecutable portatil que:
- No requiere Python instalado
- No requiere terminal
- Se distribuye como un solo archivo

> **Nota:** PyInstaller debe estar instalado (`pip install -r requirements.txt` lo incluye).

---

## Solucion de problemas

| Problema | Causa | Solucion |
|---|---|---|
| La ventana no se abre | Falta tkinter | `pip install tk` o reinstalar Python con la opcion "tcl/tk" |
| "No existe la carpeta" | La ruta no es valida | Usa el boton **Examinar** para seleccionar la carpeta |
| "No hay CSVs" | La carpeta no contiene archivos `.csv` | Verificar que los CSVs esten en la carpeta correcta |
| "Columna no encontrada" | El CSV no tiene las columnas esperadas | Verificar que los archivos sean los correctos |
| No carga fechas | La columna 'Date' no tiene formato valido | Verificar que las fechas esten en formato `dd-mmm-aaaa` |
