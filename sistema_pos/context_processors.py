def caja_context(request):
    """
    Context processor para agregar información de la caja en todos los templates
    Con soporte para modo offline
    """
    context = {
        'caja_abierta': None,
    }
    
    try:
        # Verificar autenticación sin hacer consultas a BD
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                from caja.models import CierreCaja
                from django.db import OperationalError
                
                # Usar la función centralizada para obtener caja abierta
                context['caja_abierta'] = CierreCaja.obtener_caja_abierta()
                
            except OperationalError:
                # Modo offline - usar caja desde sesión si existe
                if 'caja_offline' in request.session:
                    context['caja_abierta'] = request.session['caja_offline']
                else:
                    # Crear caja offline por defecto
                    context['caja_abierta'] = {
                        'idCaja': 1,
                        'nombre': 'Caja Offline',
                        'montoInicial': 0,
                        'modo_offline': True
                    }
                    request.session['caja_offline'] = context['caja_abierta']
            except Exception as e:
                # Otros errores
                print(f"Error en context_processor caja: {e}")
                pass
    except:
        # Error al verificar autenticación (modo offline extremo)
        pass
    
    return context

def configuracion_empresa_context(request):
    """
    Context processor para agregar configuración de empresa en todos los templates
    Incluye el tipo de menú para controlar la navegación (por usuario)
    """
    from django.db import OperationalError
    
    context = {
        'tipo_menu': 'horizontal',  # Valor por defecto
        'empresa_config': None,
    }
    
    try:
        from usuarios.models import ConfiguracionEmpresa
        empresa_config = ConfiguracionEmpresa.obtener_configuracion()
        
        if empresa_config:
            context['empresa_config'] = empresa_config
        
        # Obtener tipo de menú del usuario autenticado
        if request.user.is_authenticated:
            if hasattr(request.user, 'usuario_sistema_id'):
                from usuarios.models import UsuarioSistema
                from django.db import OperationalError
                try:
                    usuario = UsuarioSistema.objects.get(pk=request.user.usuario_sistema_id)
                    context['tipo_menu'] = usuario.tipo_menu or 'horizontal'
                except (UsuarioSistema.DoesNotExist, OperationalError):
                    # Modo offline o usuario no existe
                    pass
            
    except Exception as e:
        # Log del error para debugging
        print(f"Error en context_processor configuracion_empresa: {e}")
        pass
    
    return context