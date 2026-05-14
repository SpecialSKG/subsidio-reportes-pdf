# Mejoras futuras — subsidio-reportes-pdf

Estrategias para hacer la herramienta mas amigable para usuarios no tecnicos.

---

## Filosofia

El proyecto actual funciona correctamente desde terminal, pero requiere:

1. Tener Python instalado
2. Crear y activar un entorno virtual (`.venv`)
3. Instalar dependencias con `pip`
4. Conocer y escribir argumentos CLI (`--main`, `--sub`, `--out`, etc.)
5. Interpretar la salida en terminal

Para un usuario que solo quiere "poner los CSVs y obtener los PDFs", cada uno de estos pasos es una barrera.

---

## Categorias por esfuerzo

### 🟢 Bajo esfuerzo (1-2 dias)

| # | Opcion | Descripcion | Beneficio |
|---|---|---|---|
| 1 | **Script `run.ps1`** | PowerShell que activa `.venv`, verifica dependencias, ejecuta `generate_pdfs.py` y pausa al final para ver resultados. El usuario hace doble-clic | Elimina escribir comandos |
| 2 | **Modo interactivo** | Si no se pasan argumentos, el script pregunta paso a paso en la terminal: *"Ruta de carpeta principal:"*, *"Incluir campos vacios? (s/n)"*, etc. | El usuario no necesita conocer argumentos CLI |
| 3 | **Validador de CSVs** | Antes de procesar, verifica columnas esperadas, encoding, duplicados, filas vacias. Errores claros y tempranos | Evita frustraciones tras 30 min de procesamiento |
| 4 | **Informe HTML de resultado** | Al finalizar se genera un `.html` con resumen visual: cantidad de PDFs, fallos, tiempo, lista de archivos, enlace al ZIP | Feedback claro y compartible |

### 🟡 Medio esfuerzo (3-5 dias)

| # | Opcion | Descripcion | Beneficio |
|---|---|---|---|
| 5 | **Ejecutable `.exe`** | Empaquetar con PyInstaller. El usuario descarga un solo `.exe` y lo ejecuta. **No necesita Python, ni .venv, ni pip** | Elimina TODA la configuracion tecnica |
| 6 | **Interfaz web local** | Servidor web minimo (Flask / Dash) con drag & drop de CSVs, boton "Generar", barra de progreso en el navegador | Experiencia visual moderna, sin terminal |
| 7 | **Modo "watch"** | El script monitorea `input/`. Cuando aparecen CSVs nuevos, los procesa automaticamente | Automatizacion total para procesos batch recurrentes |

### 🔴 Alto esfuerzo (1-2 semanas)

| # | Opcion | Descripcion | Beneficio |
|---|---|---|---|
| 8 | **GUI de escritorio** | Interfaz grafica con tkinter o PyQt: selector de archivos, checkboxes, barra de progreso, boton cancelar | Experiencia completa tipo "aplicacion de Windows" |
| 9 | **Dashboard web completo** | Subida de CSVs por web, cola de procesamiento, historial de ejecuciones, descarga de ZIP | Escalable, multi-usuario, accesible desde cualquier PC |

---

## Roadmap recomendado

Para usuarios finales no tecnicos, el orden optimo de implementacion:

```
Fase 1 (inmediata)
  ├── run.ps1             ~1 hora
  ├── Validador de CSVs   ~4 horas
  └── Informe HTML        ~4 horas

Fase 2 (corto plazo)
  ├── Modo interactivo    ~1 dia
  └── Ejecutable .exe     ~1 dia

Fase 3 (medio plazo)
  ├── Interfaz web local  ~3-4 dias
  └── Modo watch          ~1 dia

Fase 4 (largo plazo)
  ├── GUI de escritorio   ~1 semana
  └── Dashboard web       ~2 semanas
```

---

## Detalle de cada opcion

### 1. Script `run.ps1`

```powershell
# run.ps1
$ErrorActionPreference = "Stop"

# Activar .venv
$venvPath = Join-Path $PSScriptRoot ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creando entorno virtual..."
    python -m venv $venvPath
}

& "$venvPath\Scripts\Activate.ps1"

# Verificar dependencias
pip install -r "$PSScriptRoot\requirements.txt" -q

# Ejecutar
python "$PSScriptRoot\generate_pdfs.py"

# Pausa
Read-Host "`nPresiona Enter para salir..."
```

**Ventajas:** Un solo clic, portable, sin comandos manuales.  
**Desventajas:** Sigue necesitando Python instalado en el sistema. La terminal se abre igual.

---

### 2. Modo interactivo

Agregar un flag `--interactive` o activarlo por defecto cuando no hay argumentos:

```
$ python generate_pdfs.py

No se detectaron argumentos. Modo interactivo:

Ruta de carpeta principal (ENTER para "input/main"):
Ruta de carpeta de subformularios (ENTER para "input/sub"):
Ruta de salida (ENTER para "output/pdfs"):
Incluir campos vacios? (s/N):
Exportar a ZIP al finalizar? (s/N):
Workers en paralelo (ENTER para 1):

