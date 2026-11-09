"""
01_extraer_sec.py
Descarga los estados financieros anuales (10-K) de cadenas de retail desde la
API companyfacts de la SEC (EDGAR/XBRL) y los guarda en formato largo:

    datos/estados_financieros.csv
    empresa | ticker | cik | anio_fiscal | fecha_cierre | metrica | valor |
    concepto_xbrl | formulario | fecha_presentacion | accn

Reglas de selección
- Solo cifras de formularios 10-K / 10-K/A.
- Métricas de flujo (ingresos, costo de ventas, utilidad): periodos de ~1 año
  (330 a 380 días, cubre años de 52 y 53 semanas).
- Métricas de saldo (inventario, CxC, CxP, activos...): valor a la fecha de
  cierre fiscal, definida por el periodo anual de ingresos.
- Si una cifra aparece en varios 10-K (p. ej. el año anterior se repite en el
  10-K siguiente), se usa la presentación más reciente (recoge reexpresiones).
- Cada métrica tiene una lista de etiquetas XBRL en orden de prioridad; se toma
  la primera que tenga dato para ese año y se registra cuál se usó.

anio_fiscal: año calendario que más cubre el ejercicio. Un cierre en enero o
febrero de 2025 se asigna a 2024 (Walmart lo llama "fiscal 2025", Target
"2024"); un cierre en agosto/septiembre de 2025 (Costco) se asigna a 2025.

La SEC exige un User-Agent con nombre y correo:
    export SEC_USER_AGENT="Nombre Apellido tu_correo@dominio.com"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[1]
URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

EMPRESAS = {
    "WMT": ("Walmart", 104169),
    "TGT": ("Target", 27419),
    "COST": ("Costco", 909832),
    "BBY": ("Best Buy", 764478),
    "DG": ("Dollar General", 29534),
}

# métrica -> (tipo, [etiquetas us-gaap en orden de prioridad])
METRICAS = {
    "ingresos": ("flujo", [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
    ]),
    "costo_ventas": ("flujo", [
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfGoodsSold",
        "CostOfGoodsSoldExcludingDepreciationDepletionAndAmortization",
    ]),
    "utilidad_neta": ("flujo", [
        "NetIncomeLoss",
        "ProfitLoss",
        # Target FY2019 solo la reportó así (3.281 MM = utilidad neta total)
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ]),
    "gastos_operativos": ("flujo", [
        "SellingGeneralAndAdministrativeExpense",
        "SellingGeneralAndAdministrativeExpenseExcludingDepreciation",
    ]),
    "depreciacion": ("flujo", [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "Depreciation",
    ]),
    "utilidad_operativa": ("flujo", ["OperatingIncomeLoss"]),
    "gasto_intereses": ("flujo", [
        "InterestExpense",
        "InterestExpenseNonoperating",
        "InterestExpenseDebt",
        "InterestIncomeExpenseNonoperatingNet",  # neto; signo se normaliza en SQL
        "InterestExpenseNet",
    ]),
    "utilidad_antes_impuestos": ("flujo", [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",
    ]),
    "impuestos": ("flujo", ["IncomeTaxExpenseBenefit"]),
    "flujo_operativo": ("flujo", [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ]),
    "flujo_inversion": ("flujo", [
        "NetCashProvidedByUsedInInvestingActivities",
        "NetCashProvidedByUsedInInvestingActivitiesContinuingOperations",
    ]),
    "flujo_financiamiento": ("flujo", [
        "NetCashProvidedByUsedInFinancingActivities",
        "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations",
    ]),
    "capex": ("flujo", [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ]),
    "dividendos": ("flujo", [
        "PaymentsOfDividendsCommonStock",
        "PaymentsOfDividends",
    ]),
    "recompra_acciones": ("flujo", [
        "PaymentsForRepurchaseOfCommonStock",
        "PaymentsForRepurchaseOfEquity",
    ]),
    "inventario": ("saldo", [
        "InventoryNet",
        "RetailRelatedInventoryMerchandise",
        "InventoryFinishedGoodsNetOfReserves",
        "InventoryFinishedGoods",
    ]),
    "cuentas_por_cobrar": ("saldo", [
        "AccountsReceivableNetCurrent",
        "ReceivablesNetCurrent",
        "AccountsNotesAndLoansReceivableNetCurrent",
    ]),
    "cuentas_por_pagar": ("saldo", [
        "AccountsPayableCurrent",
        "AccountsPayableTradeCurrent",
    ]),
    "efectivo": ("saldo", [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ]),
    "propiedades_equipo": ("saldo", [
        "PropertyPlantAndEquipmentNet",
        "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization",
    ]),
    "activo_derecho_uso": ("saldo", ["OperatingLeaseRightOfUseAsset"]),
    "plusvalia": ("saldo", ["Goodwill"]),
    "deuda_corto_plazo": ("saldo", [
        "LongTermDebtCurrent",
        "DebtCurrent",
        "LongTermDebtAndCapitalLeaseObligationsCurrent",
        "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths",
    ]),
    "deuda_largo_plazo": ("saldo", [
        "LongTermDebtNoncurrent",
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
        "LongTermDebt",
    ]),
    "pasivo_arrendamiento": ("saldo", ["OperatingLeaseLiabilityNoncurrent"]),
    "gastos_acumulados": ("saldo", [
        "AccruedLiabilitiesCurrent",
        "AccruedLiabilitiesAndOtherLiabilities",
        "OtherAccruedLiabilitiesCurrent",
        "EmployeeRelatedLiabilitiesCurrent",
    ]),
    "utilidades_retenidas": ("saldo", ["RetainedEarningsAccumulatedDeficit"]),
    "activo_corriente": ("saldo", ["AssetsCurrent"]),
    "pasivo_corriente": ("saldo", ["LiabilitiesCurrent"]),
    "activo_total": ("saldo", ["Assets"]),
    # Varias empresas (p. ej. Walmart) no reportan el total de pasivos;
    # el SQL lo deriva como activo_total - patrimonio_total.
    "pasivo_total": ("saldo", ["Liabilities"]),
    "patrimonio": ("saldo", [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ]),
    "patrimonio_total": ("saldo", [
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "StockholdersEquity",
    ]),
}

FORMULARIOS = {"10-K", "10-K/A"}


def descargar(cik: int, user_agent: str, cache: Path, refrescar: bool) -> dict:
    """Descarga companyfacts (o lo lee de caché en datos/raw/)."""
    archivo = cache / f"CIK{cik:010d}.json"
    if archivo.exists() and not refrescar:
        return json.loads(archivo.read_text())
    r = requests.get(URL.format(cik=cik), headers={"User-Agent": user_agent}, timeout=60)
    r.raise_for_status()
    cache.mkdir(parents=True, exist_ok=True)
    archivo.write_text(r.text)
    time.sleep(0.2)  # la SEC permite máx. 10 solicitudes/segundo
    return r.json()


def hechos(facts: dict, concepto: str) -> pd.DataFrame:
    """Todas las cifras en USD de una etiqueta us-gaap, solo de 10-K."""
    unidades = facts.get("facts", {}).get("us-gaap", {}).get(concepto, {}).get("units", {})
    df = pd.DataFrame(unidades.get("USD", []))
    if df.empty:
        return df
    df = df[df["form"].isin(FORMULARIOS)].copy()
    df["end"] = pd.to_datetime(df["end"])
    df["filed"] = pd.to_datetime(df["filed"])
    if "start" in df:
        df["start"] = pd.to_datetime(df["start"])
    df["concepto_xbrl"] = concepto
    return df


def mas_reciente(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por fecha de cierre: la presentación más reciente."""
    return df.sort_values("filed").drop_duplicates("end", keep="last")


