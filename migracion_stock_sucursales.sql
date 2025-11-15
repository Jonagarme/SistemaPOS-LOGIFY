-- ==================================================================
-- SCRIPT DE MIGRACION: Implementación de Stock por Sucursal
-- Fecha: 2025-11-14
-- Descripción: Agrega tablas y columnas necesarias para manejar
--              stock independiente por ubicación/sucursal
-- ==================================================================

-- 1. Agregar columna idUbicacion a kardex_movimientos
ALTER TABLE kardex_movimientos 
ADD COLUMN IF NOT EXISTS idUbicacion INT NULL COMMENT 'ID de la ubicación donde ocurrió el movimiento';

-- 2. Agregar columnas a cajas
ALTER TABLE cajas 
ADD COLUMN IF NOT EXISTS activa TINYINT(1) DEFAULT 1 COMMENT 'Indica si la caja está activa';

ALTER TABLE cajas 
ADD COLUMN IF NOT EXISTS idUbicacion INT NULL COMMENT 'ID de la ubicación/sucursal a la que pertenece la caja';

-- 3. Crear tabla para stock por ubicación
CREATE TABLE IF NOT EXISTS inventario_stockubicacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    producto_id INT NOT NULL,
    ubicacion_id INT NOT NULL,
    cantidad DECIMAL(12,2) NOT NULL DEFAULT 0.00 CHECK (cantidad >= 0),
    stock_minimo DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    stock_maximo DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    punto_reorden DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    ultima_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    creadoPor_id INT NULL,
    creadoDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editadoPor_id INT NULL,
    editadoDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Índices
    UNIQUE KEY unique_producto_ubicacion (producto_id, ubicacion_id),
    INDEX idx_producto (producto_id),
    INDEX idx_ubicacion (ubicacion_id),
    INDEX idx_cantidad (cantidad),
    
    -- Claves foráneas
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    FOREIGN KEY (ubicacion_id) REFERENCES inventario_ubicacion(id) ON DELETE CASCADE,
    FOREIGN KEY (creadoPor_id) REFERENCES auth_user(id) ON DELETE RESTRICT,
    FOREIGN KEY (editadoPor_id) REFERENCES auth_user(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Stock de productos por ubicación/sucursal';

-- ==================================================================
-- MIGRACIÓN DE DATOS INICIAL
-- ==================================================================

-- 4. Obtener o crear la ubicación principal
-- Nota: Ajusta el ID del usuario según tu sistema
SET @id_ubicacion_principal = (SELECT id FROM inventario_ubicacion WHERE es_principal = 1 LIMIT 1);
SET @id_usuario_admin = 1; -- Cambiar por el ID de tu usuario administrador

-- Si no existe ubicación principal, crearla
INSERT INTO inventario_ubicacion (codigo, nombre, tipo, activo, es_principal, creadoPor_id, creadoDate)
SELECT 'PRINC', 'Sucursal Principal', 'sucursal', 1, 1, @id_usuario_admin, NOW()
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM inventario_ubicacion WHERE es_principal = 1);

-- Actualizar la variable con el ID correcto
SET @id_ubicacion_principal = (SELECT id FROM inventario_ubicacion WHERE es_principal = 1 LIMIT 1);

-- 5. Migrar stock actual de productos a la ubicación principal
INSERT INTO inventario_stockubicacion (
    producto_id, 
    ubicacion_id, 
    cantidad, 
    stock_minimo,
    punto_reorden,
    creadoPor_id, 
    creadoDate
)
SELECT 
    p.id,
    @id_ubicacion_principal,
    COALESCE(p.stock, 0),
    0, -- stock_minimo por defecto
    0, -- punto_reorden por defecto
    @id_usuario_admin,
    NOW()
FROM productos p
WHERE p.activo = 1
  AND NOT EXISTS (
      SELECT 1 FROM inventario_stockubicacion su 
      WHERE su.producto_id = p.id 
        AND su.ubicacion_id = @id_ubicacion_principal
  );

-- 6. Asignar ubicación principal a todas las cajas existentes
UPDATE cajas 
SET idUbicacion = @id_ubicacion_principal
WHERE idUbicacion IS NULL;

-- 7. Actualizar movimientos de kardex sin ubicación a la ubicación principal
UPDATE kardex_movimientos
SET idUbicacion = @id_ubicacion_principal
WHERE idUbicacion IS NULL;

-- ==================================================================
-- VERIFICACIÓN
-- ==================================================================

-- Verificar que se crearon los registros correctamente
SELECT 
    'Total productos' as concepto, 
    COUNT(*) as cantidad 
FROM productos WHERE activo = 1

UNION ALL

SELECT 
    'Stocks creados por ubicación' as concepto, 
    COUNT(*) as cantidad 
FROM inventario_stockubicacion

UNION ALL

SELECT 
    'Ubicación principal' as concepto,
    COUNT(*) as cantidad
FROM inventario_ubicacion WHERE es_principal = 1

UNION ALL

SELECT 
    'Cajas con ubicación asignada' as concepto,
    COUNT(*) as cantidad
FROM cajas WHERE idUbicacion IS NOT NULL;

-- Mostrar resumen de stock por ubicación
SELECT 
    u.nombre as ubicacion,
    COUNT(DISTINCT su.producto_id) as total_productos,
    SUM(su.cantidad) as total_unidades,
    SUM(CASE WHEN su.cantidad <= su.stock_minimo AND su.stock_minimo > 0 THEN 1 ELSE 0 END) as productos_stock_bajo
FROM inventario_ubicacion u
LEFT JOIN inventario_stockubicacion su ON u.id = su.ubicacion_id
WHERE u.activo = 1
GROUP BY u.id, u.nombre;

-- ==================================================================
-- NOTAS IMPORTANTES
-- ==================================================================
-- 
-- 1. Después de ejecutar este script, ejecuta las migraciones de Django:
--    python manage.py makemigrations
--    python manage.py migrate
--
-- 2. Si tienes múltiples sucursales, crea las ubicaciones adicionales desde
--    el admin de Django o la interfaz de gestión de ubicaciones
--
-- 3. Los nuevos productos creados automáticamente tendrán stock 0 en todas
--    las ubicaciones hasta que se registren compras o transferencias
--
-- 4. Recuerda actualizar los permisos de usuarios para que puedan gestionar
--    transferencias entre sucursales
--
-- ==================================================================
