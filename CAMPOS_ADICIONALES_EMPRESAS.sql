# Campos adicionales sugeridos para la tabla empresas
# Puedes agregar estos campos en el futuro para hacer más configurable el sistema

ALTER TABLE empresas ADD COLUMN eslogan VARCHAR(300) NULL COMMENT 'Eslogan de la empresa';
ALTER TABLE empresas ADD COLUMN codigo_establecimiento VARCHAR(3) DEFAULT '001' COMMENT 'Código de establecimiento SRI';
ALTER TABLE empresas ADD COLUMN codigo_punto_emision VARCHAR(3) DEFAULT '001' COMMENT 'Código punto de emisión SRI';
ALTER TABLE empresas ADD COLUMN ambiente_sri ENUM('PRUEBAS', 'PRODUCCION') DEFAULT 'PRUEBAS' COMMENT 'Ambiente SRI';
ALTER TABLE empresas ADD COLUMN tipo_emision ENUM('NORMAL', 'CONTINGENCIA') DEFAULT 'NORMAL' COMMENT 'Tipo de emisión';
ALTER TABLE empresas ADD COLUMN telefono_atencion VARCHAR(50) NULL COMMENT 'Teléfono de atención al cliente';
ALTER TABLE empresas ADD COLUMN mensaje_final VARCHAR(200) NULL COMMENT 'Mensaje final para tickets';
ALTER TABLE empresas ADD COLUMN url_verificacion VARCHAR(512) DEFAULT 'https://srienlinea.sri.gob.ec/sri-en-linea/consulta/55' COMMENT 'URL de verificación SRI';

# Campos para secuenciales de facturación
ALTER TABLE empresas ADD COLUMN secuencial_actual_factura INT DEFAULT 1 COMMENT 'Secuencial actual para facturas';
ALTER TABLE empresas ADD COLUMN secuencial_actual_nota_credito INT DEFAULT 1 COMMENT 'Secuencial actual para notas de crédito';
ALTER TABLE empresas ADD COLUMN secuencial_actual_nota_debito INT DEFAULT 1 COMMENT 'Secuencial actual para notas de débito';

# Configuración de impuestos
ALTER TABLE empresas ADD COLUMN porcentaje_iva DECIMAL(5,2) DEFAULT 15.00 COMMENT 'Porcentaje de IVA';
ALTER TABLE empresas ADD COLUMN aplica_retencion TINYINT(1) DEFAULT 0 COMMENT 'Si aplica retención en la fuente';
ALTER TABLE empresas ADD COLUMN porcentaje_retencion DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Porcentaje de retención';

# Campos para personalización de tickets
ALTER TABLE empresas ADD COLUMN mostrar_eslogan_ticket TINYINT(1) DEFAULT 1 COMMENT 'Mostrar eslogan en tickets';
ALTER TABLE empresas ADD COLUMN mostrar_mensaje_final_ticket TINYINT(1) DEFAULT 1 COMMENT 'Mostrar mensaje final en tickets';
ALTER TABLE empresas ADD COLUMN formato_fecha_ticket ENUM('DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD') DEFAULT 'DD/MM/YYYY' COMMENT 'Formato de fecha para tickets';