def anio_fiscal(fecha: pd.Timestamp) -> int:
    return fecha.year if fecha.month >= 7 else fecha.year - 1


def cierres_fiscales(facts: dict) -> pd.Series:
    """Fechas de cierre anual, tomadas de los periodos anuales de ingresos."""
    fechas = set()
    for concepto in METRICAS["ingresos"][1]:
        df = hechos(facts, concepto)
        if df.empty or "start" not in df:
            continue
        dias = (df["end"] - df["start"]).dt.days
        fechas.update(df.loc[dias.between(330, 380), "end"])
    return pd.Series(sorted(fechas), dtype="datetime64[ns]")


def extraer_empresa(ticker: str, nombre: str, cik: int, facts: dict,
                    desde: int, hasta: int) -> pd.DataFrame:
    cierres = cierres_fiscales(facts)
    cierres = cierres[cierres.map(anio_fiscal).between(desde, hasta)]
    filas = []
    for metrica, (tipo, conceptos) in METRICAS.items():
        pendientes = set(cierres)
        for concepto in conceptos:  # prioridad: la primera etiqueta con dato gana
            if not pendientes:
                break
            df = hechos(facts, concepto)
            if df.empty:
                continue
            if tipo == "flujo":
                if "start" not in df:
                    continue
                dias = (df["end"] - df["start"]).dt.days
                df = df[dias.between(330, 380)]
            else:
                # Un saldo sin 'start' es instantáneo; descarta cualquier duración.
                if "start" in df:
                    df = df[df["start"].isna()]
            df = mas_reciente(df[df["end"].isin(pendientes)])
            for _, f in df.iterrows():
                filas.append({
                    "empresa": nombre,
                    "ticker": ticker,
                    "cik": cik,
                    "anio_fiscal": anio_fiscal(f["end"]),
                    "fecha_cierre": f["end"].date(),
                    "metrica": metrica,
                    "valor": f["val"],
                    "concepto_xbrl": concepto,
                    "formulario": f["form"],
                    "fecha_presentacion": f["filed"].date(),
                    "accn": f["accn"],
                })
                pendientes.discard(f["end"])
    if ticker == "DG":
        ingresos_por_anio = {
            fila["anio_fiscal"]: fila
            for fila in filas
            if fila["metrica"] == "ingresos"
        }
        recompra_reportada = {
            fila["anio_fiscal"]
            for fila in filas
            if fila["metrica"] == "recompra_acciones"
        }
        for anio in (2023, 2024, 2025):
            if anio not in ingresos_por_anio or anio in recompra_reportada:
                continue
            fila_ingresos = ingresos_por_anio[anio]
            filas.append({
                **fila_ingresos,
                "metrica": "recompra_acciones",
                "valor": 0,
                "concepto_xbrl": None,
            })
    return pd.DataFrame(filas)


