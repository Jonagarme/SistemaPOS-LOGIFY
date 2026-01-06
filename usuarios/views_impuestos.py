from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Impuesto

@login_required
def lista_impuestos(request):
    impuestos = Impuesto.objects.all().order_by('codigo')
    return render(request, 'usuarios/impuestos/lista.html', {
        'impuestos': impuestos,
        'titulo': 'Gestión de Impuestos'
    })

@login_required
def crear_impuesto(request):
    if request.method == 'POST':
        codigo = request.POST.get('codigo')
        nombre = request.POST.get('nombre')
        porcentaje = request.POST.get('porcentaje')
        descripcion = request.POST.get('descripcion')
        vigenteDesde = request.POST.get('vigenteDesde') or None
        vigenteHasta = request.POST.get('vigenteHasta') or None
        activo = request.POST.get('activo') == 'on'
        
        try:
            # Validación: Si este impuesto será activo, desactivar los demás
            if activo:
                Impuesto.objects.filter(activo=True).update(activo=False)
                
            Impuesto.objects.create(
                codigo=codigo,
                nombre=nombre,
                porcentaje=porcentaje,
                descripcion=descripcion,
                vigenteDesde=vigenteDesde,
                vigenteHasta=vigenteHasta,
                activo=activo
            )
            messages.success(request, 'Impuesto creado exitosamente.')
            return redirect('usuarios:lista_impuestos')
        except Exception as e:
            messages.error(request, f'Error al crear impuesto: {str(e)}')
            
    return render(request, 'usuarios/impuestos/crear.html', {
        'titulo': 'Crear Impuesto'
    })

@login_required
def editar_impuesto(request, id):
    impuesto = get_object_or_404(Impuesto, id=id)
    
    if request.method == 'POST':
        impuesto.codigo = request.POST.get('codigo')
        impuesto.nombre = request.POST.get('nombre')
        impuesto.porcentaje = request.POST.get('porcentaje')
        impuesto.descripcion = request.POST.get('descripcion')
        impuesto.vigenteDesde = request.POST.get('vigenteDesde') or None
        impuesto.vigenteHasta = request.POST.get('vigenteHasta') or None
        
        # Verificar si se está activando
        nuevo_activo = request.POST.get('activo') == 'on'
        
        try:
            # Validación: Si se activa este impuesto, desactivar los demás
            if nuevo_activo and not impuesto.activo:
                Impuesto.objects.filter(activo=True).exclude(id=id).update(activo=False)
            elif nuevo_activo:
                # Si ya estaba activo y sigue activo, asegurar que no haya otros (por si acaso)
                Impuesto.objects.filter(activo=True).exclude(id=id).update(activo=False)
                
            impuesto.activo = nuevo_activo
            impuesto.save()
            messages.success(request, 'Impuesto actualizado exitosamente.')
            return redirect('usuarios:lista_impuestos')
        except Exception as e:
            messages.error(request, f'Error al actualizar impuesto: {str(e)}')
            
    return render(request, 'usuarios/impuestos/editar.html', {
        'impuesto': impuesto,
        'titulo': 'Editar Impuesto'
    })

@login_required
def eliminar_impuesto(request, id):
    impuesto = get_object_or_404(Impuesto, id=id)
    try:
        impuesto.delete()
        messages.success(request, 'Impuesto eliminado exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al eliminar impuesto: {str(e)}')
        
    return redirect('usuarios:lista_impuestos')
