import plotly.graph_objects as go
import streamlit as st

from comun import SERIE, cargar, estilo, musd, pct, seleccion, tabla_estado, veces


def resto(total, *partes):
    """Otros = total − suma de las partes reportadas."""
    def f(h):
        r = h[total].copy()
        for p_ in partes:
            r = r - h[p_].fillna(0)
        return r
    return f


df = cargar()
ticker, anio, hist, f, p = seleccion(df)
if f is None:
    st.warning("No hay datos para esa empresa y año.")
    st.stop()

st.title(f"Balance general · {f['empresa']}")

c1, c2 = st.columns([3, 1])
modo = c1.radio("Vista", ["Montos", "Análisis vertical", "Variación anual"], horizontal=True)
n = c2.number_input("Años a mostrar", 2, 7, 5)

filas = [
    ("Efectivo y equivalentes", "efectivo", False),
    ("Cuentas por cobrar", "cuentas_por_cobrar", False),
    ("Inventario", "inventario", False),
    ("Otros activos corrientes",
     resto("activo_corriente", "efectivo", "cuentas_por_cobrar", "inventario"), False),
    ("Activo corriente", "activo_corriente", True),
    ("Propiedades y equipo, neto", "propiedades_equipo", False),
    ("Activos por derecho de uso", "activo_derecho_uso", False),
    ("Plusvalía", "plusvalia", False),
    ("Otros activos no corrientes",
     resto("activo_total", "activo_corriente", "propiedades_equipo", "activo_derecho_uso",
           "plusvalia"), False),
    ("ACTIVO TOTAL", "activo_total", True),
    ("Cuentas por pagar", "cuentas_por_pagar", False),
    ("Gastos acumulados", "gastos_acumulados", False),
    ("Deuda de corto plazo", "deuda_corto_plazo", False),
    ("Otros pasivos corrientes",
     resto("pasivo_corriente", "cuentas_por_pagar", "gastos_acumulados", "deuda_corto_plazo"),
     False),
    ("Pasivo corriente", "pasivo_corriente", True),
    ("Deuda de largo plazo", "deuda_largo_plazo", False),
    ("Pasivo por arrendamientos", "pasivo_arrendamiento", False),
    ("Otros pasivos no corrientes",
     resto("pasivo_total", "pasivo_corriente", "deuda_largo_plazo", "pasivo_arrendamiento"),
     False),
    ("PASIVO TOTAL", "pasivo_total", True),
    ("Utilidades retenidas", "utilidades_retenidas", False),
    ("Otros componentes del patrimonio", resto("patrimonio_total", "utilidades_retenidas"), False),
    ("PATRIMONIO TOTAL", "patrimonio_total", True),
    ("PASIVO + PATRIMONIO", lambda h: h["pasivo_total"] + h["patrimonio_total"], True),
]
datos, tabla = tabla_estado(hist, filas, anio, n, "activo_total", modo)
st.caption({"Montos": "US$ millones, saldos al cierre de cada año fiscal.",
             "Análisis vertical": "Cada línea como % del activo total.",
             "Variación anual": "Cambio % de cada línea contra el cierre anterior."}[modo])
st.dataframe(tabla, width="stretch", height=35 * (len(filas) + 1) + 3)
st.download_button("Descargar tabla (CSV)", datos.to_csv().encode("utf-8"),
                   f"balance_general_{ticker}.csv", "text/csv")

# Composición: activos vs. financiamiento
activos = [("Efectivo", f["efectivo"]), ("Cuentas por cobrar", f["cuentas_por_cobrar"]),
           ("Inventario", f["inventario"]),
           ("Otros activos", f["activo_total"] - f[["efectivo", "cuentas_por_cobrar",
                                                     "inventario"]].fillna(0).sum())]
fuentes = [("Proveedores", f["cuentas_por_pagar"]),
           ("Deuda financiera", f["deuda_financiera"]),
           ("Otros pasivos", f["pasivo_total"] - f[["cuentas_por_pagar",
                                                     "deuda_financiera"]].fillna(0).sum()),
           ("Patrimonio", f["patrimonio_total"])]
fig = go.Figure()
for i, (nombre, val) in enumerate(activos):
    fig.add_trace(go.Bar(y=["Activos"], x=[(val or 0) / 1e9], name=nombre, orientation="h",
                         marker=dict(color=SERIE[i], line=dict(width=2, color="rgba(0,0,0,0)")),
                         legendgroup="a", legendgrouptitle_text="Activos",
                         hovertemplate=nombre + ": US$ %{x:,.1f} mil M<extra></extra>"))
colores_f = ["#6250d6", "#e34948", "#9aa0a6", "#008300"]
for i, (nombre, val) in enumerate(fuentes):
    fig.add_trace(go.Bar(y=["Pasivo + patrimonio"], x=[(val or 0) / 1e9], name=nombre,
                         orientation="h", marker_color=colores_f[i],
                         legendgroup="f", legendgrouptitle_text="Financiamiento",
                         hovertemplate=nombre + ": US$ %{x:,.1f} mil M<extra></extra>"))
fig.update_layout(title=f"¿Cómo se financian los activos? · {anio} (US$ miles de millones)",
                  barmode="stack", bargap=0.35)
fig = estilo(fig, 300)
fig.update_layout(legend=dict(orientation="h", y=-0.3, yanchor="top"))
st.plotly_chart(fig, width="stretch")

cuadra = abs(f["activo_total"] - f["pasivo_total"] - f["patrimonio_total"]) < 1e6
with st.container(border=True):
    st.markdown(
        f"**Control {anio}:** activo = pasivo + patrimonio {'✅ cuadra' if cuadra else '❌ no cuadra'} · "
        f"endeudamiento {pct(f['endeudamiento'])} · razón corriente {veces(f['razon_corriente'])} · "
        f"deuda neta {musd(f['deuda_neta'])} · deuda neta / EBITDA {veces(f['deuda_neta_ebitda'])}.")
st.caption("Las líneas «otros» se calculan como total menos las partidas reportadas. Si la "
           "empresa no reporta el pasivo total, se deriva como activo − patrimonio.")