def cargar_env(archivo: Path = RAIZ / ".env") -> None:
    """Carga variables de .env (sin dependencias) si no están ya definidas."""
    if not archivo.exists():
        return
    for linea in archivo.read_text().splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def main() -> int:
    cargar_env()
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--desde", type=int, default=2019)
    p.add_argument("--hasta", type=int, default=2025)
    p.add_argument("--salida", type=Path, default=RAIZ / "datos" / "estados_financieros.csv")
    p.add_argument("--cache", type=Path, default=RAIZ / "datos" / "raw")
    p.add_argument("--refrescar", action="store_true", help="ignora la caché y vuelve a descargar")
    args = p.parse_args()

    user_agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if not user_agent or "@" not in user_agent:
        print("Falta SEC_USER_AGENT: copia .env.example como .env y pon tu nombre y correo.",
              file=sys.stderr)
        return 1

    partes = []
    for ticker, (nombre, cik) in EMPRESAS.items():
        facts = descargar(cik, user_agent, args.cache, args.refrescar)
        df = extraer_empresa(ticker, nombre, cik, facts, args.desde, args.hasta)
        print(f"{ticker:5} {nombre:15} {df['anio_fiscal'].nunique() if len(df) else 0} años, {len(df)} cifras")
        partes.append(df)

    datos = pd.concat(partes, ignore_index=True).sort_values(["ticker", "anio_fiscal", "metrica"])
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    datos.to_csv(args.salida, index=False)

    # Control de calidad: qué falta por empresa-año
    esperado = pd.MultiIndex.from_product(
        [datos["ticker"].unique(), sorted(datos["anio_fiscal"].unique()), list(METRICAS)])
    presente = pd.MultiIndex.from_frame(datos[["ticker", "anio_fiscal", "metrica"]])
    faltantes = esperado.difference(presente)
    print(f"\nGuardado: {args.salida} ({len(datos)} filas)")
    if len(faltantes):
        print(f"Faltan {len(faltantes)} cifras (pasivo_total se deriva en SQL si falta):")
        for t, a, m in faltantes:
            print(f"  {t} {a} {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
