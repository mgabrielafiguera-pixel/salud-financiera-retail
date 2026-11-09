import streamlit as st

from comun import cargar, musd, pct, seleccion, tabla_estado

df = cargar()
ticker, anio, hist, f, p = seleccion(df)
if f is None:
    st.warning("No hay datos para esa empresa y año.")
    st.stop()

st.title(f"Estado de resultados · {f['empresa']}")

c1, c2 = st.columns([3, 1])
modo = c1.radio("Vista", ["Montos", "Análisis vertical", "Variación anual"], horizontal=True)
n = c2.number_input("Años a mostrar", 2, 7, 5)

filas = [
    ("Ingresos", "ingresos", True),
    ("Costo de ventas", "costo_ventas", False),
    ("Utilidad bruta", "utilidad_bruta", True),
    ("Gastos operativos (SG&A)", "gastos_operativos", False),
    ("Utilidad operativa", "utilidad_operativa", True),
    ("Gasto por intereses", "gasto_intereses", False),
    ("Utilidad antes de impuestos", "utilidad_antes_impuestos", True),
    ("Impuesto a la renta", "impuestos", False),
    ("Utilidad neta", "utilidad_neta", True),
    ("Depreciación y amortización", "depreciacion", False),
    ("EBITDA", "ebitda", True),
]
datos, tabla = tabla_estado(hist, filas, anio, n, "ingresos", modo)
st.caption({"Montos": "US$ millones, años fiscales hasta " + str(anio) + ".",
             "Análisis vertical": "Cada línea como % de los ingresos del año.",
             "Variación anual": "Cambio % de cada línea contra el año anterior."}[modo])
st.dataframe(tabla, width="stretch", height=35 * (len(filas) + 1) + 3)
st.download_button("Descargar tabla (CSV)", datos.to_csv().encode("utf-8"),
                   f"estado_resultados_{ticker}.csv", "text/csv")

with st.container(border=True):
    st.markdown(f"**Lectura rápida {anio}:** margen bruto {pct(f['margen_bruto'])}, "
                f"margen operativo {pct(f['margen_operativo'])}, margen neto "
                f"{pct(f['margen_neto'])}, EBITDA {musd(f['ebitda'])}, "
                f"tasa efectiva de impuestos {pct(f['tasa_impuesto'])}.")
st.caption("Cifras tal como se reportan en el 10-K (XBRL). La depreciación sale del estado de "
           "flujo de efectivo. Walmart y Costco incluyen cuotas de membresía en ingresos.")
