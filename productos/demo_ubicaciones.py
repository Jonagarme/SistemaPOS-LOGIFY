#!/usr/bin/env python
"""
Demostración del Sistema de Ubicación de Productos en Perchas
Sistema POS Comercial
"""
import os
import sys
import django
from django.db import connection

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_pos.settings')
django.setup()

def mostrar_estadisticas():
    """Mostrar estadísticas del sistema de ubicaciones"""
    print("=" * 60)
    print("    SISTEMA DE UBICACIÓN DE PRODUCTOS EN PERCHAS")
    print("    📋 Sistema POS Comercial - LogiCommerce")
    print("=" * 60)
    
    try:
        with connection.cursor() as cursor:
            # Estadísticas generales
            cursor.execute("SELECT COUNT(*) FROM productos_seccion WHERE activo = 1")
            secciones = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM productos_percha WHERE activo = 1")
            perchas = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM productos_ubicacionproducto WHERE activo = 1")
            ubicaciones = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM productos WHERE activo = 1 AND anulado = 0")
            total_productos = cursor.fetchone()[0]
            
            porcentaje_ubicado = (ubicaciones / total_productos * 100) if total_productos > 0 else 0
            
            print(f"\n📊 ESTADÍSTICAS GENERALES:")
            print(f"   • Secciones creadas: {secciones}")
            print(f"   • Perchas disponibles: {perchas}")
            print(f"   • Productos ubicados: {ubicaciones}")
            print(f"   • Total de productos: {total_productos}")
            print(f"   • Porcentaje ubicado: {porcentaje_ubicado:.1f}%")
            
            # Mostrar secciones
            print(f"\n🗂️  SECCIONES DISPONIBLES:")
            cursor.execute("""
                SELECT s.nombre, s.descripcion, s.color, COUNT(p.id) as perchas
                FROM productos_seccion s
                LEFT JOIN productos_percha p ON s.id = p.seccion_id AND p.activo = 1
                WHERE s.activo = 1
                GROUP BY s.id, s.nombre, s.descripcion, s.color
                ORDER BY s.orden
            """)
            
            for seccion in cursor.fetchall():
                nombre, desc, color, perchas_count = seccion
                print(f"   • {nombre} ({color}) - {perchas_count} perchas")
                print(f"     └─ {desc}")
            
            # Mostrar algunas ubicaciones ejemplo
            print(f"\n📍 UBICACIONES DE EJEMPLO:")
            cursor.execute("""
                SELECT 
                    p.codigoPrincipal,
                    p.nombre,
                    s.nombre as seccion,
                    pr.nombre as percha,
                    u.fila,
                    u.columna,
                    CONCAT(s.nombre, ' > ', pr.nombre, ' > F', u.fila, 'C', u.columna) as ubicacion_completa
                FROM productos_ubicacionproducto u
                JOIN productos p ON u.producto_id = p.id
                JOIN productos_percha pr ON u.percha_id = pr.id
                JOIN productos_seccion s ON pr.seccion_id = s.id
                WHERE u.activo = 1 AND p.activo = 1
                LIMIT 5
            """)
            
            ubicaciones_ejemplo = cursor.fetchall()
            if ubicaciones_ejemplo:
                for ub in ubicaciones_ejemplo:
                    codigo, nombre, seccion, percha, fila, columna, ubicacion = ub
                    print(f"   • {codigo}: {nombre[:30]}...")
                    print(f"     📍 {ubicacion}")
            else:
                print("   • No hay productos ubicados aún")
                print("     💡 Usa el panel web para ubicar productos")
            
            # Mostrar capacidad de perchas
            print(f"\n📦 CAPACIDAD DE PERCHAS:")
            cursor.execute("""
                SELECT 
                    s.nombre as seccion,
                    pr.nombre as percha,
                    pr.filas * pr.columnas as capacidad_total,
                    COUNT(u.id) as ocupadas,
                    (pr.filas * pr.columnas - COUNT(u.id)) as disponibles
                FROM productos_percha pr
                JOIN productos_seccion s ON pr.seccion_id = s.id
                LEFT JOIN productos_ubicacionproducto u ON pr.id = u.percha_id AND u.activo = 1
                WHERE pr.activo = 1 AND s.activo = 1
                GROUP BY pr.id, s.nombre, pr.nombre, pr.filas, pr.columnas
                ORDER BY s.orden, pr.nombre
                LIMIT 8
            """)
            
            for percha_info in cursor.fetchall():
                seccion, percha, total, ocupadas, disponibles = percha_info
                uso_pct = (ocupadas / total * 100) if total > 0 else 0
                print(f"   • {seccion} - {percha}")
                print(f"     └─ {ocupadas}/{total} posiciones ({uso_pct:.1f}% ocupado)")
            
            print(f"\n🌐 ACCESO AL SISTEMA:")
            print(f"   • URL: http://127.0.0.1:8000/productos/ubicaciones/")
            print(f"   • Menú: Productos > Ubicaciones en Perchas")
            print(f"   • Funciones disponibles:")
            print(f"     - ✅ Gestión de secciones y perchas")
            print(f"     - ✅ Mapa visual de perchas")
            print(f"     - ✅ Ubicación de productos")
            print(f"     - ✅ Búsqueda por ubicación")
            print(f"     - ✅ Integración con POS (búsqueda con ubicación)")
            
            print(f"\n💡 CARACTERÍSTICAS:")
            print(f"   • 🎯 Búsqueda de productos incluye ubicación")
            print(f"   • 🗺️  Mapas visuales de perchas con colores")
            print(f"   • 📱 Interfaz responsive (móvil/tablet)")
            print(f"   • ⚡ Consultas SQL optimizadas")
            print(f"   • 🔄 AJAX para actualizaciones en tiempo real")
            
            print("\n" + "=" * 60)
            print("✅ SISTEMA DE UBICACIONES IMPLEMENTADO EXITOSAMENTE")
            print("🚀 ¡Listo para usar en producción!")
            print("=" * 60)
            
    except Exception as e:
        print(f"❌ Error al obtener estadísticas: {e}")

