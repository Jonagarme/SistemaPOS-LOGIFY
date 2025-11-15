from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from .models import Proveedor
from .forms import ProveedorForm


@login_required
def lista_proveedores(request):
    """Lista todos los proveedores"""
    search = request.GET.get('search', '')
    
    proveedores = Proveedor.objects.filter(estado=True, anulado=False)
    
    if search:
        proveedores = proveedores.filter(
            Q(razon_social__icontains=search) |
            Q(nombre_comercial__icontains=search) |
            Q(ruc__icontains=search) |
            Q(email__icontains=search)
        )
    
    paginator = Paginator(proveedores, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'titulo': 'Proveedores'
    }
    return render(request, 'proveedores/lista.html', context)


@login_required
def crear_proveedor(request):
    """Crear nuevo proveedor"""
    if request.method == 'POST':
        # Lógica para crear proveedor
        messages.success(request, 'Proveedor creado exitosamente')
        return redirect('proveedores:lista')
    
    context = {
        'titulo': 'Crear Proveedor'
    }
    return render(request, 'proveedores/crear.html', context)


@login_required
def editar_proveedor(request, pk):
    """Editar proveedor existente"""
    proveedor = get_object_or_404(Proveedor, pk=pk)
    
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.editado_por = request.user
            proveedor.editado_date = timezone.now()
            proveedor.save()
            messages.success(request, 'Proveedor actualizado exitosamente')
            return redirect('proveedores:detalle', pk=proveedor.pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario')
    else:
        form = ProveedorForm(instance=proveedor)
    
    context = {
        'form': form,
        'proveedor': proveedor,
        'titulo': 'Editar Proveedor'
    }
    return render(request, 'proveedores/editar.html', context)


@login_required
def detalle_proveedor(request, pk):
    """Ver detalles de un proveedor"""
    proveedor = get_object_or_404(Proveedor, pk=pk)
    
    # Obtener historial de compras (opcional)
    # compras = proveedor.compras.filter(anulado=False).order_by('-fecha')[:10]
    
    context = {
        'proveedor': proveedor,
        'titulo': f'Proveedor: {proveedor.nombre_completo}',
        # 'compras': compras
    }
    return render(request, 'proveedores/detalle.html', context)


@login_required
def eliminar_proveedor(request, pk):
    """Eliminar proveedor (marcar como inactivo)"""
    proveedor = get_object_or_404(Proveedor, pk=pk)
    
    if request.method == 'POST':
        proveedor.estado = False
        proveedor.anulado = True
        proveedor.save()
        messages.success(request, 'Proveedor eliminado exitosamente')
        return redirect('proveedores:lista')
    
    context = {
        'proveedor': proveedor,
        'titulo': 'Eliminar Proveedor'
    }
    return render(request, 'proveedores/eliminar.html', context)


@login_required
def historial_proveedor(request, pk):
    """Ver historial de compras del proveedor"""
    proveedor = get_object_or_404(Proveedor, pk=pk)
    # compras = proveedor.compras.all()[:20]  # Descomentarás cuando tengas el modelo
    
    context = {
        'proveedor': proveedor,
        # 'compras': compras,
        'titulo': f'Historial: {proveedor.nombre_completo}'
    }
    return render(request, 'proveedores/historial.html', context)


@login_required
def buscar_proveedores(request):
    """Buscar proveedores via AJAX"""
    if request.method == 'GET':
        search = request.GET.get('search', '')
        proveedores = Proveedor.objects.filter(
            Q(razon_social__icontains=search) |
            Q(nombre_comercial__icontains=search) |
            Q(ruc__icontains=search),
            estado=True,
            anulado=False
        )[:10]
        
        proveedores_data = []
        for proveedor in proveedores:
            proveedores_data.append({
                'id': proveedor.id,
                'ruc': proveedor.ruc,
                'nombre': proveedor.razon_social,
                'documento': proveedor.ruc,
                'telefono': proveedor.telefono_principal
            })
        
        return JsonResponse({'proveedores': proveedores_data})
    
    return JsonResponse({'error': 'Método no permitido'})
