from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.template.loader import render_to_string
from datetime import date, datetime, timedelta
from decimal import Decimal
import json

from .models import (
    CuentaContable, AsientoContable, MovimientoContable,
    CuentaPorCobrar, PagoCuentaPorCobrar,
    CuentaPorPagar, PagoCuentaPorPagar,
    CuentaBancaria, MovimientoBancario,
    CategoriaGasto, Gasto, FlujoCaja, TipoCuenta
)
from clientes.models import Cliente
from proveedores.models import Proveedor
from ventas.models import Venta


@login_required
def dashboard_contabilidad(request):
    """Dashboard principal de contabilidad"""
    # Resumen de cuentas por cobrar
    cxc_pendientes = CuentaPorCobrar.objects.filter(estado__in=['pendiente', 'parcial'])
    total_cxc = cxc_pendientes.aggregate(total=Sum('monto_pendiente'))['total'] or Decimal('0')
    cxc_vencidas = cxc_pendientes.filter(fecha_vencimiento__lt=date.today()).count()
    
    # Resumen de cuentas por pagar
    cxp_pendientes = CuentaPorPagar.objects.filter(estado__in=['pendiente', 'parcial'])
    total_cxp = cxp_pendientes.aggregate(total=Sum('monto_pendiente'))['total'] or Decimal('0')
    cxp_vencidas = cxp_pendientes.filter(fecha_vencimiento__lt=date.today()).count()
    
    # Saldos bancarios
    cuentas_bancarias = CuentaBancaria.objects.filter(activa=True)
    total_bancos = sum(cuenta.saldo_actual for cuenta in cuentas_bancarias)
    
    # Gastos del mes actual
    mes_actual = date.today().replace(day=1)
    gastos_mes = Gasto.objects.filter(
        fecha__gte=mes_actual,
        estado='pagado'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
    
    # Últimos movimientos
    ultimos_asientos = AsientoContable.objects.all()[:5]
    
    context = {
        'total_cxc': total_cxc,
        'cxc_vencidas': cxc_vencidas,
        'total_cxp': total_cxp,
        'cxp_vencidas': cxp_vencidas,
        'total_bancos': total_bancos,
        'gastos_mes': gastos_mes,
        'ultimos_asientos': ultimos_asientos,
        'cuentas_bancarias': cuentas_bancarias,
    }
    
    return render(request, 'contabilidad/dashboard.html', context)


@login_required
def cuentas_por_cobrar(request):
    """Gestión de cuentas por cobrar"""
    # Filtros
    cliente_id = request.GET.get('cliente')
    estado = request.GET.get('estado')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    cuentas = CuentaPorCobrar.objects.all()
    
    if cliente_id:
        cuentas = cuentas.filter(cliente_id=cliente_id)
    if estado:
        cuentas = cuentas.filter(estado=estado)
    if fecha_desde:
        cuentas = cuentas.filter(fecha_emision__gte=fecha_desde)
    if fecha_hasta:
        cuentas = cuentas.filter(fecha_emision__lte=fecha_hasta)
    
    # Paginación
    paginator = Paginator(cuentas, 20)
    page = request.GET.get('page')
    cuentas_page = paginator.get_page(page)
    
    # Datos para filtros
    clientes = Cliente.objects.filter(estado=True, anulado=False).order_by('nombres')
    
    # Resúmenes
    total_pendiente = cuentas.filter(estado__in=['pendiente', 'parcial']).aggregate(
        total=Sum('monto_pendiente')
    )['total'] or Decimal('0')
    
    context = {
        'cuentas': cuentas_page,
        'clientes': clientes,
        'total_pendiente': total_pendiente,
        'filtros': {
            'cliente_id': cliente_id,
            'estado': estado,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        }
    }
    
    return render(request, 'contabilidad/cuentas_por_cobrar.html', context)


@login_required
def cuentas_por_pagar(request):
    """Gestión de cuentas por pagar"""
    # Filtros
    proveedor_id = request.GET.get('proveedor')
    estado = request.GET.get('estado')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    cuentas = CuentaPorPagar.objects.all()
    
    if proveedor_id:
        cuentas = cuentas.filter(proveedor_id=proveedor_id)
    if estado:
        cuentas = cuentas.filter(estado=estado)
    if fecha_desde:
        cuentas = cuentas.filter(fecha_emision__gte=fecha_desde)
    if fecha_hasta:
        cuentas = cuentas.filter(fecha_emision__lte=fecha_hasta)
    
    # Paginación
    paginator = Paginator(cuentas, 20)
    page = request.GET.get('page')
    cuentas_page = paginator.get_page(page)
    
    # Datos para filtros
    proveedores = Proveedor.objects.filter(estado=True, anulado=False).order_by('razon_social')
    
    # Resúmenes
    total_pendiente = cuentas.filter(estado__in=['pendiente', 'parcial']).aggregate(
        total=Sum('monto_pendiente')
    )['total'] or Decimal('0')
    
    context = {
        'cuentas': cuentas_page,
        'proveedores': proveedores,
        'total_pendiente': total_pendiente,
        'filtros': {
            'proveedor_id': proveedor_id,
            'estado': estado,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        }
    }
    
    return render(request, 'contabilidad/cuentas_por_pagar.html', context)


@login_required
def flujo_caja(request):
    """Proyección y seguimiento del flujo de caja"""
    # Obtener período
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if not fecha_desde:
        fecha_desde = date.today().replace(day=1)  # Primer día del mes
    else:
        fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
    
    if not fecha_hasta:
        # Último día del mes siguiente
        if fecha_desde.month == 12:
            fecha_hasta = date(fecha_desde.year + 1, 1, 31)
        else:
            try:
                fecha_hasta = date(fecha_desde.year, fecha_desde.month + 1, 31)
            except ValueError:
                fecha_hasta = date(fecha_desde.year, fecha_desde.month + 1, 30)
    else:
        fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
    
    # Obtener datos de flujo de caja
    flujos = FlujoCaja.objects.filter(
        fecha__range=[fecha_desde, fecha_hasta]
    ).order_by('fecha')
    
    # Calcular saldo inicial
    saldo_inicial = sum(cuenta.saldo_actual for cuenta in CuentaBancaria.objects.filter(activa=True))
    
    # Proyecciones automáticas basadas en CxC y CxP
    cxc_periodo = CuentaPorCobrar.objects.filter(
        fecha_vencimiento__range=[fecha_desde, fecha_hasta],
        estado__in=['pendiente', 'parcial']
    )
    
    cxp_periodo = CuentaPorPagar.objects.filter(
        fecha_vencimiento__range=[fecha_desde, fecha_hasta],
        estado__in=['pendiente', 'parcial']
    )
    
    # Calcular totales
    total_cxc_periodo = cxc_periodo.aggregate(
        total=Sum('monto_pendiente')
    )['total'] or Decimal('0')
    
    total_cxp_periodo = cxp_periodo.aggregate(
        total=Sum('monto_pendiente')
    )['total'] or Decimal('0')
    
    context = {
        'flujos': flujos,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'saldo_inicial': saldo_inicial,
        'cxc_periodo': cxc_periodo,
        'cxp_periodo': cxp_periodo,
        'total_cxc_periodo': total_cxc_periodo,
        'total_cxp_periodo': total_cxp_periodo,
    }
    
    return render(request, 'contabilidad/flujo_caja.html', context)


@login_required
def conciliacion_bancaria(request):
    """Conciliación bancaria"""
    cuenta_id = request.GET.get('cuenta')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    cuentas_bancarias = CuentaBancaria.objects.filter(activa=True)
    
    if cuenta_id:
        cuenta_seleccionada = get_object_or_404(CuentaBancaria, id=cuenta_id)
        
        # Movimientos del período
        movimientos = MovimientoBancario.objects.filter(cuenta_bancaria=cuenta_seleccionada)
        
        if fecha_desde:
            movimientos = movimientos.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            movimientos = movimientos.filter(fecha__lte=fecha_hasta)
        
        # Separar movimientos conciliados y no conciliados
        conciliados = movimientos.filter(conciliado=True)
        no_conciliados = movimientos.filter(conciliado=False)
        
        # Calcular saldos
        saldo_libro = cuenta_seleccionada.saldo_actual
        saldo_conciliado = sum(mov.monto if mov.tipo == 'ingreso' else -mov.monto for mov in conciliados)
        diferencia = saldo_libro - saldo_conciliado
        
        context = {
            'cuentas_bancarias': cuentas_bancarias,
            'cuenta_seleccionada': cuenta_seleccionada,
            'conciliados': conciliados,
            'no_conciliados': no_conciliados,
            'saldo_libro': saldo_libro,
            'saldo_conciliado': saldo_conciliado,
            'diferencia': diferencia,
            'filtros': {
                'cuenta': cuenta_id,
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
            }
        }
    else:
        context = {
            'cuentas_bancarias': cuentas_bancarias,
            'filtros': {
                'cuenta': cuenta_id,
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
            }
        }
    
    return render(request, 'contabilidad/conciliacion_bancaria.html', context)


@login_required
def control_gastos(request):
    """Control y aprobación de gastos"""
    # Filtros
    categoria_id = request.GET.get('categoria')
    estado = request.GET.get('estado')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    gastos = Gasto.objects.all()
    
    if categoria_id:
        gastos = gastos.filter(categoria_id=categoria_id)
    if estado:
        gastos = gastos.filter(estado=estado)
    if fecha_desde:
        gastos = gastos.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        gastos = gastos.filter(fecha__lte=fecha_hasta)
    
    # Paginación
    paginator = Paginator(gastos, 20)
    page = request.GET.get('page')
    gastos_page = paginator.get_page(page)
    
    # Datos para filtros
    categorias = CategoriaGasto.objects.filter(activa=True).order_by('nombre')
    
    # Resúmenes por estado
    resumen_estados = Gasto.objects.values('estado').annotate(
        total=Sum('monto'),
        cantidad=Count('id')
    )
    
    context = {
        'gastos': gastos_page,
        'categorias': categorias,
        'resumen_estados': resumen_estados,
        'filtros': {
            'categoria_id': categoria_id,
            'estado': estado,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        }
    }
    
    return render(request, 'contabilidad/control_gastos.html', context)


@login_required
def reportes_contables(request):
    """Reportes contables principales"""
    fecha_corte = request.GET.get('fecha_corte', date.today().strftime('%Y-%m-%d'))
    fecha_corte = datetime.strptime(fecha_corte, '%Y-%m-%d').date()
    
    # Balance General
    activos = CuentaContable.objects.filter(
        tipo_cuenta__tipo='activo',
        activo=True
    ).order_by('codigo')
    
    pasivos = CuentaContable.objects.filter(
        tipo_cuenta__tipo='pasivo',
        activo=True
    ).order_by('codigo')
    
    patrimonio = CuentaContable.objects.filter(
        tipo_cuenta__tipo='patrimonio',
        activo=True
    ).order_by('codigo')
    
    # Estado de Resultados
    ingresos = CuentaContable.objects.filter(
        tipo_cuenta__tipo='ingreso',
        activo=True
    ).order_by('codigo')
    
    gastos = CuentaContable.objects.filter(
        tipo_cuenta__tipo='gasto',
        activo=True
    ).order_by('codigo')
    
    # Calcular totales
    total_activos = sum(cuenta.saldo_actual for cuenta in activos)
    total_pasivos = sum(cuenta.saldo_actual for cuenta in pasivos)
    total_patrimonio = sum(cuenta.saldo_actual for cuenta in patrimonio)
    total_ingresos = sum(cuenta.saldo_actual for cuenta in ingresos)
    total_gastos = sum(cuenta.saldo_actual for cuenta in gastos)
    
    utilidad_neta = total_ingresos - total_gastos
    
    context = {
        'fecha_corte': fecha_corte,
        'activos': activos,
        'pasivos': pasivos,
        'patrimonio': patrimonio,
        'ingresos': ingresos,
        'gastos': gastos,
        'total_activos': total_activos,
        'total_pasivos': total_pasivos,
        'total_patrimonio': total_patrimonio,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'utilidad_neta': utilidad_neta,
    }
    
    return render(request, 'contabilidad/reportes_contables.html', context)


# AJAX Views para operaciones rápidas

@login_required
def marcar_conciliado(request):
    """Marcar/desmarcar movimiento bancario como conciliado"""
    if request.method == 'POST':
        data = json.loads(request.body)
        movimiento_id = data.get('movimiento_id')
        conciliado = data.get('conciliado', False)
        
        try:
            movimiento = MovimientoBancario.objects.get(id=movimiento_id)
            movimiento.conciliado = conciliado
            movimiento.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Estado de conciliación actualizado'
            })
        except MovimientoBancario.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Movimiento no encontrado'
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


