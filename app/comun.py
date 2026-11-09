"""Funciones compartidas por las páginas del dashboard."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
RATIOS = RAIZ / "datos" / "ratios.csv"

# Color fijo por empresa (no cambia al filtrar). Paleta validada para daltonismo.
COLORES = {
    "WMT": "#2a78d6",   # Walmart
    "TGT": "#eb6834",   # Target
    "COST": "#1baf7a",  # Costco
    "BBY": "#eda100",   # Best Buy
    "DG": "#e87ba4",    # Dollar General
}
# Colores por rol dentro de una misma empresa (series 1-4 de la paleta)
SERIE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
POSITIVO, NEGATIVO, TOTAL = "#1baf7a", "#e34948", "#2a78d6"


# ---------- datos ----------

@st.cache_data
def cargar() -> pd.DataFrame:
    return pd.read_csv(RATIOS).sort_values(["ticker", "anio_fiscal"])


def datos_o_parar() -> pd.DataFrame:
    if not RATIOS.exists():
        st.error("No encuentro datos/ratios.csv. Corre primero scripts/01_extraer_sec.py "
                 "y scripts/02_calcular_ratios.py.")
        st.stop()
    return cargar()


def seleccion(df: pd.DataFrame):
    """Empresa y año elegidos en la barra lateral, y sus filas."""
    ticker = st.session_state["ticker"]
    anio = st.session_state["anio"]
    hist = df[df["ticker"] == ticker].set_index("anio_fiscal")
    fila = hist.loc[anio] if anio in hist.index else None
    previa = hist.loc[anio - 1] if anio - 1 in hist.index else None
    return ticker, anio, hist, fila, previa


def tiene(serie_o_valor) -> bool:
    if isinstance(serie_o_valor, pd.Series):
        return serie_o_valor.notna().any()
    return serie_o_valor is not None and not pd.isna(serie_o_valor)


# ---------- formato (estilo español: 1.234,5) ----------

def num(v, dec: int = 0) -> str:
    if v is None or pd.isna(v):
        return "s/d"
    s = f"{v:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def escala(valores) -> tuple[float, str]:
    """Divisor y unidad según el tamaño: miles de millones o millones de USD."""
    m = pd.Series(valores).abs().max()
    return (1e9, "mil M") if pd.notna(m) and m >= 1e9 else (1e6, "M")


def musd(v, dec: int | None = None) -> str:
    """Monto compacto: US$ 41,7 mil M (miles de millones) o US$ 927 M (millones)."""
    if v is None or pd.isna(v):
        return "s/d"
    div, unidad = escala([v])
    return f"US$ {num(v / div, 1 if dec is None and div == 1e9 else dec or 0)} {unidad}"


def pct(v, dec: int = 1) -> str:
    return "s/d" if v is None or pd.isna(v) else f"{num(v * 100, dec)} %"


def dias(v) -> str:
    return "s/d" if v is None or pd.isna(v) else f"{num(v, 1)} d"


def veces(v) -> str:
    return "s/d" if v is None or pd.isna(v) else f"{num(v, 2)}x"


def var_pct(actual, previo) -> str | None:
    if not tiene(actual) or not tiene(previo) or previo == 0:
        return None
    return f"{num((actual / abs(previo) - 1) * 100, 1)} %"


def var_abs(actual, previo, fmt) -> str | None:
    if not tiene(actual) or not tiene(previo):
        return None
    d = actual - previo
    return ("+" if d >= 0 else "-") + fmt(abs(d))


# ---------- gráficos ----------

def estilo(fig: go.Figure, alto: int = 360, pct_y: bool = False) -> go.Figure:
    fig.update_layout(
        height=alto, margin=dict(l=10, r=10, t=40, b=10), separators=",.",
        legend=dict(orientation="h", y=-0.12, yanchor="top", x=0, title=None),
        hoverlabel=dict(namelength=-1),
        yaxis=dict(gridcolor="rgba(128,128,128,0.15)", zerolinecolor="rgba(128,128,128,0.5)",
                   tickformat=".0%" if pct_y else None, title=None),
        xaxis=dict(showgrid=False, title=None),
    )
    return fig


def barras_anuales(hist: pd.DataFrame, cols: dict, titulo: str, anio: int | None = None,
                   alto: int = 340) -> go.Figure:
    """Barras agrupadas por año, montos en millones. cols = {columna: etiqueta}."""
    fig = go.Figure()
    presentes = [c for c in cols if c in hist and tiene(hist[c])]
    div, unidad = escala(hist[presentes].to_numpy().ravel() if presentes else [])
    formato = ",.1f" if div == 1e9 else ",.0f"
    for i, (col, nombre) in enumerate(cols.items()):
        if col not in presentes:
            continue
        fig.add_trace(go.Bar(
            x=hist.index, y=hist[col] / div, name=nombre, marker_color=SERIE[i % 4],
            hovertemplate="%{x} · " + nombre + ": US$ %{y:" + formato + "} " + unidad
                          + "<extra></extra>",
        ))
    fig.update_layout(title=f"{titulo} (US$ {'miles de millones' if div == 1e9 else 'millones'})",
                      barmode="group", bargap=0.3, bargroupgap=0.08)
    fig.update_xaxes(dtick=1)
    if len(fig.data) == 1:
        fig.update_layout(showlegend=False)
    return estilo(fig, alto)


def lineas_anuales(hist: pd.DataFrame, cols: dict, titulo: str, tipo: str = "pct",
                   alto: int = 340) -> go.Figure:
    """Líneas por año para indicadores de la misma unidad (pct o dias)."""
    fig = go.Figure()
    for i, (col, nombre) in enumerate(cols.items()):
        if col not in hist or not tiene(hist[col]):
            continue
        y = hist[col]
        hover = "%{y:.1%}" if tipo == "pct" else "%{y:,.1f} d" if tipo == "dias" else "%{y:,.2f}x"
        fig.add_trace(go.Scatter(
            x=hist.index, y=y, name=nombre, mode="lines+markers",
            line=dict(color=SERIE[i % 4], width=2), marker=dict(size=8),
            hovertemplate="%{x} · " + nombre + ": " + hover + "<extra></extra>",
        ))
    fig.update_layout(title=titulo, hovermode="x unified")
    fig.update_xaxes(dtick=1)
    if tipo == "dias":
        fig.update_yaxes(ticksuffix=" d")
    if len(fig.data) == 1:
        fig.update_layout(showlegend=False)
    return estilo(fig, alto, pct_y=(tipo == "pct"))


def comparativo(df: pd.DataFrame, anio: int, col: str, titulo: str, tipo: str,
                ticker_sel: str, menor_mejor: bool = False) -> go.Figure:
    """Barras horizontales: las 5 cadenas en un año, la elegida resaltada."""
    d = df[(df["anio_fiscal"] == anio) & df[col].notna()].sort_values(
        col, ascending=not menor_mejor)
    texto = {"pct": pct, "dias": dias, "veces": veces, "musd": musd}[tipo]
    fig = go.Figure(go.Bar(
        y=d["empresa"], x=d[col] / (1e6 if tipo == "musd" else 1), orientation="h",
        marker=dict(color=[COLORES[t] for t in d["ticker"]],
                    opacity=[1 if t == ticker_sel else 0.45 for t in d["ticker"]]),
        text=[texto(v) for v in d[col]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{text}<extra></extra>",
    ))
    fig.update_layout(title=titulo, showlegend=False)
    fig = estilo(fig, alto=60 + 48 * max(len(d), 1))
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=True)
    return fig


def nota(texto: str) -> None:
    st.caption(texto)


# ---------- estados financieros en tabla ----------

def tabla_estado(hist: pd.DataFrame, filas: list, anio: int, n_anios: int,
                 base: str | None, modo: str) -> tuple[pd.DataFrame, "pd.io.formats.style.Styler"]:
    """
    filas = [(etiqueta, columna_o_funcion, es_subtotal)], montos en USD.
    modo: "Montos" | "Análisis vertical" | "Variación anual".
    Devuelve el DataFrame numérico (para descargar) y su versión con formato.
    """
    anios = [a for a in hist.index if anio - n_anios < a <= anio]
    h = hist.loc[anios]
    datos, subtotales = {}, []
    for etiqueta, fuente, subtotal in filas:
        serie = fuente(h) if callable(fuente) else h[fuente]
        datos[etiqueta] = serie
        if subtotal:
            subtotales.append(etiqueta)
    t = pd.DataFrame(datos).T
    t.columns = [str(a) for a in anios]

    if modo == "Análisis vertical" and base:
        b = (h[base] if isinstance(base, str) else base(h)).values
        t = t.div(b, axis=1)
        fmt = lambda v: pct(v)
    elif modo == "Variación anual":
        t = t.T.pct_change(fill_method=None).T.iloc[:, 1:] if t.shape[1] > 1 else t * float("nan")
        fmt = lambda v: pct(v)
    else:
        t = t / 1e6
        fmt = lambda v: num(v)
    estilo_ = (t.style.format(fmt)
               .apply(lambda r: ["background-color: rgba(128,128,128,0.14)" if r.name in subtotales
                                 else "" for _ in r], axis=1))
    return t, estilo_
