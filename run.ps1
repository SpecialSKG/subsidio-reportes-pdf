#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$ROOT = $PSScriptRoot

function Write-Step($msg) {
    Write-Host "`n>> $msg" -ForegroundColor Cyan
}

function Write-OK($msg) {
    Write-Host "  [OK] $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "  [!] $msg" -ForegroundColor Yellow
}

function Write-Fail($msg) {
    Write-Host "  [ERROR] $msg" -ForegroundColor Red
}

# ──────────────────────────────────────────────
Clear-Host
Write-Host "============================================" -ForegroundColor DarkCyan
Write-Host "   Generador de PDFs - Subsidio GLP" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor DarkCyan
Write-Host ""

# ── 1. Verificar Python ──────────────────────
Write-Step "Verificando Python..."
try {
    $pyVersion = python --version
    Write-OK $pyVersion
} catch {
    Write-Fail "Python no esta instalado o no esta en el PATH."
    Write-Host "  Instalalo desde: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  (Marca la opcion 'Add Python to PATH' durante la instalacion)`n"
    Read-Host "Presiona Enter para salir..."
    exit 1
}

# ── 2. Validar carpetas de entrada ────────────
Write-Step "Validando archivos de entrada..."

$mainPath = Join-Path $ROOT "input/main"
$subPath  = Join-Path $ROOT "input/sub"

if (-not (Test-Path -LiteralPath $mainPath)) {
    Write-Fail "No se encuentra la carpeta: input/main"
    Write-Host "  Crea la carpeta y coloca ahi los CSVs del formulario principal.`n"
    Read-Host "Presiona Enter para salir..."
    exit 1
}

if (-not (Test-Path -LiteralPath $subPath)) {
    Write-Fail "No se encuentra la carpeta: input/sub"
    Write-Host "  Crea la carpeta y coloca ahi los CSVs de subformularios.`n"
    Read-Host "Presiona Enter para salir..."
    exit 1
}

$mainFiles = @(Get-ChildItem -LiteralPath $mainPath -Filter "*.csv" -ErrorAction SilentlyContinue)
$subFiles  = @(Get-ChildItem -LiteralPath $subPath  -Filter "*.csv" -ErrorAction SilentlyContinue)

if ($mainFiles.Count -eq 0) {
    Write-Fail "No hay archivos CSV en input/main/"
    Write-Host "  Coloca los CSVs del formulario principal en input/main/`n"
    Read-Host "Presiona Enter para salir..."
    exit 1
}

if ($subFiles.Count -eq 0) {
    Write-Fail "No hay archivos CSV en input/sub/"
    Write-Host "  Coloca los CSVs de subformularios en input/sub/`n"
    Read-Host "Presiona Enter para salir..."
    exit 1
}

Write-OK "Formulario principal: $($mainFiles.Count) archivo(s) encontrado(s)"
Write-OK "Subformularios:       $($subFiles.Count) archivo(s) encontrado(s)"

# ── 3. Verificar / activar .venv ──────────────
Write-Step "Preparando entorno virtual..."

$venvPath = Join-Path $ROOT ".venv"

if (-not (Test-Path -LiteralPath $venvPath)) {
    Write-Warn "Creando entorno virtual..."
    python -m venv $venvPath
    Write-OK "Entorno virtual creado"
}

$activate = Join-Path (Join-Path $venvPath "Scripts") "Activate.ps1"
if (Test-Path -LiteralPath $activate) {
    & $activate
    Write-OK "Entorno virtual activado"
} else {
    Write-Fail "No se encuentra el script de activacion del entorno virtual."
    Read-Host "Presiona Enter para salir..."
    exit 1
}

# ── 4. Instalar dependencias ──────────────────
Write-Step "Verificando dependencias..."
$reqFile = Join-Path $ROOT "requirements.txt"
if (Test-Path -LiteralPath $reqFile) {
    pip install -r $reqFile -q
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Dependencias instaladas / actualizadas"
    } else {
        Write-Warn "Hubo un problema con las dependencias. Continuando..."
    }
}

# ── 5. Asegurar carpeta de salida ─────────────
$outDir = Join-Path (Join-Path $ROOT "output") "pdfs"
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    Write-OK "Carpeta de salida creada: output/pdfs/"
}

# ── 6. Ejecutar generacion ────────────────────
Write-Step "Generando PDFs..."
Write-Host "  Procesando..." -ForegroundColor DarkGray
Write-Host ""

try {
    python (Join-Path $ROOT "generate_pdfs.py")
    $exitCode = $LASTEXITCODE
} catch {
    $exitCode = 1
    Write-Fail "Error durante la ejecucion: $_"
}

Write-Host ""
Write-Host "============================================" -ForegroundColor DarkCyan

if ($exitCode -eq 0) {
    Write-Host "   PROCESO COMPLETADO" -ForegroundColor Green
    Write-Host "   Los PDFs estan en: output/pdfs/" -ForegroundColor Green
} else {
    Write-Host "   EL PROCESO FINALIZO CON ERRORES" -ForegroundColor Red
    Write-Host "   Revisa los mensajes anteriores para mas detalles." -ForegroundColor Red
}

Write-Host "============================================" -ForegroundColor DarkCyan
Write-Host ""
Read-Host "Presiona Enter para cerrar esta ventana..."
