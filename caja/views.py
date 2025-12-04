from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db import connection, OperationalError
from django.utils import timezone
from django.http import JsonResponse
from datetime import date
from .models import Caja, CierreCaja, AperturaCaja, ArqueoCaja
from decimal import Decimal
import json
from functools import wraps


def login_required_offline_safe(view_func):
    """
    Decorador personalizado que permite acceso sin autenticación en modo offline
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Si el middleware ya detectó modo offline, continuar directamente
        if getattr(request, 'modo_offline', False):
            # Verificar si hay usuario en sesión
            usuario_offline = request.session.get('usuario_offline')
            if not usuario_offline:
                # No hay sesión offline, redirigir a login
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            # Hay sesión offline, continuar
            return view_func(request, *args, **kwargs)
        
        # Modo online - verificar autenticación normal
        try:
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
        except (OperationalError, Exception) as e:
            # Error inesperado - permitir acceso en modo offline
            print(f"Error de autenticación en caja: {e}")
            pass
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


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
            messages.error(request, 'Código y nombre son obligatorios')
            return render(request, 'caja/crear.html', {'titulo': 'Crear Caja'})
            
        try:
            # Verificar que el código no exista
            if Caja.objects.filter(codigo=codigo).exists():
                messages.error(request, f'Ya existe una caja con el código {codigo}')
                return render(request, 'caja/crear.html', {
                    'titulo': 'Crear Caja',
                    'codigo': codigo,
                    'nombre': nombre
                })
            
            # Crear la caja directamente en la base de datos
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO cajas (codigo, nombre, activa) VALUES (%s, %s, %s)",
                    [codigo, nombre, True]
                )
            
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
        caja = Caja.objects.get(pk=pk)
    except Caja.DoesNotExist:
        messages.error(request, 'Caja no encontrada')
        return redirect('caja:lista')
    
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        activa = 'activa' in request.POST
        
        if not codigo or not nombre:
            messages.error(request, 'Código y nombre son obligatorios')
            return render(request, 'caja/editar.html', {
                'titulo': 'Editar Caja',
                'caja': caja,
                'codigo': codigo,
                'nombre': nombre,
                'activa': activa
            })
            
        try:
            # Verificar que el código no exista en otra caja
            if Caja.objects.filter(codigo=codigo).exclude(pk=pk).exists():
                messages.error(request, f'Ya existe otra caja con el código {codigo}')
                return render(request, 'caja/editar.html', {
                    'titulo': 'Editar Caja',
                    'caja': caja,
                    'codigo': codigo,
                    'nombre': nombre,
                    'activa': activa
                })
            
            # Actualizar directamente en la base de datos
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE cajas SET codigo = %s, nombre = %s, activa = %s WHERE id = %s",
                    [codigo, nombre, activa, pk]
                )
            
            messages.success(request, f'Caja {codigo} - {nombre} actualizada exitosamente')
            return redirect('caja:lista')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar la caja: {str(e)}')
    
    context = {
        'caja': caja,
        'titulo': f'Editar Caja: {caja.nombre}'
    }
    return render(request, 'caja/editar.html', context)


@login_required
def eliminar_caja(request, caja_id):
    """Eliminar caja existente"""
    if request.method == 'POST':
        try:
            # Verificar si la caja existe
            caja = Caja.objects.get(id=caja_id)
            
            # Verificar si hay aperturas/cierres relacionados
            tiene_movimientos = CierreCaja.objects.filter(idCaja=caja_id).exists()
            
            if tiene_movimientos:
                messages.error(request, f'No se puede eliminar la caja {caja.codigo} porque tiene aperturas/cierres registrados.')
                return redirect('caja:lista')
            
            # Eliminar la caja usando SQL directo
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM cajas WHERE id = %s", [caja_id])
            
            messages.success(request, f'Caja {caja.codigo} - {caja.nombre} eliminada exitosamente')
            
        except Caja.DoesNotExist:
            messages.error(request, 'Caja no encontrada')
        except Exception as e:
            messages.error(request, f'Error al eliminar la caja: {str(e)}')
    
    return redirect('caja:lista')


@login_required_offline_safe
def abrir_caja(request):
    """Abrir caja para el usuario actual - Con soporte offline"""
    
    modo_offline = False
    caja_abierta_data = None
    caja_anterior = None
    cajas_disponibles = []
    
    try:
        # Verificar si ya hay una caja abierta del día actual usando función centralizada
        try:
            caja_abierta_data = CierreCaja.obtener_caja_abierta()
            
            if caja_abierta_data:
                messages.warning(request, 'Ya hay una caja abierta para el día de hoy')
                return redirect('caja:estado')
        except OperationalError:
            modo_offline = True
        
        # Verificar si hay cajas abiertas de días anteriores (solo si no estamos offline)
        if not modo_offline:
            try:
                hoy = date.today()
                caja_anterior = CierreCaja.objects.filter(
                    estado='ABIERTA',
                    anulado=False,
                    fechaApertura__date__lt=hoy
                ).first()
                
                # Si hay cajas anteriores abiertas, NO permitir abrir una nueva
                if caja_anterior:
                    fecha_apertura = caja_anterior.fechaApertura.strftime("%d/%m/%Y")
                    messages.error(
                        request, 
                        f'No puedes abrir una nueva caja. Existe una caja abierta del {fecha_apertura} que debe ser cerrada primero.'
                    )
                    messages.info(request, 'Por favor, dirígete a "Cerrar Caja" para cerrar la caja pendiente.')
                    return redirect('caja:cerrar')
            except OperationalError:
                modo_offline = True
        
    except OperationalError:
        modo_offline = True
    
    # Si estamos en modo offline, verificar si ya hay caja en sesión
    if modo_offline:
        caja_offline_existente = request.session.get('caja_offline')
        
        if caja_offline_existente:
            # Ya hay una caja offline abierta, redirigir directamente a ventas
            messages.info(request, f'MODO OFFLINE: Usando caja {caja_offline_existente.get("nombre", "Principal")} abierta previamente.')
            return redirect('ventas:crear')
        
        # No hay caja offline, crear una automáticamente y redirigir
        caja_offline = {
            'idCaja': 1,
            'nombre': 'Caja Principal (Offline)',
            'montoInicial': 0.0,
            'modo_offline': True,
            'fechaApertura': str(date.today())
        }
        request.session['caja_offline'] = caja_offline
        messages.success(request, 'MODO OFFLINE: Caja abierta automáticamente. Los datos se sincronizarán cuando vuelva la conexión.')
        return redirect('ventas:crear')
    
    if request.method == 'POST':
        if modo_offline:
            # En modo offline, guardar caja en sesión
            caja_offline = {
                'idCaja': 1,
                'nombre': 'Caja Principal (Offline)',
                'montoInicial': float(request.POST.get('monto_inicial', 0)),
                'modo_offline': True,
                'fechaApertura': str(date.today())
            }
            request.session['caja_offline'] = caja_offline
            messages.success(request, 'Caja abierta en MODO OFFLINE. Datos guardados localmente.')
            return redirect('ventas:crear')
        
        # Obtener datos del formulario
        caja_id = request.POST.get('caja')
        monto_inicial = request.POST.get('monto_inicial', 0)
        observaciones = request.POST.get('observaciones', '')
        
        try:
            # Obtener la caja seleccionada
            caja = Caja.objects.get(id=caja_id, activa=True)
            
            # Registrar apertura en tabla cierres_caja con estado ABIERTA
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO cierres_caja 
                    (idCaja, idUsuarioApertura, fechaApertura, saldoInicial, estado, creadoPor, creadoDate) 
                    VALUES 
                    (%s, %s, NOW(), %s, 'ABIERTA', %s, NOW())
                """, [caja_id, request.user.id, monto_inicial, request.user.id])
            
            messages.success(request, f'Caja {caja.nombre} abierta exitosamente')
            return redirect('caja:estado')
            
        except Caja.DoesNotExist:
            messages.error(request, 'La caja seleccionada no es válida')
        except OperationalError as e:
            messages.error(request, f'Error de conexión: Sin acceso a la base de datos. Trabaja en modo offline.')
            modo_offline = True
        except Exception as e:
            messages.error(request, f'Error al abrir la caja: {str(e)}')
    
    # Cargar cajas disponibles
    try:
        if not modo_offline:
            cajas_disponibles = Caja.objects.filter(activa=True)
    except OperationalError:
        modo_offline = True
        cajas_disponibles = []
    
    context = {
        'cajas_disponibles': cajas_disponibles,
        'modo_offline': modo_offline,
        'titulo': 'Abrir Caja' + (' - MODO OFFLINE' if modo_offline else '')
    }
    return render(request, 'caja/abrir.html', context)