@login_required
def aprobar_gasto(request):
    """Aprobar o rechazar un gasto"""
    if request.method == 'POST':
        data = json.loads(request.body)
        gasto_id = data.get('gasto_id')
        accion = data.get('accion')  # 'aprobar' o 'rechazar'
        observaciones = data.get('observaciones', '')
        
        try:
            gasto = Gasto.objects.get(id=gasto_id)
            
            if accion == 'aprobar':
                gasto.estado = 'aprobado'
                gasto.usuario_aprueba = request.user
                gasto.fecha_aprobacion = timezone.now()
                mensaje = f'Gasto {gasto.numero} aprobado correctamente'
            elif accion == 'rechazar':
                gasto.estado = 'rechazado'
                gasto.usuario_aprueba = request.user
                gasto.fecha_aprobacion = timezone.now()
                mensaje = f'Gasto {gasto.numero} rechazado'
            
            if observaciones:
                gasto.observaciones = f"{gasto.observaciones}\n\n{observaciones}" if gasto.observaciones else observaciones
            
            gasto.save()
            
            return JsonResponse({
                'success': True,
                'message': mensaje
            })
        except Gasto.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Gasto no encontrado'
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


@login_required
def registrar_pago_cxc(request):
    """Registrar pago de cuenta por cobrar"""
    if request.method == 'POST':
        cuenta_id = request.POST.get('cuenta_id')
        monto = request.POST.get('monto')
        forma_pago = request.POST.get('forma_pago')
        referencia = request.POST.get('referencia', '')
        observaciones = request.POST.get('observaciones', '')
        
        try:
            cuenta = CuentaPorCobrar.objects.get(id=cuenta_id)
            monto_decimal = Decimal(monto)
            
            if monto_decimal > cuenta.monto_pendiente:
                messages.error(request, 'El monto no puede ser mayor al pendiente')
                return redirect('contabilidad:cuentas_por_cobrar')
            
            # Crear el pago
            pago = PagoCuentaPorCobrar.objects.create(
                cuenta_cobrar=cuenta,
                fecha_pago=date.today(),
                monto=monto_decimal,
                forma_pago=forma_pago,
                referencia=referencia,
                observaciones=observaciones,
                usuario=request.user
            )
            
            # Actualizar el monto pendiente
            cuenta.monto_pendiente -= monto_decimal
            
            # Actualizar estado
            if cuenta.monto_pendiente == 0:
                cuenta.estado = 'pagada'
            else:
                cuenta.estado = 'parcial'
            
            cuenta.save()
            
            messages.success(request, f'Pago registrado correctamente. Nuevo saldo: ${cuenta.monto_pendiente}')
            
        except Exception as e:
            messages.error(request, f'Error al registrar el pago: {str(e)}')
    
    return redirect('contabilidad:cuentas_por_cobrar')


