-- ============================================================
-- 04. DISTRIBUCIÓN DE MONTOS POR RANGO
-- ============================================================

-- Clasificación de transacciones por rango de monto
SELECT
  CASE
    WHEN monto_transferido < 100000              THEN '< $100.000'
    WHEN monto_transferido < 500000              THEN '$100.000 - $500.000'
    WHEN monto_transferido < 1000000             THEN '$500.000 - $1.000.000'
    WHEN monto_transferido < 2000000             THEN '$1.000.000 - $2.000.000'
    ELSE '> $2.000.000'
  END                                            AS rango_monto,
  COUNT(*)                                       AS num_transacciones,
  ROUND(SUM(monto_transferido), 2)               AS monto_total,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct
FROM `gcp-project-comprobante.comprobantes_dataset.transacciones_comprobantes`
WHERE monto_transferido IS NOT NULL
GROUP BY rango_monto
ORDER BY MIN(monto_transferido);

-- Top 10 transacciones más altas
SELECT
  archivo_origen,
  banco_destino,
  monto_transferido,
  fecha,
  numero_referencia
FROM `gcp-project-comprobante.comprobantes_dataset.transacciones_comprobantes`
WHERE monto_transferido IS NOT NULL
ORDER BY monto_transferido DESC
LIMIT 10;
