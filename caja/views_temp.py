from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db import connection
from django.utils import timezone
from .models import Caja, CierreCaja, MovimientoCaja


@login_required
def lista_cajas(request):
    """Lista todas las cajas"""
    cajas = Caja.objects.all().order_by('codigo')
    cajas_activas = cajas.filter(activa=True)
    
    context = {
        'cajas': cajas,
        'cajas_activas': cajas_activas,
        'total_cajas': cajas.count(),
        'total_activas': cajas_activas.count(),
        'titulo': 'Gestión de Cajas'
    }
    return render(request, 'caja/lista.html', context)


@login_required 
def activar_caja(request, caja_id):
    """Activar/Desactivar una caja"""
    if request.method == 'POST':
        try:
            caja = Caja.objects.get(id=caja_id)
            # Toggle del estado activo
            caja.activa = not caja.activa
            caja.save()
            
            estado = "activada" if caja.activa else "desactivada"
            messages.success(request, f'Caja {caja.codigo} - {caja.nombre} {estado} exitosamente')
            
        except Caja.DoesNotExist:
            messages.error(request, 'Caja no encontrada')
        except Exception as e:
            messages.error(request, f'Error al cambiar estado de la caja: {str(e)}')
    
    return redirect('caja:lista')


@login_required
def crear_caja(request):
    """Crear nueva caja"""
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        
        if not codigo or not nombre:
            messages.error(request, 'Código y nombre son requeridos')
        elif Caja.objects.filter(codigo=codigo).exists():
            messages.error(request, f'Ya existe una caja con el código {codigo}')
        else:
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("INSERT INTO cajas (codigo, nombre, activa) VALUES (%s, %s, %s)", 
                                 [codigo, nombre, True])
                
                messages.success(request, f'Caja {codigo} - {nombre} creada exitosamente')
                return redirect('caja:lista')
                
            except Exception as e:
                messages.error(request, f'Error al crear la caja: {str(e)}')
    
    context = {
        'titulo': 'Crear Nueva Caja'
    }
    return render(request, 'caja/crear.html', context)


@login_required
def editar_caja(request, pk):
    """Editar caja existente"""
    try:
        caja = Caja.objects.get(id=pk)
    except Caja.DoesNotExist:
        messages.error(request, 'Caja no encontrada')
        return redirect('caja:lista')
    
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        
        if not codigo or not nombre:
            messages.error(request, 'Código y nombre son requeridos')
        elif Caja.objects.filter(codigo=codigo).exclude(id=pk).exists():
            messages.error(request, f'Ya existe otra caja con el código {codigo}')
        else:
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE cajas SET codigo = %s, nombre = %s WHERE id = %s", 
                                 [codigo, nombre, pk])
                
                messages.success(request, f'Caja actualizada exitosamente')
                return redirect('caja:lista')
                
            except Exception as e:
                messages.error(request, f'Error al actualizar la caja: {str(e)}')
    
    context = {
        'caja': caja,
        'titulo': f'Editar Caja: {caja.nombre}'
    }
    return render(request, 'caja/editar.html', context)


@login_required
def abrir_caja(request):
    """Abrir caja para el usuario actual"""
    from django.db import connection
    
    # Verificar si ya tiene una caja abierta
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, id_caja FROM cierres_caja 
            WHERE id_usuario_apertura = %s AND estado = 'ABIERTA'
        """, [request.user.id])
        caja_abierta = cursor.fetchone()
    
    if caja_abierta:
        messages.warning(request, 'Ya tiene una caja abierta')
        return redirect('caja:estado')
    
    if request.method == 'POST':
        # Obtener datos del formulario
        caja_id = request.POST.get('caja')
        monto_inicial = request.POST.get('monto_inicial', 0)
        
        try:
            # Obtener la caja seleccionada
            caja = Caja.objects.get(id=caja_id, activa=True)
            
            # Registrar apertura usando SQL directo como en tu código C#
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO cierres_caja 
                    (id_caja, id_usuario_apertura, fecha_apertura, saldo_inicial, estado, creado_por, creado_date) 
                    VALUES 
                    (%s, %s, NOW(), %s, 'ABIERTA', %s, NOW())
                """, [caja_id, request.user.id, monto_inicial, request.user.id])
            
            messages.success(request, f'Caja {caja.nombre} abierta exitosamente')
            return redirect('dashboard')
            
        except Caja.DoesNotExist:
            messages.error(request, 'La caja seleccionada no es válida')
        except Exception as e:
            messages.error(request, f'Error al abrir la caja: {str(e)}')
    
    context = {
        'cajas_disponibles': Caja.objects.filter(activa=True),
        'titulo': 'Abrir Caja'
    }
    return render(request, 'caja/abrir.html', context)


@login_required
def cerrar_caja(request):
    """Cerrar caja del usuario actual"""
    from django.db import connection
    
    # Verificar si tiene una caja abierta
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT cc.id, cc.id_caja, cc.saldo_inicial, c.nombre as caja_nombre
            FROM cierres_caja cc
            INNER JOIN cajas c ON cc.id_caja = c.id
            WHERE cc.id_usuario_apertura = %s AND cc.estado = 'ABIERTA'
        """, [request.user.id])
        apertura = cursor.fetchone()
    
    if not apertura:
        messages.warning(request, 'No tiene ninguna caja abierta')
        return redirect('caja:estado')
    
    if request.method == 'POST':
        try:
            total_contado = float(request.POST.get('total_contado', 0))
            saldo_teorico = float(request.POST.get('saldo_teorico', 0))
            diferencia = total_contado - saldo_teorico
            
            # Cerrar caja usando SQL directo como en tu código C#
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE cierres_caja SET
                        fecha_cierre = NOW(),
                        total_contado_fisico = %s,
                        saldo_teorico_sistema = %s,
                        diferencia = %s,
                        id_usuario_cierre = %s,
                        estado = 'CERRADA',
                        editado_por = %s,
                        editado_date = NOW()
                    WHERE id = %s
                """, [total_contado, saldo_teorico, diferencia, request.user.id, request.user.id, apertura[0]])
            
            messages.success(request, f'Caja {apertura[3]} cerrada exitosamente')
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(request, f'Error al cerrar la caja: {str(e)}')
    
    context = {
        'apertura': {
            'id': apertura[0],
            'id_caja': apertura[1],
            'saldo_inicial': apertura[2],
            'caja_nombre': apertura[3]
        },
        'titulo': 'Cerrar Caja'
    }
    return render(request, 'caja/cerrar.html', context)