Procesando...
```

**Implementacion:** Usar `input()` de Python con valores por defecto. Si se pasan argumentos CLI, omitir el modo interactivo.

---

### 3. Validador de CSVs

Funcion que se ejecuta justo despues de leer los CSVs:

```python
def validar_csvs(main_df, sub_df):
    errores = []

    if "Record Link ID" not in main_df.columns:
        errores.append("El CSV principal no tiene la columna 'Record Link ID'")
    if "Record Link ID" not in sub_df.columns:
        errores.append("El CSV de subformularios no tiene la columna 'Record Link ID'")

    # Verificar duplicados en main
    dups = main_df["Record Link ID"].value_counts()
    dups = dups[dups > 1]
    if len(dups) > 0:
        errores.append(f"Hay {len(dups)} Record Link ID duplicados en el formulario principal")

    # Verificar sub sin main
    rid_main = set(main_df["Record Link ID"])
    rid_sub = set(sub_df["Record Link ID"])
    huerfanos = rid_sub - rid_main
    if huerfanos:
        errores.append(f"Hay {len(huerfanos)} subregistros sin registro principal correspondiente")

    # Verificar DUI columna
    if DUI_COL not in main_df.columns:
        errores.append(f"No se encontro la columna '{DUI_COL}'")

    if errores:
        for e in errores:
            print(f"  [ADVERTENCIA] {e}")
        return False
    return True
```

---

### 4. Informe HTML de resultado

```html
<!DOCTYPE html>
<html>
<head><title>Reporte de generacion</title></head>
<body>
  <h1>Resumen de generacion</h1>
  <ul>
    <li>Fecha: 2026-05-14 10:30:00</li>
    <li>Registros procesados: 53.076</li>
    <li>PDFs generados: 53.074</li>
    <li>Fallidos: 2</li>
    <li>Tiempo total: 12 min 34 s</li>
    <li>Archivo ZIP: <a href="output/pdfs/subsidios_pdfs.zip">subsidios_pdfs.zip</a></li>
  </ul>
  <h2>Archivos generados (primeros 10)</h2>
  <ul>
    <li>00632632-3.pdf</li>
    <li>04858621-0.pdf</li>
    <li>...</li>
  </ul>
  <h2>Errores</h2>
  <ul>
    <li>RID=12345: Dato invalido en columna 'Edad'</li>
  </ul>
</body>
</html>
```

---

### 5. Ejecutable `.exe` con PyInstaller

```bash
pip install pyinstaller
pyinstaller --onefile --name "GenerarPDFs" generate_pdfs.py
```

**Consideraciones:**
- El `.exe` resultante pesa ~30-50 MB (incluye Python completo + pandas + reportlab)
- Hay que probar que `--workers N` funcione correctamente (multiprocessing con PyInstaller requiere configuracion extra)
- Se puede distribuir como un ZIP: el usuario descomprime y ejecuta

**Alternativa:** Usar `nuitka` en vez de PyInstaller (compila a C nativo, mas rapido, pero compilacion mas lenta).

---

### 6. Interfaz web local (Flask)

Estructura:

```
web/
  app.py            # Servidor Flask
  templates/
    index.html       # Pagina principal con drag & drop
    progress.html    # Barra de progreso en tiempo real (SSE o WebSocket)
  static/
    style.css
```

Flujo:

1. Usuario abre `http://localhost:5000`
2. Arrastra CSVs o selecciona carpetas
3. Configura opciones (checkboxes)
4. Click en "Generar PDFs"
5. Barra de progreso en tiempo real (Server-Sent Events)
6. Al finalizar, enlace de descarga del ZIP

**Dependencias extra:** `flask`, `flask-cors`

---

### 7. Modo "watch"

```python
import watchdog

def watch_folder(input_path, callback):
    observer = Observer()
    handler = CSVHandler(callback)
    observer.schedule(handler, input_path, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
```

Cuando se detecta un nuevo CSV en `input/`, se dispara el procesamiento automatico.

**Dependencia extra:** `watchdog`

---

### 8. GUI de escritorio (tkinter)

Ventana con:
- Selector de carpeta principal (boton "Examinar...")
- Selector de carpeta de subformularios
- Selector de carpeta de salida
- Checkbox "Incluir vacios"
- Checkbox "Exportar a ZIP"
- Selector numerico "Workers"
- Barra de progreso
- Boton "Generar" y "Cancelar"
- Area de log con scroll

**Ventaja:** Sin dependencias extra (tkinter viene con Python).  
**Desventaja:** Interfaz visual anticuada.

---

### 9. Dashboard web completo

Aplicacion web con:
- Autenticacion basica
- Subida de archivos CSV
- Cola de procesamiento (varios usuarios pueden encolar)
- Historial de ejecuciones
- Descarga de ZIPs anteriores
- Panel de administracion

**Stack sugerido:** FastAPI + React/Svelte o Django template.  
**Infraestructura:** Podria correr en un servidor interno o como aplicacion de escritorio "falsa" con `electron`.

---

## Criterios para priorizar

| Criterio | Peso |
|---|---|
| Impacto en experiencia de usuario | Alto |
| Tiempo de implementacion | Medio |
| Mantenimiento futuro | Medio |
| Compatibilidad con Windows | Alto |
| Sin dependencias adicionales pesadas | Bajo |
| Facilidad de distribucion | Alto |

---

## Notas tecnicas

- **Multiprocessing + PyInstaller:** En Windows, los ejecutables empaquetados con PyInstaller necesitan `multiprocessing.freeze_support()` al inicio.
- **Encoding:** Todos los archivos generados deben ser UTF-8 para evitar problemas con caracteres especiales (acentos, enies, etc.).
- **Rutas largas:** En Windows, rutas de mas de 260 caracteres pueden fallar. Considerar usar `\\?\` prefijo o `pathlib` que lo maneja automaticamente en Python 3.12+.
- **Permisos:** El `.exe` o la web no deben requerir permisos de administrador.
