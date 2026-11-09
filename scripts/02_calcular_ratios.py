"""Ejecuta sql/02_ratios.sql con DuckDB (no requiere la CLI de DuckDB)."""

import os
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[1]
os.chdir(RAIZ)  # el SQL usa rutas relativas a la raíz del proyecto
if not Path("datos/estados_financieros.csv").exists():
    raise SystemExit("Falta datos/estados_financieros.csv: corre primero scripts/01_extraer_sec.py")

con = duckdb.connect()
sentencias = [s for s in (RAIZ / "sql" / "02_ratios.sql").read_text().split(";") if s.strip()]
for s in sentencias[:-1]:
    con.execute(s)
print("Guardado: datos/ratios.csv\n\nCiclo de caja (días) por año fiscal:")
print(con.sql(sentencias[-1]).df().to_string(index=False))
