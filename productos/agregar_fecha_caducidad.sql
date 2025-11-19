-- Agregar campo fecha de caducidad a la tabla productos
-- Ejecutar en MySQL Workbench

USE logipharmbd;

-- Agregar columna fecha de caducidad
ALTER TABLE productos 
ADD COLUMN fechaCaducidad DATE NULL AFTER registroSanitario,
ADD INDEX idx_fecha_caducidad (fechaCaducidad);

-- Verificar que se agregó correctamente
DESCRIBE productos;
