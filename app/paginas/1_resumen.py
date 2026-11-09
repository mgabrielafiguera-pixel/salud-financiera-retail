import pandas as pd
import streamlit as st

from comun import (barras_anuales, cargar, comparativo, dias, lineas_anuales, musd, num,
                   pct, seleccion, tiene, var_abs, var_pct, veces)

df = cargar()
ticker, anio, hist, f, p = seleccion(df)

st.title(f"Resumen ejecutivo · {f['empresa'] if f is not None else ticker} {anio}")
if f is None:
    st.warning("No hay datos para esa empresa y año.")
    st.stop()
p = p if p is not None else pd.Series(dtype=float)
st.caption(f"Cierre fiscal: {f['fecha_cierre']} · variaciones contra el año fiscal anterior")

# KPIs
c = st.columns(4)
c[0].metric("Ingresos", musd(f["ingresos"]), var_pct(f["ingresos"], p.get("ingresos")))
c[1].metric("Utilidad neta", musd(f["utilidad_neta"]),
            var_pct(f["utilidad_neta"], p.get("utilidad_neta")))
c[2].metric("Margen neto", pct(f["margen_neto"]),
            var_abs(f["margen_neto"], p.get("margen_neto"), lambda v: f"{num(v*100, 1)} pp"))
c[3].metric("EBITDA", musd(f["ebitda"]), var_pct(f["ebitda"], p.get("ebitda")))
c = st.columns(4)
c[0].metric("Flujo de caja libre", musd(f["flujo_caja_libre"]),
            var_pct(f["flujo_caja_libre"], p.get("flujo_caja_libre")))
c[1].metric("Efectivo", musd(f["efectivo"]), var_pct(f["efectivo"], p.get("efectivo")))
c[2].metric("Ciclo de caja", dias(f["ciclo_caja"]),
            var_abs(f["ciclo_caja"], p.get("ciclo_caja"), dias), delta_color="inverse")
c[3].metric("Deuda neta / EBITDA", veces(f["deuda_neta_ebitda"]),
            var_abs(f["deuda_neta_ebitda"], p.get("deuda_neta_ebitda"), veces),
            delta_color="inverse")

# Señales de alerta (reglas simples, estilo auditoría)
senales = []
if tiene(p.get("margen_neto")) and f["margen_neto"] - p["margen_neto"] < -0.005:
    senales.append(f"⚠️ El margen neto cayó {num((p['margen_neto'] - f['margen_neto'])*100, 1)} pp.")
if tiene(p.get("ciclo_caja")) and f["ciclo_caja"] - p["ciclo_caja"] > 5:
    senales.append(f"⚠️ El ciclo de caja se alargó {num(f['ciclo_caja'] - p['ciclo_caja'], 1)} días.")
if tiene(p.get("dias_inventario")) and f["dias_inventario"] - p["dias_inventario"] > 5:
    senales.append(f"⚠️ Los días de inventario subieron {num(f['dias_inventario'] - p['dias_inventario'], 1)}.")
if tiene(f["flujo_caja_libre"]) and f["flujo_caja_libre"] < 0:
    senales.append("⚠️ El flujo de caja libre es negativo.")
if tiene(f["deuda_neta_ebitda"]) and f["deuda_neta_ebitda"] > 3:
    senales.append("⚠️ La deuda neta supera 3 veces el EBITDA.")
if tiene(f["razon_corriente"]) and f["razon_corriente"] < 1:
    senales.append("ℹ️ Razón corriente menor a 1: habitual en retail cuando los proveedores "
                   "financian el inventario; vigilar junto al ciclo de caja.")
with st.container(border=True):
    st.markdown("**Señales del año**")
    st.markdown("\n".join(f"- {s}" for s in senales) if senales
                else "✅ Sin señales de alerta frente al año anterior.")

# Tendencias
c1, c2 = st.columns(2)
c1.plotly_chart(barras_anuales(hist, {"ingresos": "Ingresos", "utilidad_neta": "Utilidad neta"},
                               "Ingresos y utilidad neta"), width="stretch")
c2.plotly_chart(lineas_anuales(hist, {"margen_bruto": "Margen bruto",
                                      "margen_operativo": "Margen operativo",
                                      "margen_neto": "Margen neto"}, "Márgenes"),
                width="stretch")

# Comparativo con las demás cadenas
st.subheader(f"Frente a las demás cadenas · {anio}")
c1, c2, c3 = st.columns(3)
c1.plotly_chart(comparativo(df, anio, "margen_neto", "Margen neto", "pct", ticker),
                width="stretch")
c2.plotly_chart(comparativo(df, anio, "ciclo_caja", "Ciclo de caja (menos es mejor)", "dias",
                            ticker, menor_mejor=True), width="stretch")
c3.plotly_chart(comparativo(df, anio, "roe", "ROE", "pct", ticker), width="stretch")
