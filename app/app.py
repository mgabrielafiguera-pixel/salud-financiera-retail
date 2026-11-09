"""
Dashboard contable: salud financiera de cadenas de retail (10-K de la SEC).
Lee datos/ratios.csv (generado por scripts/02_calcular_ratios.py).

Correr desde la raíz del proyecto:
    streamlit run app/app.py
"""

import streamlit as st

from comun import datos_o_parar

st.set_page_config(page_title="Dashboard contable retail", page_icon=":material/analytics:", layout="wide")

df = datos_o_parar()

# Filtros globales: se comparten entre todas las páginas
empresas = df.drop_duplicates("ticker").set_index("ticker")["empresa"].to_dict()
anios = sorted(df["anio_fiscal"].unique())
with st.sidebar:
    st.markdown("### Filtros")
    st.selectbox("Empresa", list(empresas), format_func=lambda t: f"{empresas[t]} ({t})",
                 key="ticker")
    st.selectbox("Año fiscal", anios[::-1], key="anio")
    st.caption("Fuente: 10-K de la SEC (EDGAR, API companyfacts). «mil M» = miles de millones "
               "de USD; las tablas contables van en millones. Año fiscal = año calendario que más "
               "cubre el ejercicio.")

paginas = [
    st.Page("paginas/1_resumen.py", title="Resumen ejecutivo", icon=":material/dashboard:", default=True),
    st.Page("paginas/2_ingresos_gastos.py", title="Ingresos y gastos", icon=":material/payments:"),
    st.Page("paginas/3_cuentas_cobrar.py", title="Cuentas por cobrar", icon=":material/call_received:"),
    st.Page("paginas/4_cuentas_pagar.py", title="Cuentas por pagar", icon=":material/call_made:"),
    st.Page("paginas/5_flujo_efectivo.py", title="Bancos y flujo de efectivo", icon=":material/account_balance:"),
    st.Page("paginas/6_estado_resultados.py", title="Estado de resultados", icon=":material/receipt_long:"),
    st.Page("paginas/7_balance_general.py", title="Balance general", icon=":material/balance:"),
    st.Page("paginas/8_ciclo_caja.py", title="Ciclo de caja (comparativo)", icon=":material/autorenew:"),
]
st.navigation(paginas).run()
