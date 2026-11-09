-- 02_ratios.sql  (DuckDB)
-- Entrada : datos/estados_financieros.csv  (formato largo, de 01_extraer_sec.py)
-- Salida  : datos/ratios.csv               (una fila por empresa y año fiscal:
--           cifras de los estados financieros + indicadores)
-- Correr desde la raíz del proyecto:
--   duckdb -c ".read sql/02_ratios.sql"      (CLI)
--   python scripts/02_calcular_ratios.py     (sin CLI)
--
-- Convenciones: saldos de cierre (no promedios), año de 365 días,
-- ratios en proporción (0.25 = 25 %), días en días, montos en USD.

CREATE OR REPLACE VIEW estados AS
SELECT
    ticker,
    any_value(empresa)      AS empresa,
    anio_fiscal,
    max(fecha_cierre)       AS fecha_cierre,
    -- Estado de resultados
    max(valor) FILTER (WHERE metrica = 'ingresos')                 AS ingresos,
    max(valor) FILTER (WHERE metrica = 'costo_ventas')             AS costo_ventas,
    max(valor) FILTER (WHERE metrica = 'gastos_operativos')        AS gastos_operativos,
    max(valor) FILTER (WHERE metrica = 'depreciacion')             AS depreciacion,
    max(valor) FILTER (WHERE metrica = 'utilidad_operativa')       AS utilidad_operativa,
    -- Algunas empresas reportan intereses netos con signo negativo.
    abs(max(valor) FILTER (WHERE metrica = 'gasto_intereses'))     AS gasto_intereses,
    max(valor) FILTER (WHERE metrica = 'utilidad_antes_impuestos') AS utilidad_antes_impuestos,
    max(valor) FILTER (WHERE metrica = 'impuestos')                AS impuestos,
    max(valor) FILTER (WHERE metrica = 'utilidad_neta')            AS utilidad_neta,
    -- Flujo de efectivo
    max(valor) FILTER (WHERE metrica = 'flujo_operativo')          AS flujo_operativo,
    max(valor) FILTER (WHERE metrica = 'flujo_inversion')          AS flujo_inversion,
    max(valor) FILTER (WHERE metrica = 'flujo_financiamiento')     AS flujo_financiamiento,
    max(valor) FILTER (WHERE metrica = 'capex')                    AS capex,
    max(valor) FILTER (WHERE metrica = 'dividendos')               AS dividendos,
    max(valor) FILTER (WHERE metrica = 'recompra_acciones')        AS recompra_acciones,
    -- Balance general
    max(valor) FILTER (WHERE metrica = 'efectivo')                 AS efectivo,
    max(valor) FILTER (WHERE metrica = 'cuentas_por_cobrar')       AS cuentas_por_cobrar,
    max(valor) FILTER (WHERE metrica = 'inventario')               AS inventario,
    max(valor) FILTER (WHERE metrica = 'activo_corriente')         AS activo_corriente,
    max(valor) FILTER (WHERE metrica = 'propiedades_equipo')       AS propiedades_equipo,
    max(valor) FILTER (WHERE metrica = 'activo_derecho_uso')       AS activo_derecho_uso,
    max(valor) FILTER (WHERE metrica = 'plusvalia')                AS plusvalia,
    max(valor) FILTER (WHERE metrica = 'activo_total')             AS activo_total,
    max(valor) FILTER (WHERE metrica = 'cuentas_por_pagar')        AS cuentas_por_pagar,
    max(valor) FILTER (WHERE metrica = 'gastos_acumulados')        AS gastos_acumulados,
    max(valor) FILTER (WHERE metrica = 'deuda_corto_plazo')        AS deuda_corto_plazo,
    max(valor) FILTER (WHERE metrica = 'pasivo_corriente')         AS pasivo_corriente,
    max(valor) FILTER (WHERE metrica = 'deuda_largo_plazo')        AS deuda_largo_plazo,
    max(valor) FILTER (WHERE metrica = 'pasivo_arrendamiento')     AS pasivo_arrendamiento,
    -- Si la empresa no reporta el total de pasivos, se deriva del balance.
    coalesce(
        max(valor) FILTER (WHERE metrica = 'pasivo_total'),
        max(valor) FILTER (WHERE metrica = 'activo_total')
          - max(valor) FILTER (WHERE metrica = 'patrimonio_total')
    )                                                               AS pasivo_total,
    max(valor) FILTER (WHERE metrica = 'utilidades_retenidas')     AS utilidades_retenidas,
    max(valor) FILTER (WHERE metrica = 'patrimonio')               AS patrimonio,
    max(valor) FILTER (WHERE metrica = 'patrimonio_total')         AS patrimonio_total
