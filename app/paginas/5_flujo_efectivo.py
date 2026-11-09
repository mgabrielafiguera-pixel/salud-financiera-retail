import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import (SERIE, barras_anuales, cargar, comparativo, estilo, lineas_anuales, musd,
                   pct, seleccion, tiene, var_pct, veces)

df = cargar()
ticker, anio, hist, f, p = seleccion(df)
if f is None:
    st.warning("No hay datos para esa empresa y año.")
    st.stop()

st.title(f"Bancos y flujo de efectivo · {f['empresa']} {anio}")
prev = p if p is not None else {}

c = st.columns(3) + st.columns(3)
c[0].metric("Efectivo y equivalentes", musd(f["efectivo"]),
            var_pct(f["efectivo"], prev.get("efectivo")))
c[1].metric("Flujo operativo", musd(f["flujo_operativo"]),
            var_pct(f["flujo_operativo"], prev.get("flujo_operativo")))
c[2].metric("Inversión en activos (capex)", musd(f["capex"]),
            var_pct(f["capex"], prev.get("capex")), delta_color="off")
c[3].metric("Flujo de caja libre", musd(f["flujo_caja_libre"]),
            var_pct(f["flujo_caja_libre"], prev.get("flujo_caja_libre")))
c[4].metric("Caja libre / utilidad neta", pct(f["conversion_caja"], 0))
st.caption("Flujo de caja libre = flujo operativo − capex. «Caja libre / utilidad neta» "
           "mide cuánto de la utilidad contable se convierte en efectivo.")

c1, c2 = st.columns(2)
c1.plotly_chart(barras_anuales(hist, {"flujo_operativo": "Operación",
                                      "flujo_inversion": "Inversión",
                                      "flujo_financiamiento": "Financiamiento"},
                               "Flujos de efectivo por actividad"),
                width="stretch")
c2.plotly_chart(barras_anuales(hist, {"efectivo": "Efectivo al cierre"},
                               "Efectivo y equivalentes al cierre"),
                width="stretch")

# Uso del flujo de caja libre
fig = go.Figure()
fig.add_trace(go.Bar(x=hist.index, y=hist["flujo_caja_libre"] / 1e9, name="Flujo de caja libre",
                     marker_color=SERIE[0], offsetgroup=0,
                     hovertemplate="%{x} · Caja libre: US$ %{y:,.2f} mil M<extra></extra>"))
for i, (col, nombre) in enumerate([("dividendos", "Dividendos"),
                                   ("recompra_acciones", "Recompra de acciones")], start=1):
    if tiene(hist[col]):
        fig.add_trace(go.Bar(x=hist.index, y=hist[col].fillna(0) / 1e9, name=nombre,
                             marker_color=SERIE[i], offsetgroup=1,
                             hovertemplate="%{x} · " + nombre + ": US$ %{y:,.2f} mil M<extra></extra>"))
fig.update_layout(title="¿A dónde va la caja libre? (US$ miles de millones)", barmode="relative")
fig.update_xaxes(dtick=1)
st.plotly_chart(estilo(fig, 360), width="stretch")
st.caption("La barra apilada muestra lo devuelto a los accionistas (dividendos + recompras) "
           "frente a la caja libre generada ese año.")

c1, c2 = st.columns(2)
c1.plotly_chart(lineas_anuales(hist, {"razon_efectivo": "Efectivo / pasivo corriente"},
                               "Cobertura de efectivo", tipo="veces"), width="stretch")
c2.plotly_chart(comparativo(df, anio, "flujo_caja_libre", f"Flujo de caja libre · {anio}",
                            "musd", ticker), width="stretch")
st.caption("Los 10-K reportan el efectivo consolidado; no hay detalle por banco ni por cuenta.")
