import streamlit as st

from comun import (barras_anuales, cargar, comparativo, dias, lineas_anuales, musd, pct,
                   seleccion, tiene, var_abs, var_pct)

df = cargar()
ticker, anio, hist, f, p = seleccion(df)
if f is None:
    st.warning("No hay datos para esa empresa y año.")
    st.stop()

st.title(f"Cuentas por cobrar · {f['empresa']} {anio}")

if not tiene(hist["cuentas_por_cobrar"]):
    st.info(f"{f['empresa']} no reporta cuentas por cobrar en su balance: vende casi todo al "
            "contado o con tarjeta, y el cobro es prácticamente inmediato. En el ciclo de caja "
            "cuenta como 0 días de cobro. Abajo puedes comparar con las cadenas que sí reportan.")
else:
    prev = p if p is not None else {}
    c = st.columns(4)
    c[0].metric("Saldo de cuentas por cobrar", musd(f["cuentas_por_cobrar"]),
                var_pct(f["cuentas_por_cobrar"], prev.get("cuentas_por_cobrar")),
                delta_color="inverse")
    c[1].metric("Días de cobro", dias(f["dias_cobro"]),
                var_abs(f["dias_cobro"], prev.get("dias_cobro"), dias), delta_color="inverse")
    c[2].metric("% del activo corriente",
                pct(f["cuentas_por_cobrar"] / f["activo_corriente"]))
    c[3].metric("Crecimiento CxC vs. ingresos",
                var_pct(f["cuentas_por_cobrar"], prev.get("cuentas_por_cobrar")) or "s/d",
                f"ingresos {var_pct(f['ingresos'], prev.get('ingresos')) or 's/d'}",
                delta_color="off")
    st.caption("Si las cuentas por cobrar crecen más rápido que los ingresos, la empresa está "
               "tardando más en cobrar.")

    c1, c2 = st.columns(2)
    c1.plotly_chart(barras_anuales(hist, {"cuentas_por_cobrar": "Cuentas por cobrar"},
                                   "Saldo al cierre"), width="stretch")
    c2.plotly_chart(lineas_anuales(hist, {"dias_cobro": "Días de cobro"},
                                   "Días de cobro (DSO)", tipo="dias"), width="stretch")

st.plotly_chart(comparativo(df, anio, "dias_cobro", f"Días de cobro · {anio} (menos es mejor)",
                            "dias", ticker, menor_mejor=True), width="stretch")
st.caption("Días de cobro = cuentas por cobrar al cierre / ingresos × 365. Los 10-K no "
           "detallan la antigüedad de saldos por cliente; solo el saldo consolidado.")