FROM read_csv_auto('datos/estados_financieros.csv')
GROUP BY ticker, anio_fiscal;

CREATE OR REPLACE VIEW ratios AS
WITH base AS (
    SELECT
        *,
        ingresos - costo_ventas                                   AS utilidad_bruta,
        utilidad_operativa + coalesce(depreciacion, 0)            AS ebitda,
        flujo_operativo - coalesce(capex, 0)                      AS flujo_caja_libre,
        coalesce(deuda_corto_plazo, 0) + coalesce(deuda_largo_plazo, 0) AS deuda_financiera,
        -- Rentabilidad
        (ingresos - costo_ventas) / nullif(ingresos, 0)           AS margen_bruto,
        gastos_operativos / nullif(ingresos, 0)                   AS gastos_sobre_ventas,
        utilidad_operativa / nullif(ingresos, 0)                  AS margen_operativo,
        utilidad_neta / nullif(ingresos, 0)                       AS margen_neto,
        impuestos / nullif(utilidad_antes_impuestos, 0)           AS tasa_impuesto,
        -- Capital de trabajo
        costo_ventas / nullif(inventario, 0)                      AS rotacion_inventario,
        365 * inventario / nullif(costo_ventas, 0)                AS dias_inventario,
        365 * cuentas_por_cobrar / nullif(ingresos, 0)            AS dias_cobro,
        365 * cuentas_por_pagar / nullif(costo_ventas, 0)         AS dias_pago,
        activo_corriente - pasivo_corriente                       AS capital_trabajo,
        -- Liquidez
        activo_corriente / nullif(pasivo_corriente, 0)            AS razon_corriente,
        (activo_corriente - inventario) / nullif(pasivo_corriente, 0) AS prueba_acida,
        efectivo / nullif(pasivo_corriente, 0)                    AS razon_efectivo,
        -- Endeudamiento
        pasivo_total / nullif(activo_total, 0)                    AS endeudamiento,
        pasivo_total / nullif(patrimonio, 0)                      AS pasivo_patrimonio,
        utilidad_operativa / nullif(gasto_intereses, 0)           AS cobertura_intereses,
        -- Retorno
        utilidad_neta / nullif(patrimonio, 0)                     AS roe,
        utilidad_neta / nullif(activo_total, 0)                   AS roa
    FROM estados
)
SELECT
    *,
    -- Ciclo de conversión de efectivo: días que la caja queda atrapada en
    -- inventario + cobranza, menos los días que financian los proveedores.
    dias_inventario + coalesce(dias_cobro, 0) - dias_pago         AS ciclo_caja,
    ebitda / nullif(ingresos, 0)                                  AS margen_ebitda,
    deuda_financiera - efectivo                                   AS deuda_neta,
    (deuda_financiera - efectivo) / nullif(ebitda, 0)             AS deuda_neta_ebitda,
    flujo_caja_libre / nullif(utilidad_neta, 0)                   AS conversion_caja,
    -- Crecimiento contra el año fiscal anterior de la misma empresa
    ingresos / nullif(lag(ingresos) OVER w, 0) - 1                AS crecimiento_ingresos,
    utilidad_neta / nullif(lag(utilidad_neta) OVER w, 0) - 1      AS crecimiento_utilidad
FROM base
WINDOW w AS (PARTITION BY ticker ORDER BY anio_fiscal)
ORDER BY ticker, anio_fiscal;

COPY (SELECT * FROM ratios) TO 'datos/ratios.csv' (HEADER, DELIMITER ',');

-- Respuesta directa a la pregunta de negocio: ciclo de caja por año.
-- Menor (o negativo) = la cadena convierte su inventario en caja más rápido.
PIVOT (SELECT ticker, anio_fiscal, round(ciclo_caja, 1) AS ciclo_caja FROM ratios)
ON anio_fiscal USING any_value(ciclo_caja)
ORDER BY ticker;
