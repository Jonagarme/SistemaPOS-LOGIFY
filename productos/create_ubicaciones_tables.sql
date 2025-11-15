-- Crear tablas para ubicación de productos en perchas
-- Ejecutar este script directamente en MySQL

USE sistema_pos;

-- Tabla de secciones
CREATE TABLE IF NOT EXISTS productos_seccion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    color VARCHAR(7) DEFAULT '#007bff',
    orden INT DEFAULT 0,
    activo TINYINT(1) DEFAULT 1,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_nombre_activo (nombre, activo)
);

-- Tabla de perchas
CREATE TABLE IF NOT EXISTS productos_percha (
    id INT AUTO_INCREMENT PRIMARY KEY,
    seccion_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    filas INT DEFAULT 5,
    columnas INT DEFAULT 10,
    activo TINYINT(1) DEFAULT 1,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (seccion_id) REFERENCES productos_seccion(id) ON DELETE CASCADE,
    UNIQUE KEY unique_nombre_seccion_activo (seccion_id, nombre, activo)
);

-- Tabla de ubicación de productos
CREATE TABLE IF NOT EXISTS productos_ubicacionproducto (
    id INT AUTO_INCREMENT PRIMARY KEY,
    producto_id INT NOT NULL,
    percha_id INT NOT NULL,
    fila INT NOT NULL,
    columna INT NOT NULL,
    cantidad_maxima INT DEFAULT 50,
    cantidad_actual INT DEFAULT 0,
    observaciones TEXT,
    activo TINYINT(1) DEFAULT 1,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (percha_id) REFERENCES productos_percha(id) ON DELETE CASCADE,
    UNIQUE KEY unique_producto_activo (producto_id, activo),
    UNIQUE KEY unique_posicion_percha_activo (percha_id, fila, columna, activo)
);

-- Insertar datos de ejemplo
INSERT INTO productos_seccion (nombre, descripcion, color, orden) VALUES
('Medicamentos', 'Medicamentos recetados y de venta libre', '#dc3545', 1),
('Cosméticos', 'Productos de belleza y cuidado personal', '#28a745', 2),
('Higiene', 'Productos de higiene personal', '#007bff', 3),
('Vitaminas', 'Suplementos vitamínicos y nutricionales', '#ffc107', 4);

INSERT INTO productos_percha (seccion_id, nombre, descripcion, filas, columnas) VALUES
(1, 'Percha A1', 'Analgésicos y antiinflamatorios', 5, 8),
(1, 'Percha A2', 'Antibióticos y antivirales', 5, 8),
(2, 'Percha B1', 'Maquillaje y fragancias', 4, 10),
(2, 'Percha B2', 'Cremas y lociones', 4, 10),
(3, 'Percha C1', 'Champús y acondicionadores', 6, 6),
(3, 'Percha C2', 'Jabones y desodorantes', 6, 6),
(4, 'Percha D1', 'Vitaminas A-M', 5, 8),
(4, 'Percha D2', 'Vitaminas N-Z', 5, 8);

-- Crear índices para optimizar consultas
CREATE INDEX idx_ubicacion_producto ON productos_ubicacionproducto(producto_id);
CREATE INDEX idx_ubicacion_percha ON productos_ubicacionproducto(percha_id);
CREATE INDEX idx_percha_seccion ON productos_percha(seccion_id);
CREATE INDEX idx_seccion_activo ON productos_seccion(activo);
CREATE INDEX idx_percha_activo ON productos_percha(activo);
CREATE INDEX idx_ubicacion_activo ON productos_ubicacionproducto(activo);