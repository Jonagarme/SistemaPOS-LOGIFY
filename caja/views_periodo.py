from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from datetime import date, datetime, timedelta
from .models import CierrePeriodo
from ventas.models import FacturaVenta
from inventario.models import Compra, Producto
from decimal import Decimal
import calendar

@login_required
def lista_cierres_periodo(request):
    """Lista de cierres de periodo (mensuales y anuales)"""
    cierres = CierrePeriodo.objects.all().order_by('-anio', '-mes')
    
    context = {
        'cierres': cierres,
        'titulo': 'Cierres de Periodo'
    }
    return render(request, 'caja/periodo/lista.html', context)

@login_required
def crear_cierre_periodo(request):
    """Crear un nuevo cierre de periodo"""
    hoy = date.today()
    
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        anio = int(request.POST.get('anio'))
        mes = int(request.POST.get('mes')) if request.POST.get('mes') else None
        observaciones = request.POST.get('observaciones', '')
        
        # Validar duplicados
        if CierrePeriodo.objects.filter(tipo=tipo, anio=anio, mes=mes).exists():
            messages.error(request, f'Ya existe un cierre para este periodo.')
            return redirect('caja:crear_cierre_periodo')
            
        # Definir fechas inicio y fin
        if tipo == 'MENSUAL':
            fecha_inicio = date(anio, mes, 1)
            ultimo_dia = calendar.monthrange(anio, mes)[1]
            fecha_fin = date(anio, mes, ultimo_dia)
        else: # ANUAL
            fecha_inicio = date(anio, 1, 1)
            fecha_fin = date(anio, 12, 31)
            
        # Calcular totales
        # 1. Ventas (Facturas emitidas y autorizadas/pagadas, no anuladas)
        ventas = FacturaVenta.objects.filter(
            fechaEmision__date__range=[fecha_inicio, fecha_fin]
        ).exclude(estado='ANULADA')
        
        total_ventas = ventas.aggregate(Sum('total'))['total__sum'] or 0
        
        # 2. Compras
        compras = Compra.objects.filter(
            fecha__date__range=[fecha_inicio, fecha_fin]
        ).exclude(estado='anulada')
        
        total_compras = compras.aggregate(Sum('total'))['total__sum'] or 0
        
        # 3. Gastos (Si existe modelo de gastos, por ahora 0 o placeholder)
        # TODO: Implementar integración con gastos si existe
        total_gastos = 0
        
        # 4. Inventario (Snapshot actual)
        # Nota: Esto es el valor ACTUAL, no el histórico. 
        # Para histórico exacto se requeriría snapshot diario.
        productos = Producto.objects.filter(activo=True, anulado=False)
        valor_inventario_costo = sum(p.stock * p.costoUnidad for p in productos)
        valor_inventario_venta = sum(p.stock * p.precioVenta for p in productos)
        
        # Crear cierre
        cierre = CierrePeriodo(
            tipo=tipo,
            mes=mes,
            anio=anio,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            total_ventas=total_ventas,
            total_compras=total_compras,
            total_gastos=total_gastos,
            valor_inventario_costo=valor_inventario_costo,
            valor_inventario_venta=valor_inventario_venta,
            usuario=request.user,
            observaciones=observaciones
        )
        cierre.save()
        
        messages.success(request, f'Cierre {tipo} generado exitosamente.')
        return redirect('caja:lista_cierres_periodo')
    
    # Contexto para el formulario
    anios_disponibles = range(hoy.year, hoy.year - 5, -1)
    meses = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    
    context = {
        'anios': anios_disponibles,
        'meses': meses,
        'titulo': 'Generar Cierre de Periodo'
    }
    return render(request, 'caja/periodo/crear.html', context)

@login_required
def detalle_cierre_periodo(request, id):
    """Ver detalle de un cierre"""
    cierre = get_object_or_404(CierrePeriodo, id=id)
    
    # Calcular balance
    balance = cierre.total_ventas - cierre.total_compras - cierre.total_gastos + cierre.total_ingresos_extra
    
    context = {
        'cierre': cierre,
        'balance': balance,
        'titulo': f'Detalle de Cierre {cierre.mes}/{cierre.anio}' if cierre.mes else f'Detalle de Cierre {cierre.anio}'
    }
    return render(request, 'caja/periodo/detalle.html', context)
