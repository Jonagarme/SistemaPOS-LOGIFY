#!/usr/bin/env python
"""
Script para verificar el estado de las tablas de ubicación
"""
import os
import sys
import django
from django.db import connection

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_pos.settings')
django.setup()

def verificar_tablas():
    """Verificar estado de las tablas de ubicación"""
    print("=== VERIFICACIÓN DE TABLAS ===")
    
    try:
        with connection.cursor() as cursor:
            # Verificar que las tablas existen
            tablas = ['productos_seccion', 'productos_percha', 'productos_ubicacionproducto']
            
            for tabla in tablas:
                try:
                    cursor.execute(f"SHOW TABLES LIKE '{tabla}'")
                    existe = cursor.fetchone()
                    if existe:
                        print(f"✅ Tabla {tabla} existe")
                        
                        # Contar registros
                        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                        total = cursor.fetchone()[0]
                        print(f"   📊 Total registros: {total}")
                        
                        # Mostrar algunos datos
                        if tabla == 'productos_seccion':
                            cursor.execute("SELECT id, nombre, activo FROM productos_seccion LIMIT 5")
                            for row in cursor.fetchall():
                                print(f"      ID: {row[0]}, Nombre: {row[1]}, Activo: {row[2]}")
                        
                        elif tabla == 'productos_percha':
                            cursor.execute("SELECT id, nombre, seccion_id, activo FROM productos_percha LIMIT 5")
                            for row in cursor.fetchall():
                                print(f"      ID: {row[0]}, Nombre: {row[1]}, Sección: {row[2]}, Activo: {row[3]}")
                        
                        elif tabla == 'productos_ubicacionproducto':
                            cursor.execute("SELECT id, producto_id, percha_id, fila, columna, activo FROM productos_ubicacionproducto LIMIT 5")
                            for row in cursor.fetchall():
                                print(f"      ID: {row[0]}, Producto: {row[1]}, Percha: {row[2]}, F{row[3]}C{row[4]}, Activo: {row[5]}")
                        
                        print()
                    else:
                        print(f"❌ Tabla {tabla} NO existe")
                except Exception as e:
                    print(f"❌ Error verificando tabla {tabla}: {e}")
            
            # Verificar tabla productos
            print("=== VERIFICACIÓN TABLA PRODUCTOS ===")
            try:
                cursor.execute("SELECT COUNT(*) FROM productos WHERE activo = 1 AND anulado = 0")
                total_productos = cursor.fetchone()[0]
                print(f"✅ Total productos activos: {total_productos}")
                
                cursor.execute("SELECT id, codigoPrincipal, nombre FROM productos WHERE activo = 1 AND anulado = 0 LIMIT 3")
                for row in cursor.fetchall():
                    print(f"   Producto: {row[0]} - {row[1]} - {row[2]}")
                    
            except Exception as e:
                print(f"❌ Error verificando productos: {e}")
                
            # Probar las consultas de las vistas
            print("\n=== PROBANDO CONSULTAS DE VISTAS ===")
            try:
                cursor.execute("SELECT COUNT(*) FROM productos_seccion WHERE activo = 1")
                secciones = cursor.fetchone()[0]
                print(f"Secciones activas: {secciones}")
                
                cursor.execute("SELECT COUNT(*) FROM productos_percha WHERE activo = 1")
                perchas = cursor.fetchone()[0]
                print(f"Perchas activas: {perchas}")
                
                cursor.execute("SELECT COUNT(*) FROM productos_ubicacionproducto WHERE activo = 1")
                ubicaciones = cursor.fetchone()[0]
                print(f"Ubicaciones activas: {ubicaciones}")
                
            except Exception as e:
                print(f"❌ Error en consultas: {e}")
            
    except Exception as e:
        print(f"❌ Error general: {e}")

if __name__ == "__main__":
    verificar_tablas()