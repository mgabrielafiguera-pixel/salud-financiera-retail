import streamlit as st

from comun import (barras_anuales, cargar, comparativo, dias, lineas_anuales, musd, pct,
                   seleccion, var_abs, var_pct)

df = cargar()
ticker, anio, hist, f, p = seleccion(df)
if f is None:
    st.warning("No hay datos para esa empresa y año.")
    st.stop()

st.title(f"Cuentas por pagar · {f['empresa']} {anio}")
prev = p if p is not None else {}
financiado = f["cuentas_por_pagar"] / f["inventario"]

c = st.columns(4)
c[0].metric("Saldo de cuentas por pagar", musd(f["cuentas_por_pagar"]),
            var_pct(f["cuentas_por_pagar"], prev.get("cuentas_por_pagar")), delta_color="off")
c[1].metric("Días de pago", dias(f["dias_pago"]),
            var_abs(f["dias_pago"], prev.get("dias_pago"), dias))
c[2].metric("CxP / inventario", pct(financiado))
c[3].metric("Gastos acumulados por pagar", musd(f["gastos_acumulados"]),
            var_pct(f["gastos_acumulados"], prev.get("gastos_acumulados")), delta_color="off")
st.caption("«CxP / inventario» = parte del inventario financiada por proveedores. "
           "Más de 100 % significa que los proveedores financian todo el inventario.")

c1, c2 = st.columns(2)
c1.plotly_chart(barras_anuales(hist, {"cuentas_por_pagar": "Cuentas por pagar",
                                      "inventario": "Inventario"},
                               "Cuentas por pagar vs. inventario"),
                width="stretch")
c2.plotly_chart(lineas_anuales(hist, {"dias_pago": "Días de pago",
                                      "dias_inventario": "Días de inventario"},
                               "Días de pago vs. días de inventario", tipo="dias"),
                width="stretch")
st.caption("Cuando la línea de días de pago está por encima de la de inventario, la empresa "
           "vende la mercancía antes de pagarla.")

st.plotly_chart(comparativo(df, anio, "dias_pago", f"Días de pago · {anio}", "dias", ticker),
                width="stretch")
st.caption("Días de pago = cuentas por pagar al cierre / costo de ventas × 365. Los 10-K no "
           "detallan vencimientos por proveedor.")
