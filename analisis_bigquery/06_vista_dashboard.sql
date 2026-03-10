-- ============================================================
-- 06. VISTA CONSOLIDADA PARA POWER BI / LOOKER STUDIO
-- ============================================================
-- Esta query genera la vista principal lista para conectar
-- directamente al dashboard. Incluye todas las métricas
-- calculadas en una sola tabla desnormalizada.

SELECT
  -- Identificación
  archivo_origen,
  numero_referencia,

  -- Banco y monto
  banco_destino,
  monto_transferido,

  -- Clasificación del monto (para filtros en dashboard)
  CASE
    WHEN monto_transferido < 100000    THEN '1. Menos de $100K'
    WHEN monto_transferido < 500000    THEN '2. $100K - $500K'
    WHEN monto_transferido < 1000000   THEN '3. $500K - $1M'
    WHEN monto_transferido < 2000000   THEN '4. $1M - $2M'
    ELSE                                    '5. Más de $2M'
  END AS rango_monto,

  -- Clasificación del tipo de comprobante
  CASE
    WHEN archivo_origen LIKE '%nequi_app%'    THEN 'Nequi App'
    WHEN archivo_origen LIKE '%nequi_recibo%' THEN 'Nequi Recibo'
    WHEN archivo_origen LIKE '%davivienda%'   THEN 'Davivienda'
    ELSE 'Otro'
  END AS tipo_comprobante,

  -- Fecha y remitente
  fecha,
  enviado_por,

  -- Completitud del registro (para métricas de calidad)
  CASE
    WHEN banco_destino = 'No identificado' OR
         monto_transferido IS NULL         OR
         fecha = 'No disponible'           OR
         numero_referencia = 'No disponible'
    THEN 'Incompleto'
    ELSE 'Completo'
  END AS estado_registro,

  -- Fecha de procesamiento
  DATE(fecha_carga) AS fecha_procesamiento

FROM `gcp-project-comprobante.comprobantes_dataset.transacciones_comprobantes`
ORDER BY fecha_carga DESC;
