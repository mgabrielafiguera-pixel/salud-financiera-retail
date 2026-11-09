import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from comun import COLORES, SERIE, cargar, dias, estilo, num

df = cargar()
anio = st.session_state["anio"]
anios = sorted(df["anio_fiscal"].unique())

st.title("Ciclo de caja: ¿qué cadena convierte mejor su inventario en caja?")
st.caption("Comparativo de las cinco cadenas, 2019–2025. Menos días = la caja vuelve antes; "
           "negativo = cobra a sus clientes antes de pagar a sus proveedores.")

# KPIs: año elegido y cambio contra el primer año
primero = df[df["anio_fiscal"] == anios[0]].set_index("ticker")
ultimo = df[df["anio_fiscal"] == anio].set_index("ticker").sort_values("ciclo_caja")
cols = st.columns(len(ultimo) or 1)
for col, (t, fila) in zip(cols, ultimo.iterrows()):
    delta = fila["ciclo_caja"] - primero["ciclo_caja"].get(t, float("nan"))
    col.metric(fila["empresa"], dias(fila["ciclo_caja"]),
               None if pd.isna(delta) else f"{num(delta, 1)} d vs. {anios[0]}",
               delta_color="inverse")

# Evolución
fig = go.Figure()
for t, g in df.groupby("ticker", sort=False):
    fig.add_trace(go.Scatter(
        x=g["anio_fiscal"], y=g["ciclo_caja"], name=g["empresa"].iloc[0],
        mode="lines+markers", line=dict(color=COLORES.get(t), width=2), marker=dict(size=8),
        hovertemplate="%{fullData.name}: %{y:,.1f} d<extra></extra>"))
fig.add_hline(y=0, line_width=1, line_color="rgba(128,128,128,0.6)")
fig.update_layout(title="Ciclo de caja por año (días)", hovermode="x unified")
fig.update_xaxes(dtick=1)
st.plotly_chart(estilo(fig, 420), width="stretch")

# Descomposición del año elegido
d = df[df["anio_fiscal"] == anio].sort_values("ciclo_caja")
fig = go.Figure()
for (col, nombre, signo), color in zip(
        [("dias_inventario", "Días de inventario", 1), ("dias_cobro", "Días de cobro", 1),
         ("dias_pago", "Días de pago (resta)", -1)], SERIE):
    fig.add_trace(go.Bar(y=d["empresa"], x=d[col].fillna(0) * signo, name=nombre,
                         orientation="h", marker_color=color, customdata=d[col].fillna(0),
                         hovertemplate="%{y} · " + nombre + ": %{customdata:,.1f} d<extra></extra>"))
fig.add_trace(go.Scatter(y=d["empresa"], x=d["ciclo_caja"], mode="markers", name="Ciclo de caja",
                         marker=dict(symbol="diamond", size=12, color="#6250d6",
                                     line=dict(width=2, color="white")),
                         hovertemplate="%{y} · Ciclo de caja: %{x:,.1f} d<extra></extra>"))
fig.update_layout(title=f"¿De dónde sale el ciclo? · {anio}", barmode="relative", bargap=0.35)
fig.update_xaxes(ticksuffix=" d")
st.plotly_chart(estilo(fig, 360), width="stretch")
st.caption("Ciclo de caja = días de inventario + días de cobro − días de pago. "
           "Target y Dollar General no reportan cuentas por cobrar (0 días).")