@login_required
def estado_caja(request):
    """Estado actual de la caja del usuario"""
    from django.db import connection
    
    # Obtener caja abierta del usuario
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT cc.id, cc.id_caja, cc.saldo_inicial, cc.fecha_apertura, c.nombre as caja_nombre
            FROM cierres_caja cc
            INNER JOIN cajas c ON cc.id_caja = c.id
            WHERE cc.id_usuario_apertura = %s AND cc.estado = 'ABIERTA'
        """, [request.user.id])
        apertura = cursor.fetchone()
    
    if not apertura:
        messages.warning(request, 'No tiene ninguna caja abierta')
        return redirect('caja:abrir')
    
    # Aquí puedes agregar lógica para calcular ventas, movimientos, etc.
    context = {
        'apertura': {
            'id': apertura[0],
            'id_caja': apertura[1],
            'saldo_inicial': apertura[2],
            'fecha_apertura': apertura[3],
            'caja_nombre': apertura[4]
        },
        'titulo': 'Estado de Caja'
    }
    return render(request, 'caja/estado.html', context)


@login_required
def eliminar_caja(request, caja_id):
    """Eliminar una caja"""
    if request.method == 'POST':
        try:
            caja = Caja.objects.get(id=caja_id)
            nombre_caja = f"{caja.codigo} - {caja.nombre}"
            
            # Verificar si la caja tiene registros relacionados
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM cierres_caja WHERE id_caja = %s", [caja_id])
                tiene_movimientos = cursor.fetchone()[0] > 0
            
            if tiene_movimientos:
                messages.error(request, 'No se puede eliminar la caja porque tiene movimientos registrados')
            else:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM cajas WHERE id = %s", [caja_id])
                messages.success(request, f'Caja {nombre_caja} eliminada exitosamente')
                
        except Caja.DoesNotExist:
            messages.error(request, 'Caja no encontrada')
        except Exception as e:
            messages.error(request, f'Error al eliminar la caja: {str(e)}')
    
    return redirect('caja:lista')


@login_required
def estado_cajas(request):
    """Estado general de todas las cajas"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.id, c.codigo, c.nombre, c.activa,
                   COUNT(cc.id) as total_aperturas,
                   SUM(CASE WHEN cc.estado = 'ABIERTA' THEN 1 ELSE 0 END) as cajas_abiertas
            FROM cajas c
            LEFT JOIN cierres_caja cc ON c.id = cc.id_caja
            GROUP BY c.id, c.codigo, c.nombre, c.activa
            ORDER BY c.codigo
        """)
        cajas_estado = cursor.fetchall()
    
    context = {
        'cajas_estado': cajas_estado,
        'titulo': 'Estado General de Cajas'
    }
    return render(request, 'caja/estado_general.html', context)


# Funciones simplificadas para evitar errores
@login_required
def lista_movimientos(request):
    """Lista movimientos de caja"""
    movimientos = MovimientoCaja.objects.all().order_by('-fecha')[:50]
    
    context = {
        'movimientos': movimientos,
        'titulo': 'Movimientos de Caja'
    }
    return render(request, 'caja/movimientos.html', context)


@login_required
def nuevo_movimiento(request):
    """Crear nuevo movimiento de caja"""
    context = {
        'titulo': 'Nuevo Movimiento'
    }
    return render(request, 'caja/nuevo_movimiento.html', context)


@login_required 
def lista_aperturas(request):
    """Lista de aperturas de caja"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT cc.id, cc.id_caja, c.nombre, cc.fecha_apertura, cc.saldo_inicial, cc.estado
            FROM cierres_caja cc
            INNER JOIN cajas c ON cc.id_caja = c.id
            ORDER BY cc.fecha_apertura DESC
            LIMIT 50
        """)
        aperturas = cursor.fetchall()
    
    context = {
        'aperturas': aperturas,
        'titulo': 'Historial de Aperturas'
    }
    return render(request, 'caja/aperturas.html', context)


@login_required
def lista_cierres(request):
    """Lista de cierres de caja"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT cc.id, cc.id_caja, c.nombre, cc.fecha_cierre, cc.diferencia, cc.estado
            FROM cierres_caja cc
            INNER JOIN cajas c ON cc.id_caja = c.id
            WHERE cc.estado = 'CERRADA'
            ORDER BY cc.fecha_cierre DESC
            LIMIT 50
        """)
        cierres = cursor.fetchall()
    
    context = {
        'cierres': cierres,
        'titulo': 'Historial de Cierres'
    }
    return render(request, 'caja/cierres.html', context)


@login_required
def detalle_apertura(request, pk):
    """Detalle de una apertura específica"""
    context = {
        'titulo': 'Detalle de Apertura'
    }
    return render(request, 'caja/detalle_apertura.html', context)


@login_required
def detalle_cierre(request, pk):
    """Detalle de un cierre específico"""
    context = {
        'titulo': 'Detalle de Cierre'
    }
    return render(request, 'caja/detalle_cierre.html', context)