@login_required
def cerrar_caja(request):
    """Cerrar caja actual"""
    # Verificar si hay una caja abierta
    caja_abierta = CierreCaja.objects.filter(
        estado='ABIERTA',
        anulado=False
    ).first()
    
    if not caja_abierta:
        messages.warning(request, 'No hay ninguna caja abierta')
        return redirect('caja:abrir')
    
    # Obtener el ID del usuario del sistema (no el de Django auth)
    usuario_sistema_id = None
    if hasattr(request.user, 'usuario_sistema_id'):
        usuario_sistema_id = request.user.usuario_sistema_id
    else:
        # Fallback: buscar por username
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM usuarios WHERE nombreUsuario = %s", 
                    [request.user.username]
                )
                row = cursor.fetchone()
                usuario_sistema_id = row[0] if row else None
        except:
            pass
    
    # Validar que el usuario que intenta cerrar sea el mismo que abrió la caja
    if usuario_sistema_id and caja_abierta.idUsuarioApertura != usuario_sistema_id:
        # Obtener el nombre del usuario que abrió la caja
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT nombreCompleto FROM usuarios WHERE id = %s", 
                    [caja_abierta.idUsuarioApertura]
                )
                row = cursor.fetchone()
                nombre_usuario_apertura = row[0] if row else f"Usuario #{caja_abierta.idUsuarioApertura}"
        except:
            nombre_usuario_apertura = f"Usuario #{caja_abierta.idUsuarioApertura}"
        
        messages.error(
            request, 
            f'⚠️ Solo el usuario que abrió la caja puede cerrarla. Esta caja fue abierta por: {nombre_usuario_apertura}'
        )
        messages.info(request, 'Por favor, solicita al usuario que abrió la caja que la cierre.')
        return redirect('caja:estado')
    
    if request.method == 'POST':
        try:
            total_contado = float(request.POST.get('total_contado', 0))
            observaciones = request.POST.get('observaciones', '')
            notas_arqueo = request.POST.get('notas_arqueo', '')
            
            # Obtener datos del arqueo
            arqueo_data = {
                'billete_100': int(request.POST.get('billete_100', 0)),
                'billete_50': int(request.POST.get('billete_50', 0)),
                'billete_20': int(request.POST.get('billete_20', 0)),
                'billete_10': int(request.POST.get('billete_10', 0)),
                'billete_5': int(request.POST.get('billete_5', 0)),
                'moneda_1': int(request.POST.get('moneda_1', 0)),
                'moneda_050': int(request.POST.get('moneda_050', 0)),
                'moneda_025': int(request.POST.get('moneda_025', 0)),
                'moneda_010': int(request.POST.get('moneda_010', 0)),
                'moneda_005': int(request.POST.get('moneda_005', 0)),
                'moneda_001': int(request.POST.get('moneda_001', 0)),
            }
            
            # Por ahora, sin cálculos de movimientos hasta que se cree la tabla
            total_ingresos = caja_abierta.totalIngresosSistema or 0
            total_egresos = caja_abierta.totalEgresosSistema or 0
            
            saldo_teorico = float(caja_abierta.saldoInicial) + float(total_ingresos) - float(total_egresos)
            diferencia = total_contado - saldo_teorico
            
            # Actualizar el registro para cerrar la caja
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE cierres_caja SET 
                        idUsuarioCierre = %s,
                        fechaCierre = NOW(),
                        totalIngresosSistema = %s,
                        totalEgresosSistema = %s,
                        saldoTeoricoSistema = %s,
                        totalContadoFisico = %s,
                        diferencia = %s,
                        estado = 'CERRADA'
                    WHERE id = %s
                """, [usuario_sistema_id, total_ingresos, total_egresos, saldo_teorico, total_contado, diferencia, caja_abierta.id])
            
            # Guardar el arqueo de caja
            try:
                # Calcular totales del arqueo
                total_billetes = (
                    arqueo_data['billete_100'] * 100 +
                    arqueo_data['billete_50'] * 50 +
                    arqueo_data['billete_20'] * 20 +
                    arqueo_data['billete_10'] * 10 +
                    arqueo_data['billete_5'] * 5
                )
                
                total_monedas = (
                    arqueo_data['moneda_1'] * 1 +
                    arqueo_data['moneda_050'] * 0.50 +
                    arqueo_data['moneda_025'] * 0.25 +
                    arqueo_data['moneda_010'] * 0.10 +
                    arqueo_data['moneda_005'] * 0.05 +
                    arqueo_data['moneda_001'] * 0.01
                )
                
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO arqueos_caja (
                            idCierreCaja, 
                            billete_100, billete_50, billete_20, billete_10, billete_5,
                            moneda_1, moneda_050, moneda_025, moneda_010, moneda_005, moneda_001,
                            total_billetes, total_monedas, total_general,
                            notas_arqueo, creadoPor, creadoDate
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                        )
                    """, [
                        caja_abierta.id,
                        arqueo_data['billete_100'], arqueo_data['billete_50'], arqueo_data['billete_20'],
                        arqueo_data['billete_10'], arqueo_data['billete_5'],
                        arqueo_data['moneda_1'], arqueo_data['moneda_050'], arqueo_data['moneda_025'],
                        arqueo_data['moneda_010'], arqueo_data['moneda_005'], arqueo_data['moneda_001'],
                        total_billetes, total_monedas, total_contado,
                        notas_arqueo, usuario_sistema_id
                    ])
            except Exception as e:
                print(f"Error al guardar arqueo: {e}")
                # No fallar el cierre si hay error en el arqueo
            
            # Generar ticket de cierre
            try:
                generar_ticket_cierre_caja(
                    caja_abierta=caja_abierta,
                    usuario_cierre_id=usuario_sistema_id,
                    saldo_inicial=float(caja_abierta.saldoInicial),
                    total_ingresos=float(total_ingresos),
                    total_egresos=float(total_egresos),
                    saldo_teorico=saldo_teorico,
                    total_contado=total_contado,
                    diferencia=diferencia,
                    observaciones=observaciones,
                    arqueo_data=arqueo_data
                )
            except Exception as e:
                print(f"Error al generar ticket de cierre: {e}")
                # No fallar el cierre si hay error en el ticket
            
            messages.success(request, f'Caja cerrada exitosamente. Diferencia: ${diferencia:.2f}')
            return redirect('caja:historial')
            
        except Exception as e:
            messages.error(request, f'Error al cerrar la caja: {str(e)}')
    
    # Obtener información del usuario que abrió la caja
    nombre_usuario_apertura = None
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT nombreCompleto FROM usuarios WHERE id = %s", 
                [caja_abierta.idUsuarioApertura]
            )
            row = cursor.fetchone()
            nombre_usuario_apertura = row[0] if row else None
    except:
        pass
    
    # Calcular totales para mostrar
    total_ingresos = float(caja_abierta.totalIngresosSistema or 0)
    total_egresos = float(caja_abierta.totalEgresosSistema or 0)
    saldo_inicial = float(caja_abierta.saldoInicial or 0)
    saldo_teorico = saldo_inicial + total_ingresos - total_egresos
    
    # Verificar si ya existe un arqueo guardado (en caso de edición)
    arqueo_existente = None
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM arqueos_caja WHERE idCierreCaja = %s ORDER BY id DESC LIMIT 1",
                [caja_abierta.id]
            )
            row = cursor.fetchone()
            if row:
                arqueo_existente = {
                    'billete_100': row[2], 'billete_50': row[3], 'billete_20': row[4],
                    'billete_10': row[5], 'billete_5': row[6],
                    'moneda_1': row[7], 'moneda_050': row[8], 'moneda_025': row[9],
                    'moneda_010': row[10], 'moneda_005': row[11], 'moneda_001': row[12],
                    'notas_arqueo': row[16]
                }
    except:
        pass
    
    context = {
        'caja_abierta': caja_abierta,
        'nombre_usuario_apertura': nombre_usuario_apertura,
        'total_ventas': total_ingresos,  # Por ahora, total_ingresos representa las ventas
        'entradas': 0,  # Otros ingresos (por implementar con movimientos)
        'salidas': total_egresos,
        'saldo_inicial': saldo_inicial,
        'total_ingresos': total_ingresos,
        'saldo_teorico': saldo_teorico,
        'arqueo_existente': arqueo_existente,
        'titulo': 'Cerrar Caja'
    }
    return render(request, 'caja/cerrar.html', context)


