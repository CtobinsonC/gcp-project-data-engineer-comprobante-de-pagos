-- ============================================================
-- QUERIES ANALÍTICAS — COMPROBANTES DE PAGO
-- BigQuery: gcp-project-comprobante.comprobantes_dataset
-- Tabla: transacciones_comprobantes
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- 01. KPIs GENERALES
-- ─────────────────────────────────────────────────────────────

-- Total de transacciones procesadas
SELECT COUNT(*) AS total_transacciones
FROM `gcp-project-comprobante.comprobantes_dataset.transacciones_comprobantes`;

-- Monto total transferido
SELECT
  COUNT(*)                                    AS total_transacciones,
  ROUND(SUM(monto_transferido), 2)            AS monto_total,
  ROUND(AVG(monto_transferido), 2)            AS monto_promedio,
  MAX(monto_transferido)                      AS monto_maximo,
  MIN(monto_transferido)                      AS monto_minimo
FROM `gcp-project-comprobante.comprobantes_dataset.transacciones_comprobantes`
WHERE monto_transferido IS NOT NULL;
