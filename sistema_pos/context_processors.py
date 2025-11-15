def caja_context(request):
    """
    Context processor para agregar información de la caja en todos los templates
    """
    context = {
        'caja_abierta': None,
    }
    
    if request.user.is_authenticated:
        try:
            from caja.models import CierreCaja
            # Usar la función centralizada para obtener caja abierta
            context['caja_abierta'] = CierreCaja.obtener_caja_abierta()
            
        except Exception as e:
            # Log del error para debugging
            print(f"Error en context_processor caja: {e}")
            # En caso de error, mantener caja_abierta como None
            pass
    
    return context

def configuracion_empresa_context(request):
    """
    Context processor para agregar configuración de empresa en todos los templates
    Incluye el tipo de menú para controlar la navegación (por usuario)
    """
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
                try:
                    usuario = UsuarioSistema.objects.get(pk=request.user.usuario_sistema_id)
                    context['tipo_menu'] = usuario.tipo_menu or 'horizontal'
                except UsuarioSistema.DoesNotExist:
                    pass
            
    except Exception as e:
        # Log del error para debugging
        print(f"Error en context_processor configuracion_empresa: {e}")
        pass
    
    return context