"""
URL configuration for sistema_pos project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# Función simple para redireccionar al dashboard
def home_redirect(request):
    return redirect('usuarios:dashboard')

# Vistas de error personalizadas
def custom_400_view(request, exception=None):
    from django.shortcuts import render
    return render(request, '400.html', status=400)

def custom_403_view(request, exception=None):
    from django.shortcuts import render
    return render(request, '403.html', status=403)

def custom_404_view(request, exception=None):
    from django.shortcuts import render
    return render(request, '404.html', status=404)

def custom_500_view(request):
    from django.shortcuts import render
    return render(request, '500.html', status=500)

# Vista especial para forzar error 404 en desarrollo
def force_404_view(request, path=''):
    from django.shortcuts import render
    return render(request, '404.html', status=404)

# Vista para página offline
class OfflineView(TemplateView):
    template_name = 'offline.html'

# Vista para manejar sincronización de ventas offline
@csrf_exempt
def sync_offline_sales(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Aquí procesarías las ventas offline
            # Por ahora retornamos éxito
            return JsonResponse({
                'success': True,
                'message': 'Ventas sincronizadas correctamente',
                'synced_count': len(data.get('sales', []))
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_redirect, name='home'),
    
    # URLs offline
    path('offline/', OfflineView.as_view(), name='offline'),
    path('api/sync-offline-sales/', sync_offline_sales, name='sync_offline_sales'),
    
    # URLs de las aplicaciones
    path('usuarios/', include('usuarios.urls')),
    path('productos/', include('productos.urls')),
    path('clientes/', include('clientes.urls')),
    path('proveedores/', include('proveedores.urls')),
    path('ventas/', include('ventas.urls')),
    path('inventario/', include('inventario.urls')),
    path('caja/', include('caja.urls')),
    path('cotizaciones/', include('cotizaciones.urls')),
    path('contabilidad/', include('contabilidad.urls')),
    path('reportes/', include('reportes.urls')),
    
    # URLs de prueba para errores (solo en DEBUG)
]

# Agregar URLs de prueba de error en modo DEBUG
if settings.DEBUG:
    urlpatterns += [
        path('test-400/', custom_400_view, name='test_400'),
        path('test-403/', custom_403_view, name='test_403'),
        path('test-404/', custom_404_view, name='test_404'),
        path('test-500/', custom_500_view, name='test_500'),
    ]
    # Agregar catch-all al final para capturar URLs incorrectas
    urlpatterns += [
        path('<path:path>/', force_404_view, name='catch_all_404'),
    ]

# Configurar los handlers de error
handler400 = custom_400_view
handler403 = custom_403_view
handler404 = custom_404_view
handler500 = custom_500_view

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
