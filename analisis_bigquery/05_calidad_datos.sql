-- ============================================================
-- 05. CALIDAD DE DATOS — INTEGRIDAD DEL PIPELINE
-- ============================================================

-- Porcentaje de completitud por campo
SELECT
  COUNT(*)                                                          AS total_registros,
  COUNTIF(banco_destino NOT IN ('No identificado'))                 AS banco_ok,
  COUNTIF(monto_transferido IS NOT NULL)                            AS monto_ok,
  COUNTIF(fecha NOT IN ('No disponible'))                           AS fecha_ok,
  COUNTIF(numero_referencia NOT IN ('No disponible'))               AS referencia_ok,
  COUNTIF(enviado_por NOT IN ('No especificado'))                   AS enviado_ok,

  -- Porcentajes
  ROUND(COUNTIF(banco_destino NOT IN ('No identificado'))
        * 100.0 / COUNT(*), 1)                                      AS pct_banco,
  ROUND(COUNTIF(monto_transferido IS NOT NULL)
        * 100.0 / COUNT(*), 1)                                      AS pct_monto,
  ROUND(COUNTIF(fecha NOT IN ('No disponible'))
        * 100.0 / COUNT(*), 1)                                      AS pct_fecha,
  ROUND(COUNTIF(numero_referencia NOT IN ('No disponible'))
        * 100.0 / COUNT(*), 1)                                      AS pct_referencia
FROM `gcp-project-comprobante.comprobantes_dataset.transacciones_comprobantes`;

-- Registros con algún campo incompleto
SELECT
  archivo_origen,
  banco_destino,
  monto_transferido,
  fecha,
  numero_referencia,
  enviado_por
FROM `gcp-project-comprobante.comprobantes_dataset.transacciones_comprobantes`
WHERE
  banco_destino    = 'No identificado' OR
  monto_transferido IS NULL            OR
  fecha            = 'No disponible'   OR
  numero_referencia = 'No disponible'
ORDER BY archivo_origen;