def mostrar_ejemplo_busqueda():
    """Mostrar ejemplo de búsqueda con ubicación"""
    print(f"\n🔍 EJEMPLO DE BÚSQUEDA CON UBICACIÓN:")
    print("   (Simulando búsqueda en POS)")
    
    try:
        with connection.cursor() as cursor:
            # Buscar productos con ubicación
            cursor.execute("""
                SELECT 
                    p.codigoPrincipal,
                    p.nombre,
                    p.precioVenta,
                    p.stock,
                    CASE WHEN u.id IS NOT NULL 
                         THEN CONCAT(s.nombre, ' > ', pr.nombre, ' > F', u.fila, 'C', u.columna)
                         ELSE 'Sin ubicar' 
                    END as ubicacion_completa,
                    s.color as color_seccion
                FROM productos p
                LEFT JOIN productos_ubicacionproducto u ON p.id = u.producto_id AND u.activo = 1
                LEFT JOIN productos_percha pr ON u.percha_id = pr.id AND pr.activo = 1
                LEFT JOIN productos_seccion s ON pr.seccion_id = s.id AND s.activo = 1
                WHERE p.activo = 1 AND p.anulado = 0
                ORDER BY u.id IS NOT NULL DESC, p.nombre
                LIMIT 3
            """)
            
            productos = cursor.fetchall()
            for producto in productos:
                codigo, nombre, precio, stock, ubicacion, color = producto
                estado = "📍 UBICADO" if ubicacion != "Sin ubicar" else "❓ SIN UBICAR"
                
                print(f"\n   {estado}")
                print(f"   • Código: {codigo}")
                print(f"   • Producto: {nombre}")
                print(f"   • Precio: ${precio}")
                print(f"   • Stock: {stock}")
                print(f"   • Ubicación: {ubicacion}")
                if color:
                    print(f"   • Color sección: {color}")
                
    except Exception as e:
        print(f"❌ Error en ejemplo de búsqueda: {e}")

if __name__ == "__main__":
    mostrar_estadisticas()
    mostrar_ejemplo_busqueda()