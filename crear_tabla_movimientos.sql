-- Script para crear la tabla movimientos_caja
-- Ejecutar este script en tu base de datos MySQL si quieres habilitar los movimientos de caja

CREATE TABLE IF NOT EXISTS `movimientos_caja` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `idCaja` int unsigned NOT NULL,
  `tipo` varchar(20) NOT NULL,
  `concepto` varchar(200) NOT NULL,
  `monto` decimal(10,2) NOT NULL,
  `fecha` datetime NOT NULL,
  `idUsuario` int unsigned NOT NULL,
  `observaciones` text,
  PRIMARY KEY (`id`),
  KEY `idx_movimientos_caja` (`idCaja`),
  KEY `idx_movimientos_fecha` (`fecha`),
  KEY `idx_movimientos_tipo` (`tipo`),
  KEY `fk_movimientos_usuario` (`idUsuario`),
  CONSTRAINT `fk_movimientos_caja` FOREIGN KEY (`idCaja`) REFERENCES `cajas` (`id`),
  CONSTRAINT `fk_movimientos_usuario` FOREIGN KEY (`idUsuario`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Los tipos de movimiento válidos son: 'ingreso', 'egreso', 'venta', 'devolucion'