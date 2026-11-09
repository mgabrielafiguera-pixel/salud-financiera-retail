# Paso a paso en VS Code (macOS)

## 1. Abrir el proyecto
1. Descomprime `salud-financiera-retail.zip` (o clona el repo) en tu carpeta de proyectos.
2. En VS Code: **File → Open Folder…** y elige `salud-financiera-retail`.
3. VS Code te ofrecerá instalar las extensiones recomendadas (Python, Pylance, Jupyter, Rainbow CSV). Acepta.

## 2. Preparar el entorno (una sola vez)
1. `Cmd + Shift + P` → **Tasks: Run Task** → **0. Preparar entorno (.venv + dependencias)**.
   Equivale a: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
2. `Cmd + Shift + P` → **Python: Select Interpreter** → elige `.venv`.
3. Copia `.env.example` como `.env` y escribe tu nombre y correo:
   ```
   SEC_USER_AGENT="Maria Figuera tu_correo@dominio.com"
   ```
   `.env` está en `.gitignore`: tu correo no se sube a GitHub.

## 3. Paso 1: extraer los 10-K
`Cmd + Shift + P` → **Tasks: Run Task** → **1. Extraer 10-K de la SEC**

Resultado esperado en la terminal: una línea por empresa (`WMT Walmart 7 años, ...`) y un listado de cifras faltantes.
Revisa `datos/estados_financieros.csv` (Rainbow CSV lo muestra por columnas). La columna `concepto_xbrl` dice qué etiqueta se usó en cada cifra.

Las respuestas de la SEC quedan en `datos/raw/`. Para volver a descargar usa la tarea **1b**.

## 4. Paso 2: calcular los ratios
**Tasks: Run Task** → **2. Calcular ratios (DuckDB)**

Genera `datos/ratios.csv` e imprime el ciclo de caja por empresa y año (la respuesta a la pregunta de negocio).

Atajo: `Cmd + Shift + B` corre el pipeline completo (paso 1 + paso 2).

## 5. Depurar
Pestaña **Run and Debug** (`Cmd + Shift + D`) → **Depurar: 01 extraer SEC**. Pon un breakpoint en
`extraer_empresa()` para inspeccionar el DataFrame de cada etiqueta XBRL.

## 6. Control de calidad sugerido
Compara 2 o 3 cifras por empresa contra el 10-K original en EDGAR
(https://www.sec.gov/edgar/search/): ingresos, inventario y cuentas por pagar del último año.

## 7. Subir a GitHub (opcional)
```bash
git init && git add . && git commit -m "Proyecto salud financiera retail SEC"
git branch -M main
git remote add origin https://github.com/<tu-usuario>/salud-financiera-retail.git
git push -u origin main
```

## Siguiente paso
`app/`: app de Streamlit sobre `datos/ratios.csv`.
