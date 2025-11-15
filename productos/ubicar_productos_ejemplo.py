#!/usr/bin/env python
"""
Script para ubicar algunos productos de ejemplo en las perchas
"""
import os
import sys
import django
from django.db import connection

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_pos.settings')
django.setup()

def ubicar_productos_ejemplo():
    """Ubicar algunos productos de ejemplo en las perchas"""
    print("=== UBICANDO PRODUCTOS DE EJEMPLO ===")
    
    try:
        with connection.cursor() as cursor:
            # Obtener algunos productos de ejemplo
            cursor.execute("""
                SELECT id, codigoPrincipal, nombre 
                FROM productos 
                WHERE activo = 1 AND anulado = 0 
                LIMIT 10
            """)
            productos = cursor.fetchall()
            
            if not productos:
                print("No se encontraron productos para ubicar")
                return
            
            print(f"Productos disponibles: {len(productos)}")
            
            # Obtener perchas disponibles
            cursor.execute("""
                SELECT p.id, p.nombre, s.nombre as seccion
                FROM productos_percha p
                JOIN productos_seccion s ON p.seccion_id = s.id
                WHERE p.activo = 1 AND s.activo = 1
                ORDER BY s.orden, p.nombre
            """)
            perchas = cursor.fetchall()
            
            print(f"Perchas disponibles: {len(perchas)}")
            
            # Ubicar productos de forma aleatoria
            ubicaciones_creadas = 0
            for i, producto in enumerate(productos[:8]):  # Solo 8 productos
                producto_id = producto[0]
                codigo = producto[1]
                nombre = producto[2]
                
                # Seleccionar percha (rotar entre las disponibles)
                percha = perchas[i % len(perchas)]
                percha_id = percha[0]
                percha_nombre = percha[1]
                seccion_nombre = percha[2]
                
                # Calcular posición (fila y columna)
                fila = (i % 5) + 1  # Filas 1-5
                columna = (i % 8) + 1  # Columnas 1-8
                
                # Verificar si ya existe ubicación para este producto
                cursor.execute("""
                    SELECT id FROM productos_ubicacionproducto 
                    WHERE producto_id = %s AND activo = 1
                """, [producto_id])
                
                if cursor.fetchone():
                    print(f"⚠ Producto {codigo} ya tiene ubicación")
                    continue
                
                # Verificar si la posición está ocupada
                cursor.execute("""
                    SELECT id FROM productos_ubicacionproducto 
                    WHERE percha_id = %s AND fila = %s AND columna = %s AND activo = 1
                """, [percha_id, fila, columna])
                
                if cursor.fetchone():
                    # Buscar siguiente posición disponible
                    fila = ((i + 3) % 5) + 1
                    columna = ((i + 2) % 8) + 1
                
                # Crear ubicación
                cursor.execute("""
                    INSERT INTO productos_ubicacionproducto 
                    (producto_id, percha_id, fila, columna, cantidad_maxima, cantidad_actual, activo)
                    VALUES (%s, %s, %s, %s, %s, %s, 1)
                """, [producto_id, percha_id, fila, columna, 50, 25])
                
                print(f"✓ {codigo} ({nombre[:30]}...) -> {seccion_nombre} > {percha_nombre} > F{fila}C{columna}")
                ubicaciones_creadas += 1
            
            print(f"\n¡Se crearon {ubicaciones_creadas} ubicaciones de ejemplo!")
            
            # Mostrar estadísticas
            cursor.execute("SELECT COUNT(*) FROM productos_ubicacionproducto WHERE activo = 1")
            total_ubicaciones = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM productos WHERE activo = 1 AND anulado = 0")
            total_productos = cursor.fetchone()[0]
            
            productos_ubicados = (total_ubicaciones / total_productos) * 100 if total_productos > 0 else 0
            
            print(f"\n=== ESTADÍSTICAS ===")
            print(f"Total productos: {total_productos}")
            print(f"Productos ubicados: {total_ubicaciones}")
            print(f"Porcentaje ubicado: {productos_ubicados:.1f}%")
            
    except Exception as e:
        print(f"Error al ubicar productos: {e}")
        return False
    
    return True

if __name__ == "__main__":
    ubicar_productos_ejemplo()