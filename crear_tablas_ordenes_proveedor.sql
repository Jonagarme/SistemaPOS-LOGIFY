-- Crear tablas para órdenes de compra a proveedores

-- Tabla principal de órdenes
CREATE TABLE IF NOT EXISTS ordenes_compra_proveedor (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numero_orden VARCHAR(20) UNIQUE NOT NULL COMMENT 'Número único de orden (ej: ORD-2025-001)',
    proveedor_id INT UNSIGNED NOT NULL,
    fecha_orden DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_entrega_estimada DATE NULL,
    
    subtotal DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    iva DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    total DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    
    estado ENUM('BORRADOR', 'ENVIADA', 'CONFIRMADA', 'RECIBIDA', 'CANCELADA') NOT NULL DEFAULT 'BORRADOR',
    observaciones TEXT NULL,
    
    enviada_whatsapp TINYINT(1) NOT NULL DEFAULT 0,
    fecha_envio_whatsapp DATETIME NULL,
    
    creado_por INT NOT NULL,
    creado_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editado_por INT NULL,
    editado_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    anulado TINYINT(1) NOT NULL DEFAULT 0,
    
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
    INDEX idx_proveedor (proveedor_id),
    INDEX idx_estado (estado),
    INDEX idx_fecha_orden (fecha_orden)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Órdenes de compra a proveedores';

-- Tabla de detalles de orden
CREATE TABLE IF NOT EXISTS detalles_orden_proveedor (
    id INT AUTO_INCREMENT PRIMARY KEY,
    orden_id INT NOT NULL,
    producto_id BIGINT UNSIGNED NOT NULL,
    
    cantidad DECIMAL(12,2) NOT NULL,
    precio_unitario DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    subtotal DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    
    observaciones VARCHAR(500) NULL,
    
    FOREIGN KEY (orden_id) REFERENCES ordenes_compra_proveedor(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    UNIQUE KEY unique_orden_producto (orden_id, producto_id),
    INDEX idx_producto (producto_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Detalle de productos en órdenes';
