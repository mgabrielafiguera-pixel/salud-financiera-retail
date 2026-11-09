import plotly.graph_objects as go
import streamlit as st

from comun import (NEGATIVO, POSITIVO, TOTAL, barras_anuales, cargar, comparativo, estilo,
                   lineas_anuales, musd, pct, seleccion, tiene, var_pct)

df = cargar()
ticker, anio, hist, f, p = seleccion(df)
if f is None:
    st.warning("No hay datos para esa empresa y año.")
    st.stop()

st.title(f"Ingresos y gastos · {f['empresa']} {anio}")

c = st.columns(4)
c[0].metric("Ingresos", musd(f["ingresos"]),
            var_pct(f["ingresos"], p["ingresos"] if p is not None else None))
c[1].metric("Costo de ventas", musd(f["costo_ventas"]),
            var_pct(f["costo_ventas"], p["costo_ventas"] if p is not None else None),
            delta_color="inverse")
c[2].metric("Gastos operativos", musd(f["gastos_operativos"]),
            var_pct(f["gastos_operativos"], p["gastos_operativos"] if p is not None else None),
            delta_color="inverse")
c[3].metric("Utilidad operativa", musd(f["utilidad_operativa"]),
            var_pct(f["utilidad_operativa"], p["utilidad_operativa"] if p is not None else None))

# Cascada: de ingresos a utilidad neta
def v(col):
    return f[col] if tiene(f[col]) else 0.0

pasos = [("Ingresos", v("ingresos"), "absolute"),
         ("Costo de ventas", -v("costo_ventas"), "relative"),
         ("Utilidad bruta", 0, "total"),
         ("Gastos operativos", -v("gastos_operativos"), "relative")]
otros_op = v("utilidad_operativa") - (v("ingresos") - v("costo_ventas") - v("gastos_operativos"))
if tiene(f["utilidad_operativa"]) and abs(otros_op) > 0.001 * v("ingresos"):
    pasos.append(("Otros operativos", otros_op, "relative"))
pasos.append(("Utilidad operativa", 0, "total"))
if tiene(f["utilidad_antes_impuestos"]):
    pasos.append(("Intereses", -v("gasto_intereses"), "relative"))
    otros_no_op = v("utilidad_antes_impuestos") - (v("utilidad_operativa") - v("gasto_intereses"))
    if abs(otros_no_op) > 0.001 * v("ingresos"):
        pasos.append(("Otros no operativos", otros_no_op, "relative"))
    pasos.append(("Antes de impuestos", 0, "total"))
    pasos.append(("Impuestos", -v("impuestos"), "relative"))
    resto = v("utilidad_neta") - (v("utilidad_antes_impuestos") - v("impuestos"))
    if abs(resto) > 0.001 * v("ingresos"):
        pasos.append(("Otros (minoritarios, discontinuadas)", resto, "relative"))
pasos.append(("Utilidad neta", 0, "total"))

fig = go.Figure(go.Waterfall(
    x=[p_[0] for p_ in pasos], y=[p_[1] / 1e9 for p_ in pasos],
    measure=[p_[2] for p_ in pasos],
    increasing=dict(marker_color=POSITIVO), decreasing=dict(marker_color=NEGATIVO),
    totals=dict(marker_color=TOTAL), connector=dict(line=dict(color="rgba(128,128,128,0.4)")),
    hovertemplate="%{x}: US$ %{y:,.2f} mil M<extra></extra>",
))
fig.update_layout(title="De los ingresos a la utilidad neta (US$ miles de millones)", showlegend=False)
st.plotly_chart(estilo(fig, 420), width="stretch")
st.caption("Verde suma, rojo resta, azul son subtotales. Las partidas «otros» cuadran la "
           "cascada con lo reportado en el 10-K.")

c1, c2 = st.columns(2)
c1.plotly_chart(lineas_anuales(hist, {"margen_bruto": "Margen bruto",
                                      "gastos_sobre_ventas": "Gastos operativos / ingresos",
                                      "margen_operativo": "Margen operativo"},
                               "Estructura de costos (% de ingresos)"), width="stretch")
c2.plotly_chart(lineas_anuales(hist, {"crecimiento_ingresos": "Ingresos",
                                      "crecimiento_utilidad": "Utilidad neta"},
                               "Crecimiento anual"), width="stretch")

c1, c2 = st.columns(2)
c1.plotly_chart(barras_anuales(hist, {"ingresos": "Ingresos", "costo_ventas": "Costo de ventas",
                                      "gastos_operativos": "Gastos operativos"},
                               "Ingresos y gastos por año"), width="stretch")
c2.plotly_chart(comparativo(df, anio, "gastos_sobre_ventas",
                            f"Gastos operativos / ingresos · {anio} (menos es mejor)", "pct",
                            ticker, menor_mejor=True), width="stretch")
st.caption(f"Tasa efectiva de impuestos {anio}: {pct(f['tasa_impuesto'])}. "
           "Walmart y Costco incluyen cuotas de membresía en ingresos.")
