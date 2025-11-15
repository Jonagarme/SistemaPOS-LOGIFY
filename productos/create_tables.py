#!/usr/bin/env python
"""
Script para crear las tablas de ubicación de productos
"""
import os
import sys
import django
from django.db import connection

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_pos.settings')
django.setup()

def create_ubicacion_tables():
    """Crear tablas de ubicación de productos"""
    print("=== CREANDO TABLAS DE UBICACIÓN ===")
    
    sql_statements = [
        # Tabla de secciones
        """
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
        )
        """,
        
        # Tabla de perchas
        """
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
        )
        """,
        
        # Tabla de ubicación de productos
        """
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
        )
        """
    ]
    
    # Datos de ejemplo
    insert_statements = [
        """
        INSERT IGNORE INTO productos_seccion (nombre, descripcion, color, orden) VALUES
        ('Medicamentos', 'Medicamentos recetados y de venta libre', '#dc3545', 1),
        ('Cosméticos', 'Productos de belleza y cuidado personal', '#28a745', 2),
        ('Higiene', 'Productos de higiene personal', '#007bff', 3),
        ('Vitaminas', 'Suplementos vitamínicos y nutricionales', '#ffc107', 4)
        """,
        
        """
        INSERT IGNORE INTO productos_percha (seccion_id, nombre, descripcion, filas, columnas) 
        SELECT s.id, percha_data.nombre, percha_data.descripcion, percha_data.filas, percha_data.columnas
        FROM productos_seccion s
        CROSS JOIN (
            SELECT 'Percha A1' as nombre, 'Analgésicos y antiinflamatorios' as descripcion, 5 as filas, 8 as columnas, 'Medicamentos' as seccion
            UNION ALL SELECT 'Percha A2', 'Antibióticos y antivirales', 5, 8, 'Medicamentos'
            UNION ALL SELECT 'Percha B1', 'Maquillaje y fragancias', 4, 10, 'Cosméticos'
            UNION ALL SELECT 'Percha B2', 'Cremas y lociones', 4, 10, 'Cosméticos'
            UNION ALL SELECT 'Percha C1', 'Champús y acondicionadores', 6, 6, 'Higiene'
            UNION ALL SELECT 'Percha C2', 'Jabones y desodorantes', 6, 6, 'Higiene'
            UNION ALL SELECT 'Percha D1', 'Vitaminas A-M', 5, 8, 'Vitaminas'
            UNION ALL SELECT 'Percha D2', 'Vitaminas N-Z', 5, 8, 'Vitaminas'
        ) percha_data
        WHERE s.nombre = percha_data.seccion
        """
    ]
    
    # Índices
    index_statements = [
        "CREATE INDEX idx_ubicacion_producto ON productos_ubicacionproducto(producto_id)",
        "CREATE INDEX idx_ubicacion_percha ON productos_ubicacionproducto(percha_id)",
        "CREATE INDEX idx_percha_seccion ON productos_percha(seccion_id)",
        "CREATE INDEX idx_seccion_activo ON productos_seccion(activo)",
        "CREATE INDEX idx_percha_activo ON productos_percha(activo)",
        "CREATE INDEX idx_ubicacion_activo ON productos_ubicacionproducto(activo)"
    ]
    
    try:
        with connection.cursor() as cursor:
            # Crear tablas
            for i, sql in enumerate(sql_statements, 1):
                print(f"Ejecutando statement {i}/3...")
                cursor.execute(sql)
                print("✓ Completado")
            
            # Insertar datos de ejemplo
            for i, sql in enumerate(insert_statements, 1):
                print(f"Insertando datos {i}/2...")
                cursor.execute(sql)
                print("✓ Completado")
            
            # Crear índices
            for i, sql in enumerate(index_statements, 1):
                try:
                    print(f"Creando índice {i}/6...")
                    cursor.execute(sql)
                    print("✓ Completado")
                except Exception as e:
                    if "Duplicate key name" in str(e):
                        print("✓ Índice ya existe")
                    else:
                        print(f"⚠ Error en índice: {e}")
                        continue
            
            print("\n=== VERIFICANDO TABLAS CREADAS ===")
            cursor.execute("SHOW TABLES LIKE 'productos_%'")
            tables = cursor.fetchall()
            for table in tables:
                print(f"✓ Tabla: {table[0]}")
            
            # Verificar datos insertados
            print("\n=== DATOS INSERTADOS ===")
            cursor.execute("SELECT COUNT(*) FROM productos_seccion")
            secciones = cursor.fetchone()[0]
            print(f"✓ Secciones: {secciones}")
            
            cursor.execute("SELECT COUNT(*) FROM productos_percha")
            perchas = cursor.fetchone()[0]
            print(f"✓ Perchas: {perchas}")
            
            print("\n¡Tablas de ubicación creadas exitosamente!")
            
    except Exception as e:
        print(f"Error al crear tablas: {e}")
        return False
    
    return True

if __name__ == "__main__":
    create_ubicacion_tables()