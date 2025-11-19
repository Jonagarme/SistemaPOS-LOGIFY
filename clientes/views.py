from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.db import OperationalError
from .models import Cliente
from .forms import ClienteForm


@login_required
def lista_clientes(request):
    """Lista todos los clientes"""
    search = request.GET.get('search', '')
    
    clientes = Cliente.objects.filter(estado=True, anulado=False)
    
    if search:
        clientes = clientes.filter(
            Q(nombres__icontains=search) |
            Q(apellidos__icontains=search) |
            Q(razon_social__icontains=search) |
            Q(cedula_ruc__icontains=search) |
            Q(email__icontains=search)
        )
    
    paginator = Paginator(clientes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'titulo': 'Clientes'
    }
    return render(request, 'clientes/lista.html', context)


@login_required
def crear_cliente(request):
    """Crear nuevo cliente"""
    if request.method == 'POST':
        # Lógica para crear cliente
        messages.success(request, 'Cliente creado exitosamente')
        return redirect('clientes:lista')
    
    context = {
        'titulo': 'Crear Cliente'
    }
    return render(request, 'clientes/crear.html', context)


@login_required
def editar_cliente(request, pk):
    """Editar cliente existente"""
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.editado_por = request.user
            cliente.editado_date = timezone.now()
            cliente.save()
            messages.success(request, 'Cliente actualizado exitosamente')
            return redirect('clientes:detalle', pk=cliente.pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario')
    else:
        form = ClienteForm(instance=cliente)
    
    context = {
        'form': form,
        'cliente': cliente,
        'titulo': 'Editar Cliente'
    }
    return render(request, 'clientes/editar.html', context)


@login_required
def detalle_cliente(request, pk):
    """Ver detalles de un cliente"""
    cliente = get_object_or_404(Cliente, pk=pk)
    
    # Obtener historial de ventas (opcional)
    # ventas = cliente.ventas.filter(anulado=False).order_by('-fecha')[:10]
    
    context = {
        'cliente': cliente,
        'titulo': f'Cliente: {cliente.nombre_completo}',
        # 'ventas': ventas
    }
    return render(request, 'clientes/detalle.html', context)


@login_required
def eliminar_cliente(request, pk):
    """Eliminar cliente (marcar como inactivo)"""
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        cliente.estado = False
        cliente.anulado = True
        cliente.save()
        messages.success(request, 'Cliente eliminado exitosamente')
        return redirect('clientes:lista')
    
    context = {
        'cliente': cliente,
        'titulo': 'Eliminar Cliente'
    }
    return render(request, 'clientes/eliminar.html', context)


@login_required
def historial_cliente(request, pk):
    """Ver historial de compras del cliente"""
    cliente = get_object_or_404(Cliente, pk=pk)
    ventas = cliente.ventas.all()[:20]
    
    context = {
        'cliente': cliente,
        'ventas': ventas,
        'titulo': f'Historial: {cliente.nombre_completo}'
    }
    return render(request, 'clientes/historial.html', context)


@login_required
def buscar_clientes(request):
    """Buscar clientes via AJAX - Con soporte offline"""
    if request.method == 'GET':
        search = request.GET.get('search', '')
        
        try:
            clientes = Cliente.objects.filter(
                Q(nombres__icontains=search) |
                Q(apellidos__icontains=search) |
                Q(cedula_ruc__icontains=search),
                estado=True,
                anulado=False
            )[:10]
            
            clientes_data = []
            for cliente in clientes:
                clientes_data.append({
                    'id': cliente.id,
                    'cedula_ruc': cliente.cedula_ruc,
                    'nombre': cliente.nombre_completo,
                    'documento': cliente.cedula_ruc,
                    'telefono': cliente.telefono_principal
                })
            
            return JsonResponse({'clientes': clientes_data})
            
        except OperationalError:
            # Modo offline - buscar en localStorage del navegador
            # Retornar lista vacía, el frontend usará su cache
            return JsonResponse({
                'clientes': [],
                'modo_offline': True,
                'mensaje': 'Modo offline: Busca clientes desde el cache del navegador'
            })
        except Exception as e:
            return JsonResponse({
                'error': f'Error al buscar clientes: {str(e)}',
                'clientes': []
            })
    
    return JsonResponse({'error': 'Método no permitido'})