@login_required
def estado_caja(request):
    """Estado actual de la caja"""
    # Usar la función centralizada para obtener caja abierta
    caja_abierta_data = CierreCaja.obtener_caja_abierta()
    
    # Si no hay caja abierta del día actual, redirigir a apertura
    if not caja_abierta_data:
        # Verificar si hay cajas de días anteriores para informar al usuario
        from django.utils import timezone
        hoy = timezone.localtime().date()
        caja_anterior = CierreCaja.objects.filter(
            estado='ABIERTA',
            anulado=False,
            fechaApertura__date__lt=hoy
        ).first()
        
        if caja_anterior:
            fecha_anterior = timezone.localtime(caja_anterior.fechaApertura).strftime("%d/%m/%Y")
            messages.warning(request, f'Hay una caja abierta del {fecha_anterior}. Debe cerrarla y abrir una nueva para hoy.')
        else:
            messages.info(request, 'No hay ninguna caja abierta para el día de hoy')
        
        return redirect('caja:abrir')
    
    # Obtener el objeto CierreCaja completo
    caja_abierta = CierreCaja.objects.get(id=caja_abierta_data['id'])
    
    # Obtener información de la caja
    try:
        caja = Caja.objects.get(id=caja_abierta_data['idCaja'])
        nombre_caja = caja.nombre
    except Caja.DoesNotExist:
        caja = None
        nombre_caja = f"Caja {caja_abierta.idCaja}"
    
    # Por ahora, sin movimientos hasta que se cree la tabla
    total_ingresos = caja_abierta.totalIngresosSistema or 0
    total_egresos = caja_abierta.totalEgresosSistema or 0
    saldo_teorico = caja_abierta.saldoInicial + total_ingresos - total_egresos
    ultimos_movimientos = []
    
    context = {
        'caja_abierta': caja_abierta,
        'apertura': {
            'id': caja_abierta.id,
            'idCaja': caja_abierta.idCaja,
            'caja_nombre': nombre_caja,
            'fechaApertura': caja_abierta.fechaApertura,
            'saldoInicial': caja_abierta.saldoInicial,
            'estado': caja_abierta.estado
        },  # Objeto preparado para el template
        'caja': caja,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'saldo_teorico': saldo_teorico,
        'ultimos_movimientos': ultimos_movimientos,
        'titulo': 'Estado de Caja'
    }
    return render(request, 'caja/estado.html', context)


