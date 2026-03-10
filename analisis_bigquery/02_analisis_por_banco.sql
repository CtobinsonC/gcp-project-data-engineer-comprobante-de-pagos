-- ============================================================
-- 02. ANÁLISIS POR BANCO DESTINO
-- ============================================================

-- Transacciones y monto total por banco
SELECT
  banco_destino,
  COUNT(*)                                    AS num_transacciones,
  ROUND(SUM(monto_transferido), 2)            AS monto_total,
  ROUND(AVG(monto_transferido), 2)            AS monto_promedio,
  MAX(monto_transferido)                      AS monto_maximo
FROM `gcp-project-comprobante.comprobantes_dataset.transacciones_comprobantes`
WHERE monto_transferido IS NOT NULL
GROUP BY banco_destino
ORDER BY monto_total DESC;

-- Participación porcentual por banco (para Pie/Donut chart)
SELECT
  banco_destino,
  COUNT(*)                                                        AS num_transacciones,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)             AS pct_transacciones,
  ROUND(SUM(monto_transferido), 2)                               AS monto_total,
  ROUND(SUM(monto_transferido) * 100.0
        / SUM(SUM(monto_transferido)) OVER (), 2)                AS pct_monto
FROM `gcp-project-comprobante.comprobantes_dataset.transacciones_comprobantes`
WHERE monto_transferido IS NOT NULL
GROUP BY banco_destino
ORDER BY pct_monto DESC;