@login_required
def registrar_pago_cxp(request):
    """Registrar pago de cuenta por pagar"""
    if request.method == 'POST':
        cuenta_id = request.POST.get('cuenta_id')
        monto = request.POST.get('monto')
        forma_pago = request.POST.get('forma_pago')
        referencia = request.POST.get('referencia', '')
        observaciones = request.POST.get('observaciones', '')
        
        try:
            cuenta = CuentaPorPagar.objects.get(id=cuenta_id)
            monto_decimal = Decimal(monto)
            
            if monto_decimal > cuenta.monto_pendiente:
                messages.error(request, 'El monto no puede ser mayor al pendiente')
                return redirect('contabilidad:cuentas_por_pagar')
            
            # Crear el pago
            pago = PagoCuentaPorPagar.objects.create(
                cuenta_pagar=cuenta,
                fecha_pago=date.today(),
                monto=monto_decimal,
                forma_pago=forma_pago,
                referencia=referencia,
                observaciones=observaciones,
                usuario=request.user
            )
            
            # Actualizar el monto pendiente
            cuenta.monto_pendiente -= monto_decimal
            
            # Actualizar estado
            if cuenta.monto_pendiente == 0:
                cuenta.estado = 'pagada'
            else:
                cuenta.estado = 'parcial'
            
            cuenta.save()
            
            messages.success(request, f'Pago registrado correctamente. Nuevo saldo: ${cuenta.monto_pendiente}')
            
        except Exception as e:
            messages.error(request, f'Error al registrar el pago: {str(e)}')
    
    return redirect('contabilidad:cuentas_por_pagar')
