# Uso con `run.ps1` — Un solo clic

Script de PowerShell listo para ejecutar. Ideal para usuarios que solo quieren hacer doble clic y obtener los PDFs sin tocar la terminal.

---

## Requisitos

- Python 3.9+ instalado (el script lo verifica automaticamente)
- Conexion a internet solo en la **primera ejecucion** (para instalar dependencias)
- Archivos CSV en las carpetas `input/main/` y `input/sub/`

---

## Como se usa

1. Coloca los archivos CSV en las carpetas correspondientes:
   - `input/main/` — formulario principal
   - `input/sub/` — subformularios

2. Haz **doble clic** en `run.ps1`.

3. El script hara todo automaticamente:
   - Verifica que Python este instalado
   - Valida que las carpetas tengan archivos CSV
   - Crea y activa el entorno virtual (`.venv`) si no existe
   - Instala las dependencias necesarias (solo la primera vez)
   - Ejecuta la generacion de PDFs con barra de progreso
   - Muestra un resumen al finalizar
   - Pausa la ventana para que puedas ver los resultados

4. Presiona **Enter** para cerrar la ventana.

---

## Validaciones que realiza

El script verifica antes de ejecutar:

- ✅ Que Python exista en el sistema
- ✅ Que la carpeta `input/main/` exista y contenga archivos `.csv`
- ✅ Que la carpeta `input/sub/` exista y contenga archivos `.csv`

Si alguna validacion falla, muestra un mensaje claro y espera antes de cerrar.

---

## Estructura de carpetas esperada

```
proyecto/
  run.ps1              ← Script de doble clic
  config.json          ← Configuracion (rutas, opciones)
  input/
    main/              ← CSVs del formulario principal
    sub/               ← CSVs de subformularios
  output/
    pdfs/              ← PDFs generados (se crea automaticamente)
```

---

## Primera ejecucion

La primera vez que ejecutas `run.ps1`:

1. Crea un entorno virtual (`.venv/`) si no existe
2. Descarga e instala las dependencias (`pandas`, `reportlab`, `tqdm`)
3. Genera los PDFs

Este proceso puede tomar unos minutos adicionales. Las ejecuciones siguientes son mas rapidas.

---

## Personalizacion

El script usa los valores de `config.json` para las rutas. Si necesitas cambiar las carpetas de entrada o salida, edita `config.json`:

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

---

## Solucion de problemas

| Problema | Causa | Solucion |
|---|---|---|
| Se abre un editor de texto en vez de ejecutarse | Windows no asocia `.ps1` con doble clic | Haz clic derecho → "Ejecutar con PowerShell" |
| "Python no esta instalado" | Python no esta en el PATH | Instalar Python desde python.org (marcar "Add to PATH") |
| "No hay archivos CSV en input/main/" | La carpeta esta vacia o no existe | Colocar los CSVs en `input/main/` |
| "No se encuentra el script de activacion" | El `.venv` esta corrupto | Borrar la carpeta `.venv` y ejecutar de nuevo |