@login_required
def lista_movimientos(request):
    """Lista todos los registros de cierres_caja (aperturas y cierres)"""
    # Obtener todos los registros de cierres_caja ordenados por fecha
    movimientos = CierreCaja.objects.all().order_by('-fechaApertura')
    
    # Crear una lista con información adicional para el template
    movimientos_con_info = []
    for movimiento in movimientos:
        try:
            caja = Caja.objects.get(id=movimiento.idCaja)
            caja_codigo = caja.codigo
            caja_nombre_extra = caja.nombre
        except Caja.DoesNotExist:
            caja_codigo = f"C{movimiento.idCaja}"
            caja_nombre_extra = f"Caja {movimiento.idCaja}"
        
        # Crear un objeto con la información adicional
        movimiento_info = {
            'movimiento': movimiento,
            'caja_codigo': caja_codigo,
            'caja_nombre_extra': caja_nombre_extra
        }
        movimientos_con_info.append(movimiento_info)
    
    paginator = Paginator(movimientos_con_info, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener caja abierta para mostrar en contexto
    caja_abierta = CierreCaja.objects.filter(
        estado='ABIERTA',
        anulado=False
    ).first()
    
    context = {
        'page_obj': page_obj,
        'caja_abierta': caja_abierta,
        'titulo': 'Historial de Movimientos de Caja'
    }
    return render(request, 'caja/movimientos.html', context)
    
    context = {
        'page_obj': page_obj,
        'caja_abierta': caja_abierta,
        'titulo': 'Movimientos de Caja'
    }
    return render(request, 'caja/movimientos.html', context)


@login_required
def agregar_movimiento(request):
    """Agregar un movimiento a la caja"""
    # Verificar que hay una caja abierta
    caja_abierta = CierreCaja.objects.filter(
        estado='ABIERTA',
        anulado=False
    ).first()
    
    if not caja_abierta:
        messages.error(request, 'No hay ninguna caja abierta.')
        return redirect('caja:abrir')
    
    if request.method == 'POST':
        # Por ahora solo mostrar mensaje hasta que se cree la tabla movimientos_caja
        messages.info(request, 'Función de movimientos pendiente de implementar (tabla no existe)')
        return redirect('caja:estado')
    
    context = {
        'caja_abierta': caja_abierta,
        'titulo': 'Agregar Movimiento'
    }
    return render(request, 'caja/movimiento.html', context)


@login_required
def historial_cierres(request):
    """Mostrar historial de cierres de caja"""
    return redirect('caja:cierres')


@login_required
def lista_aperturas(request):
    """Lista todas las aperturas/cierres de caja"""
    cierres = CierreCaja.objects.all().order_by('-fechaApertura')[:50]
    
    context = {
        'cierres': cierres,
        'titulo': 'Historial de Cajas'
    }
    return render(request, 'caja/aperturas.html', context)


@login_required
def lista_cierres(request):
    """Lista todos los cierres de caja con información completa"""
    from datetime import datetime, timedelta
    
    # Obtener parámetros de filtro
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    usuario_id = request.GET.get('usuario')
    
    # Query base: solo cierres cerrados
    with connection.cursor() as cursor:
        # Construir query dinámicamente
        query = """
            SELECT 
                cc.id,
                cc.idCaja,
                c.nombre as caja_nombre,
                cc.fechaApertura,
                cc.fechaCierre,
                TIMESTAMPDIFF(MINUTE, cc.fechaApertura, cc.fechaCierre) as duracion_minutos,
                cc.idUsuarioApertura,
                ua.nombreCompleto as usuario_apertura,
                cc.idUsuarioCierre,
                uc.nombreCompleto as usuario_cierre,
                cc.saldoInicial,
                cc.totalIngresosSistema,
                cc.totalEgresosSistema,
                cc.saldoTeoricoSistema,
                cc.totalContadoFisico,
                cc.diferencia,
                cc.estado
            FROM cierres_caja cc
            LEFT JOIN cajas c ON c.id = cc.idCaja
            LEFT JOIN usuarios ua ON ua.id = cc.idUsuarioApertura
            LEFT JOIN usuarios uc ON uc.id = cc.idUsuarioCierre
            WHERE cc.estado = 'CERRADA' AND cc.anulado = 0
        """
        
        params = []
        
        # Aplicar filtros
        if fecha_inicio:
            query += " AND DATE(cc.fechaCierre) >= %s"
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += " AND DATE(cc.fechaCierre) <= %s"
            params.append(fecha_fin)
        
        if usuario_id:
            query += " AND cc.idUsuarioCierre = %s"
            params.append(usuario_id)
        
        query += " ORDER BY cc.fechaCierre DESC LIMIT 50"
        
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        cierres_raw = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # Procesar los cierres
    cierres = []
    for cierre in cierres_raw:
        # Calcular duración en formato legible
        duracion_minutos = cierre['duracion_minutos'] or 0
        horas = duracion_minutos // 60
        minutos = duracion_minutos % 60
        
        cierres.append({
            'id': cierre['id'],
            'caja_nombre': cierre['caja_nombre'] or f"Caja {cierre['idCaja']}",
            'fecha_apertura': cierre['fechaApertura'],
            'fecha_cierre': cierre['fechaCierre'],
            'duracion': f"{horas} horas" if horas > 0 else f"{minutos} minutos",
            'duracion_minutos': duracion_minutos,
            'usuario_apertura': cierre['usuario_apertura'] or 'Usuario desconocido',
            'usuario_cierre': cierre['usuario_cierre'] or 'Usuario desconocido',
            'monto_inicial': float(cierre['saldoInicial'] or 0),
            'total_ventas': float(cierre['totalIngresosSistema'] or 0),
            'otros_ingresos': 0,  # Por implementar cuando exista tabla de movimientos
            'total_egresos': float(cierre['totalEgresosSistema'] or 0),
            'efectivo_esperado': float(cierre['saldoTeoricoSistema'] or 0),
            'efectivo_contado': float(cierre['totalContadoFisico'] or 0),
            'diferencia': float(cierre['diferencia'] or 0),
            'estado_diferencia': 'exacto' if abs(float(cierre['diferencia'] or 0)) < 0.01 else ('sobrante' if float(cierre['diferencia'] or 0) > 0 else 'faltante')
        })
    
    # Calcular estadísticas
    total_cierres = len(cierres)
    
    # Ventas promedio
    if cierres:
        ventas_promedio = sum(c['total_ventas'] for c in cierres) / len(cierres)
    else:
        ventas_promedio = 0
    
    # Mejor día (por ventas)
    mejor_dia = None
    mejor_dia_ventas = 0
    if cierres:
        for cierre in cierres:
            if cierre['total_ventas'] > mejor_dia_ventas:
                mejor_dia_ventas = cierre['total_ventas']
                mejor_dia = cierre
    
    # Total del mes actual
    mes_actual = datetime.now().month
    total_mes = sum(c['total_ventas'] for c in cierres if cierre['fecha_cierre'] and cierre['fecha_cierre'].month == mes_actual)
    
    # Verificar si hay caja abierta
    caja_abierta = CierreCaja.objects.filter(estado='ABIERTA', anulado=False).first()
    
    # Obtener lista de usuarios para filtro
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, nombreCompleto FROM usuarios WHERE activo = 1 ORDER BY nombreCompleto")
        usuarios_raw = cursor.fetchall()
        usuarios = [{'id': u[0], 'nombre': u[1]} for u in usuarios_raw]
    
    context = {
        'cierres': cierres,
        'total_cierres': total_cierres,
        'ventas_promedio': ventas_promedio,
        'mejor_dia': mejor_dia,
        'mejor_dia_ventas': mejor_dia_ventas,
        'total_mes': total_mes,
        'caja_abierta': caja_abierta,
        'usuarios': usuarios,
        'titulo': 'Cierres de Caja'
    }
    return render(request, 'caja/cierres.html', context)


@login_required
def dashboard_caja(request):
    """Dashboard de caja"""
    # Verificar si hay una caja abierta
    caja_abierta = CierreCaja.objects.filter(
        estado='ABIERTA',
        anulado=False
    ).first()
    
    context = {
        'caja_abierta': caja_abierta,
        'puede_abrir_caja': not caja_abierta,
        'cajas_disponibles': Caja.objects.filter(activa=True).exists(),
        'titulo': 'Dashboard de Caja'
    }
    return render(request, 'caja/dashboard.html', context)


def verificar_caja_abierta(request):
    """Verificar si hay una caja abierta"""
    try:
        caja_abierta = CierreCaja.objects.filter(
            estado='ABIERTA',
            anulado=False
        ).first()
        
        caja_nombre = None
        if caja_abierta:
            try:
                caja = Caja.objects.get(id=caja_abierta.idCaja)
                caja_nombre = caja.nombre
            except Caja.DoesNotExist:
                caja_nombre = f"Caja {caja_abierta.idCaja}"
        
        return JsonResponse({
            'caja_abierta': caja_abierta is not None,
            'caja_nombre': caja_nombre
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def iniciar_dia_caja(request):
    """Iniciar nuevo día de caja - DESHABILITADO: Ahora se requiere cierre manual"""
    messages.warning(request, '⚠️ Esta función está deshabilitada.')
    messages.info(request, 'Ahora debes cerrar manualmente la caja abierta antes de abrir una nueva.')
    messages.info(request, 'Dirígete a "Cerrar Caja" para cerrar la caja pendiente, luego podrás abrir una nueva.')
    return redirect('caja:estado')


def verificar_caja_dia_actual():
    """Verificar si hay una caja abierta del día actual (sin crear nuevas)"""
    from datetime import date
    
    hoy = date.today()
    caja_abierta = CierreCaja.objects.filter(
        estado='ABIERTA',
        anulado=False,
        fechaApertura__date=hoy
    ).first()
    
    return caja_abierta


def cerrar_caja_automatica(caja_abierta, usuario):
    """Cerrar caja automáticamente sin validación de montos"""
    try:
        # Actualizar registro con cierre automático
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE cierres_caja 
                SET idUsuarioCierre = %s,
                    fechaCierre = %s,
                    estado = 'CERRADA',
                    totalContadoFisico = saldoTeoricoSistema,
                    diferencia = 0
                WHERE id = %s
            """, [usuario.id, timezone.now(), caja_abierta.id])
        
        return True
    except Exception as e:
        raise Exception(f"Error al cerrar caja: {str(e)}")


def abrir_caja_automatica(usuario):
    """Abrir nueva caja automáticamente con saldo inicial de 0"""
    try:
        # Obtener la primera caja activa disponible
        caja = Caja.objects.filter(activa=True).first()
        if not caja:
            raise Exception("No hay cajas activas disponibles")
        
        # Crear nueva apertura de caja
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO cierres_caja 
                (idCaja, idUsuarioApertura, fechaApertura, saldoInicial, 
                 totalIngresosSistema, totalEgresosSistema, saldoTeoricoSistema,
                 totalContadoFisico, diferencia, estado, creadoPor, creadoDate, anulado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                caja.id,           # idCaja
                usuario.id,        # idUsuarioApertura  
                timezone.now(),    # fechaApertura
                0.0000,           # saldoInicial
                0.0000,           # totalIngresosSistema
                0.0000,           # totalEgresosSistema
                0.0000,           # saldoTeoricoSistema
                0.0000,           # totalContadoFisico
                0.0000,           # diferencia
                'ABIERTA',        # estado
                usuario.id,       # creadoPor
                timezone.now(),   # creadoDate
                False             # anulado
            ])
            
            # Obtener el ID del registro insertado
            caja_id = cursor.lastrowid
        
        # Obtener el objeto creado para devolverlo
        nueva_caja = CierreCaja.objects.get(id=caja_id)
        return nueva_caja
        
    except Exception as e:
        raise Exception(f"Error al abrir caja: {str(e)}")


def generar_ticket_cierre_caja(caja_abierta, usuario_cierre_id, saldo_inicial, 
                                 total_ingresos, total_egresos, saldo_teorico, 
                                 total_contado, diferencia, observaciones, arqueo_data=None):
    """
    Genera un ticket térmico de cierre de caja con el formato de la imagen
    Incluye el detalle del arqueo físico si está disponible
    """
    from datetime import datetime
    from escpos.printer import Usb, Network, File
    
    try:
        # Obtener configuración de empresa
        from usuarios.models import ConfiguracionEmpresa
        empresa_config = ConfiguracionEmpresa.obtener_configuracion()
        
        # Obtener datos del usuario que cerró
        usuario_cierre_nombre = "Usuario"
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT nombreCompleto FROM usuarios WHERE id = %s", 
                    [usuario_cierre_id]
                )
                row = cursor.fetchone()
                if row:
                    usuario_cierre_nombre = row[0]
        except:
            pass
        
        # Configurar impresora (ajustar según tu configuración)
        try:
            # Intenta con impresora USB (ajusta vendor_id y product_id según tu impresora)
            p = Usb(0x04b8, 0x0e15)  # IDs de ejemplo para Epson
        except:
            try:
                # Intenta con impresora de red
                p = Network("192.168.1.100")  # IP de ejemplo
            except:
                # Fallback: guardar en archivo
                import os
                ticket_dir = os.path.join(os.path.dirname(__file__), 'tickets_cierres')
                os.makedirs(ticket_dir, exist_ok=True)
                ticket_file = os.path.join(ticket_dir, f'cierre_{caja_abierta.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
                p = File(ticket_file)
        
        # Iniciar ticket
        p.set(align='center', width=2, height=2)
        
        # Logo o nombre de empresa
        if empresa_config and empresa_config.nombre_comercial:
            p.text(empresa_config.nombre_comercial + '\n')
        else:
            p.text('FARMACIA FE Y SALUD\n')
        
        p.set(align='center', width=1, height=1)
        p.text('=' * 42 + '\n')
        p.set(bold=True)
        p.text('RESUMEN DE CIERRE\n')
        p.set(bold=False)
        p.text('=' * 42 + '\n\n')
        
        # Información de la caja
        p.set(align='left')
        fecha_apertura = caja_abierta.fechaApertura.strftime('%d/%m/%Y %H:%M')
        fecha_cierre = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        p.text(f'Caja: Caja Principal\n')
        p.text(f'Apertura: {fecha_apertura}\n')
        p.text(f'Cierre: {fecha_cierre}\n')
        p.text(f'Usuario: {usuario_cierre_nombre}\n')
        p.text('-' * 42 + '\n\n')
        
        # Formato: descripción alineada a izquierda, valor a derecha
        def print_line(descripcion, valor):
            valor_str = f'${valor:.2f}'
            # Calcular espacios para alinear (42 caracteres total)
            espacios_necesarios = 42 - len(descripcion) - len(valor_str)
            if espacios_necesarios < 1:
                espacios_necesarios = 1
            p.text(f'{descripcion}{" " * espacios_necesarios}{valor_str}\n')
        
        # Arqueo de Caja Físico (si está disponible)
        if arqueo_data:
            p.set(bold=True)
            p.text('ARQUEO DE CAJA FISICO\n')
            p.set(bold=False)
            p.text('-' * 42 + '\n')
            
            # Billetes
            p.text('Billetes:\n')
            if arqueo_data.get('billete_100', 0) > 0:
                p.text(f"  $100.00 x {arqueo_data['billete_100']:3d}    ${arqueo_data['billete_100'] * 100:.2f}\n")
            if arqueo_data.get('billete_50', 0) > 0:
                p.text(f"  $50.00  x {arqueo_data['billete_50']:3d}    ${arqueo_data['billete_50'] * 50:.2f}\n")
            if arqueo_data.get('billete_20', 0) > 0:
                p.text(f"  $20.00  x {arqueo_data['billete_20']:3d}    ${arqueo_data['billete_20'] * 20:.2f}\n")
            if arqueo_data.get('billete_10', 0) > 0:
                p.text(f"  $10.00  x {arqueo_data['billete_10']:3d}    ${arqueo_data['billete_10'] * 10:.2f}\n")
            if arqueo_data.get('billete_5', 0) > 0:
                p.text(f"  $5.00   x {arqueo_data['billete_5']:3d}    ${arqueo_data['billete_5'] * 5:.2f}\n")
            
            # Monedas
            p.text('\nMonedas:\n')
            if arqueo_data.get('moneda_1', 0) > 0:
                p.text(f"  $1.00   x {arqueo_data['moneda_1']:3d}    ${arqueo_data['moneda_1'] * 1:.2f}\n")
            if arqueo_data.get('moneda_050', 0) > 0:
                p.text(f"  $0.50   x {arqueo_data['moneda_050']:3d}    ${arqueo_data['moneda_050'] * 0.50:.2f}\n")
            if arqueo_data.get('moneda_025', 0) > 0:
                p.text(f"  $0.25   x {arqueo_data['moneda_025']:3d}    ${arqueo_data['moneda_025'] * 0.25:.2f}\n")
            if arqueo_data.get('moneda_010', 0) > 0:
                p.text(f"  $0.10   x {arqueo_data['moneda_010']:3d}    ${arqueo_data['moneda_010'] * 0.10:.2f}\n")
            if arqueo_data.get('moneda_005', 0) > 0:
                p.text(f"  $0.05   x {arqueo_data['moneda_005']:3d}    ${arqueo_data['moneda_005'] * 0.05:.2f}\n")
            if arqueo_data.get('moneda_001', 0) > 0:
                p.text(f"  $0.01   x {arqueo_data['moneda_001']:3d}    ${arqueo_data['moneda_001'] * 0.01:.2f}\n")
            
            p.text('-' * 42 + '\n\n')
        
        # Detalles financieros
        p.set(bold=True)
        p.text('RESUMEN DE MOVIMIENTOS\n')
        p.set(bold=False)
        p.text('-' * 42 + '\n')
        
        print_line('Saldo Inicial (+)', saldo_inicial)
        print_line('Total Ingresos Sistema (+)', total_ingresos)
        print_line('Total Egresos Sistema (-)', total_egresos)
        print_line('Saldo Teorico Sistema (=)', saldo_teorico)
        p.text('\n')
        print_line('Total Contado Fisico (=)', total_contado)
        p.text('\n')
        
        # Diferencia
        p.set(bold=True)
        if abs(diferencia) < 0.01:
            p.text('Diferencia: $0.00 - Sin diferencia\n')
        elif diferencia > 0:
            p.text(f'Diferencia: +${abs(diferencia):.2f} SOBRANTE\n')
        else:
            p.text(f'Diferencia: -${abs(diferencia):.2f} FALTANTE\n')
        p.set(bold=False)
        
        p.text('\n')
        p.text('-' * 42 + '\n')
        
        # Observaciones si existen
        if observaciones and observaciones.strip():
            p.text('Observaciones:\n')
            p.text(observaciones[:100] + '\n\n')  # Limitar a 100 caracteres
        
        # Pie de ticket
        p.text('=' * 42 + '\n')
        p.set(align='center')
        p.text('GRACIAS - CIERRE GENERADO\n')
        p.text(f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}\n')
        
        # Cortar papel
        p.cut()
        
        # Cerrar conexión
        p.close()
        
        return True
        
    except Exception as e:
        print(f"Error al imprimir ticket de cierre: {e}")
        # No fallar la operación si hay error en la impresión
        return False


@login_required
def detalle_cierre_api(request, cierre_id):
    """API para obtener el detalle completo de un cierre de caja"""
    try:
        with connection.cursor() as cursor:
            # Obtener información del cierre
            cursor.execute("""
                SELECT 
                    cc.id,
                    cc.idCaja,
                    c.nombre as caja_nombre,
                    cc.fechaApertura,
                    cc.fechaCierre,
                    TIMESTAMPDIFF(MINUTE, cc.fechaApertura, cc.fechaCierre) as duracion_minutos,
                    cc.idUsuarioApertura,
                    ua.nombreCompleto as usuario_apertura,
                    cc.idUsuarioCierre,
                    uc.nombreCompleto as usuario_cierre,
                    cc.saldoInicial,
                    cc.totalIngresosSistema,
                    cc.totalEgresosSistema,
                    cc.saldoTeoricoSistema,
                    cc.totalContadoFisico,
                    cc.diferencia
                FROM cierres_caja cc
                LEFT JOIN cajas c ON c.id = cc.idCaja
                LEFT JOIN usuarios ua ON ua.id = cc.idUsuarioApertura
                LEFT JOIN usuarios uc ON uc.id = cc.idUsuarioCierre
                WHERE cc.id = %s AND cc.estado = 'CERRADA'
            """, [cierre_id])
            
            row = cursor.fetchone()
            
            if not row:
                return JsonResponse({'error': 'Cierre no encontrado'}, status=404)
            
            # Procesar los datos
            duracion_minutos = row[5] or 0
            horas = duracion_minutos // 60
            minutos = duracion_minutos % 60
            
            # Buscar arqueo si existe
            cursor.execute("""
                SELECT 
                    billete_100, billete_50, billete_20, billete_10, billete_5,
                    moneda_1, moneda_050, moneda_025, moneda_010, moneda_005, moneda_001,
                    total_billetes, total_monedas, total_general, notas_arqueo
                FROM arqueos_caja
                WHERE idCierreCaja = %s
                ORDER BY id DESC
                LIMIT 1
            """, [cierre_id])
            
            arqueo_row = cursor.fetchone()
            arqueo = None
            
            if arqueo_row:
                arqueo = {
                    'billetes': {
                        '100': arqueo_row[0],
                        '50': arqueo_row[1],
                        '20': arqueo_row[2],
                        '10': arqueo_row[3],
                        '5': arqueo_row[4],
                    },
                    'monedas': {
                        '1': arqueo_row[5],
                        '0.50': arqueo_row[6],
                        '0.25': arqueo_row[7],
                        '0.10': arqueo_row[8],
                        '0.05': arqueo_row[9],
                        '0.01': arqueo_row[10],
                    },
                    'total_billetes': float(arqueo_row[11]),
                    'total_monedas': float(arqueo_row[12]),
                    'total_general': float(arqueo_row[13]),
                    'notas': arqueo_row[14]
                }
            
            # TODO: Obtener desglose de ventas por forma de pago cuando esté disponible
            # Por ahora, usaremos datos de ejemplo basados en el total
            total_ventas = float(row[11] or 0)
            desglose_pagos = {
                'efectivo': {
                    'monto': total_ventas * 0.58,
                    'porcentaje': 58
                },
                'tarjeta': {
                    'monto': total_ventas * 0.36,
                    'porcentaje': 36
                },
                'transferencia': {
                    'monto': total_ventas * 0.06,
                    'porcentaje': 6
                }
            }
            
            data = {
                'id': row[0],
                'caja_nombre': row[2] or f"Caja {row[1]}",
                'fecha_apertura': row[3].strftime('%d/%m/%Y %H:%M:%S'),
                'fecha_cierre': row[4].strftime('%d/%m/%Y %H:%M:%S'),
                'duracion': f"{horas} horas" if horas > 0 else f"{minutos} minutos",
                'duracion_completa': f"{horas} horas {minutos} minutos" if horas > 0 else f"{minutos} minutos",
                'usuario_apertura': row[7] or 'Usuario desconocido',
                'usuario_cierre': row[9] or 'Usuario desconocido',
                'monto_inicial': float(row[10] or 0),
                'total_ventas': float(row[11] or 0),
                'otros_ingresos': 0,  # Por implementar
                'total_egresos': float(row[12] or 0),
                'efectivo_esperado': float(row[13] or 0),
                'efectivo_contado': float(row[14] or 0),
                'diferencia': float(row[15] or 0),
                'arqueo': arqueo,
                'desglose_pagos': desglose_pagos
            }
            
            return JsonResponse(data)
            
    except Exception as e:
        print(f"Error en detalle_cierre_api: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def imprimir_cierre_ticket(request, cierre_id):
    """Vista para imprimir el ticket de cierre en HTML"""
    try:
        # Obtener el cierre
        cierre = get_object_or_404(CierreCaja, id=cierre_id)
        
        # Obtener la caja
        try:
            caja = Caja.objects.get(id=cierre.idCaja)
        except Caja.DoesNotExist:
            caja = None
            
        # Obtener usuario de cierre
        usuario_cierre = None
        if cierre.idUsuarioCierre:
            try:
                from usuarios.models import Usuario
                usuario_cierre = Usuario.objects.get(id=cierre.idUsuarioCierre)
            except:
                pass
                
        # Obtener configuración de empresa
        from usuarios.models import ConfiguracionEmpresa
        empresa = ConfiguracionEmpresa.obtener_configuracion()
        
        # Obtener arqueo si existe
        arqueo = ArqueoCaja.objects.filter(idCierreCaja=cierre.id).order_by('-id').first()
        
        arqueo_detalles = None
        if arqueo:
            arqueo_detalles = {
                'billetes': [
                    {'valor': 100, 'cantidad': arqueo.billete_100, 'total': arqueo.billete_100 * 100},
                    {'valor': 50, 'cantidad': arqueo.billete_50, 'total': arqueo.billete_50 * 50},
                    {'valor': 20, 'cantidad': arqueo.billete_20, 'total': arqueo.billete_20 * 20},
                    {'valor': 10, 'cantidad': arqueo.billete_10, 'total': arqueo.billete_10 * 10},
                    {'valor': 5, 'cantidad': arqueo.billete_5, 'total': arqueo.billete_5 * 5},
                ],
                'monedas': [
                    {'valor': 1.00, 'cantidad': arqueo.moneda_1, 'total': arqueo.moneda_1 * 1.00},
                    {'valor': 0.50, 'cantidad': arqueo.moneda_050, 'total': arqueo.moneda_050 * 0.50},
                    {'valor': 0.25, 'cantidad': arqueo.moneda_025, 'total': arqueo.moneda_025 * 0.25},
                    {'valor': 0.10, 'cantidad': arqueo.moneda_010, 'total': arqueo.moneda_010 * 0.10},
                    {'valor': 0.05, 'cantidad': arqueo.moneda_005, 'total': arqueo.moneda_005 * 0.05},
                    {'valor': 0.01, 'cantidad': arqueo.moneda_001, 'total': arqueo.moneda_001 * 0.01},
                ],
                'total_general': arqueo.total_general,
                'notas_arqueo': arqueo.notas_arqueo
            }
        
        context = {
            'cierre': cierre,
            'caja': caja,
            'usuario_cierre': usuario_cierre,
            'empresa': empresa,
            'arqueo': arqueo_detalles,
        }
        
        return render(request, 'caja/ticket_cierre.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al generar ticket: {str(e)}')
        return redirect('caja:cierres')
