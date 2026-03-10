-- ============================================================
-- 03. ANÁLISIS TEMPORAL
-- ============================================================

-- Transacciones por tipo de comprobante (según nombre de archivo)
SELECT
  CASE
    WHEN archivo_origen LIKE '%nequi_app%'    THEN 'Nequi App'
    WHEN archivo_origen LIKE '%nequi_recibo%' THEN 'Nequi Recibo'
    WHEN archivo_origen LIKE '%davivienda%'   THEN 'Davivienda'
    ELSE 'Otro'
  END                                         AS tipo_comprobante,
  COUNT(*)                                    AS num_transacciones,
  ROUND(SUM(monto_transferido), 2)            AS monto_total
FROM `gcp-project-comprobante.comprobantes_dataset.transacciones_comprobantes`
GROUP BY tipo_comprobante
ORDER BY num_transacciones DESC;

-- Transacciones por fecha de carga (cuándo fueron procesadas)
SELECT
  DATE(fecha_carga)                           AS fecha_procesamiento,
  COUNT(*)                                    AS num_transacciones,
  ROUND(SUM(monto_transferido), 2)            AS monto_total
FROM `gcp-project-comprobante.comprobantes_dataset.transacciones_comprobantes`
GROUP BY fecha_procesamiento
ORDER BY fecha_procesamiento DESC;
