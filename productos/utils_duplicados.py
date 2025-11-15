"""
Utilidades para detección de productos duplicados y mapeo de códigos alternativos
"""
from difflib import SequenceMatcher
from django.db.models import Q
from productos.models import Producto, CodigoAlternativo


def similitud_texto(texto1, texto2):
    """
    Calcula la similitud entre dos textos usando SequenceMatcher
    Retorna un valor entre 0 y 1 (1 = idéntico)
    """
    if not texto1 or not texto2:
        return 0.0
    
    return SequenceMatcher(None, texto1.lower().strip(), texto2.lower().strip()).ratio()


def extraer_palabras_clave(nombre):
    """
    Extrae palabras clave relevantes de un nombre de producto
    Ignora palabras comunes y se enfoca en sustantivos principales
    """
    # Palabras a ignorar
    palabras_ignorar = {
        'mg', 'ml', 'gr', 'kg', 'tab', 'cap', 'amp', 'fr', 'sobre',
        'caja', 'tabletas', 'capsulas', 'ampolla', 'frasco', 'sobres',
        'de', 'del', 'la', 'el', 'los', 'las', 'con', 'sin', 'para',
        'x', 'por', 'en'
    }
    
    palabras = nombre.lower().split()
    palabras_clave = [p for p in palabras if p not in palabras_ignorar and len(p) > 2]
    
    return palabras_clave


def buscar_producto_por_codigo_exacto(codigo):
    """
    Busca un producto por código exacto (principal, auxiliar o alternativo)
    Retorna el producto si lo encuentra, None si no
    """
    # Buscar por código principal
    try:
        return Producto.objects.get(codigo_principal=codigo, activo=True)
    except Producto.DoesNotExist:
        pass
    
    # Buscar por código auxiliar
    try:
        return Producto.objects.get(codigo_auxiliar=codigo, activo=True)
    except Producto.DoesNotExist:
        pass
    
    # Buscar en códigos alternativos
    try:
        codigo_alt = CodigoAlternativo.objects.get(codigo=codigo, activo=True)
        return codigo_alt.producto if codigo_alt.producto.activo else None
    except CodigoAlternativo.DoesNotExist:
        pass
    
    return None


def buscar_productos_similares(nombre, codigo=None, umbral_similitud=0.75, max_resultados=5):
    """
    Busca productos similares por nombre y opcionalmente por código
    
    Args:
        nombre: Nombre del producto a buscar
        codigo: Código del producto (opcional)
        umbral_similitud: Valor mínimo de similitud (0.0 a 1.0)
        max_resultados: Cantidad máxima de resultados a retornar
        
    Returns:
        Lista de diccionarios con productos similares y su score de similitud
    """
    # Primero buscar por código exacto
    if codigo:
        producto_exacto = buscar_producto_por_codigo_exacto(codigo)
        if producto_exacto:
            return [{
                'producto': producto_exacto,
                'similitud_nombre': 100.0,
                'similitud_codigo': 100.0,
                'score_total': 100.0,
                'tipo_coincidencia': 'exacto',
                'mensaje': '✓ Código ya existe en el sistema'
            }]
    
    # Normalizar nombre de búsqueda
    nombre_busqueda = nombre.lower().strip()
    palabras_busqueda = extraer_palabras_clave(nombre)
    
    # OPTIMIZACIÓN: Construir query SQL con LIKE para filtrar candidatos
    # En lugar de cargar TODOS los productos, solo cargamos los que contienen
    # alguna palabra clave relevante
    q_objects = Q()
    
    for palabra in palabras_busqueda:
        if len(palabra) >= 3:  # Solo palabras significativas (mínimo 3 caracteres)
            q_objects |= Q(nombre__icontains=palabra)
    
    # Si se proporcionó código, agregar búsqueda por código
    if codigo and len(codigo) >= 3:
        q_objects |= Q(codigo_principal__icontains=codigo)
        q_objects |= Q(codigo_auxiliar__icontains=codigo)
    
    # Si no hay palabras clave válidas, retornar vacío
    if not q_objects:
        return []
    
    # Ejecutar query optimizada - SQL: WHERE nombre LIKE '%palabra1%' OR nombre LIKE '%palabra2%'
    # Esto trae solo candidatos potenciales en lugar de toda la tabla
    productos_activos = Producto.objects.filter(
        q_objects,
        activo=True
    ).only(
        'id', 'nombre', 'codigo_principal', 'codigo_auxiliar', 'stock', 'precio_venta'
    )[:100]  # Limitar a 100 candidatos máximo para seguridad
    
    similitudes = []
    
    for producto in productos_activos:
        producto_nombre = producto.nombre.lower()
        
        # 1. Similitud por nombre completo (difflib)
        ratio_nombre = similitud_texto(nombre, producto.nombre)
        
        # 2. Similitud por palabras clave comunes
        palabras_producto = extraer_palabras_clave(producto.nombre)
        palabras_comunes = set(palabras_busqueda) & set(palabras_producto)
        ratio_palabras = len(palabras_comunes) / max(len(palabras_busqueda), 1) if palabras_busqueda else 0.0
        
        # 3. NUEVO: Búsqueda por subcadenas (para casos como "finalin" vs "FINALIN FORTE")
        # Si alguna palabra de búsqueda está contenida en el nombre del producto
        ratio_subcadena = 0.0
        for palabra_busq in palabras_busqueda:
            if len(palabra_busq) >= 3:  # Reducido a 3+ caracteres para más flexibilidad
                if palabra_busq in producto_nombre:
                    # Coincidencia exacta de subcadena
                    ratio_subcadena = max(ratio_subcadena, 0.95)
                elif any(palabra_busq in palabra_prod for palabra_prod in palabras_producto):
                    # Coincidencia parcial
                    ratio_subcadena = max(ratio_subcadena, 0.85)
                elif any(palabra_prod in palabra_busq for palabra_prod in palabras_producto if len(palabra_prod) >= 3):
                    # Inverso: palabra del producto contenida en palabra de búsqueda
                    ratio_subcadena = max(ratio_subcadena, 0.75)
        
        # 4. NUEVO: Coincidencia al inicio del nombre (boost para marcas)
        ratio_inicio = 0.0
        if palabras_busqueda:
            primera_palabra = palabras_busqueda[0]
            if len(primera_palabra) >= 3:  # Reducido a 3+ caracteres
                if producto_nombre.startswith(primera_palabra):
                    ratio_inicio = 1.0
                elif any(p.startswith(primera_palabra) for p in palabras_producto):
                    ratio_inicio = 0.85
        
        # 5. Similitud por código (si se proporcionó)
        ratio_codigo = 0.0
        if codigo:
            if producto.codigo_principal:
                ratio_codigo = max(ratio_codigo, similitud_texto(codigo, producto.codigo_principal))
            if producto.codigo_auxiliar:
                ratio_codigo = max(ratio_codigo, similitud_texto(codigo, producto.codigo_auxiliar))
        
        # Score combinado optimizado:
        # - 25% similitud de nombre completo (difflib)
        # - 20% palabras clave comunes
        # - 35% coincidencia de subcadena (AUMENTADO - es el más importante para nombres parciales)
        # - 15% coincidencia al inicio (importante para marcas)
        # - 5% similitud de código
        score_final = (
            (ratio_nombre * 0.25) + 
            (ratio_palabras * 0.20) + 
            (ratio_subcadena * 0.35) + 
            (ratio_inicio * 0.15) + 
            (ratio_codigo * 0.05)
        )
        
        # Reducir el umbral efectivo si hay buena coincidencia de subcadena o inicio
        umbral_efectivo = umbral_similitud
        # Reducir el umbral efectivo si hay buena coincidencia de subcadena o inicio
        umbral_efectivo = umbral_similitud
        if ratio_subcadena >= 0.85 or ratio_inicio >= 0.85:
            umbral_efectivo = max(0.45, umbral_similitud - 0.25)  # Reducir umbral en 25%
        
        if score_final >= umbral_efectivo:
            similitudes.append({
                'producto': producto,
                'similitud_nombre': round(ratio_nombre * 100, 1),
                'similitud_codigo': round(ratio_codigo * 100, 1) if codigo else 0.0,
                'score_total': round(score_final * 100, 1),
                'tipo_coincidencia': 'similar',
                'mensaje': f'Similitud: {round(score_final * 100, 1)}%',
                # Debug info (opcional, comentar en producción)
                '_debug': {
                    'nombre': round(ratio_nombre * 100, 1),
                    'palabras': round(ratio_palabras * 100, 1),
                    'subcadena': round(ratio_subcadena * 100, 1),
                    'inicio': round(ratio_inicio * 100, 1),
                    'candidatos_sql': len(productos_activos)
                }
            })
    
    # Ordenar por score y retornar los mejores resultados
    similitudes.sort(key=lambda x: x['score_total'], reverse=True)
    return similitudes[:max_resultados]


def vincular_codigo_alternativo(producto_id, codigo, nombre_proveedor=None, id_proveedor=None):
    """
    Vincula un código alternativo a un producto existente
    
    Args:
        producto_id: ID del producto al que vincular el código
        codigo: Código alternativo a vincular
        nombre_proveedor: Nombre del producto según el proveedor (opcional)
        id_proveedor: ID del proveedor (opcional)
        
    Returns:
        Tupla (success: bool, message: str, codigo_alternativo: CodigoAlternativo)
    """
    try:
        producto = Producto.objects.get(id=producto_id)
        
        # Verificar si el código ya existe
        if CodigoAlternativo.objects.filter(codigo=codigo).exists():
            return (False, f"El código '{codigo}' ya está registrado", None)
        
        # Crear el código alternativo
        codigo_alt = CodigoAlternativo.objects.create(
            producto=producto,
            codigo=codigo,
            nombre_proveedor=nombre_proveedor,
            id_proveedor=id_proveedor,
            activo=True
        )
        
        return (True, f"Código '{codigo}' vinculado exitosamente a {producto.nombre}", codigo_alt)
        
    except Producto.DoesNotExist:
        return (False, f"Producto con ID {producto_id} no encontrado", None)
    except Exception as e:
        return (False, f"Error al vincular código: {str(e)}", None)


def obtener_producto_con_alternativo(codigo):
    """
    Obtiene el producto usando código principal, auxiliar o alternativo
    
    Returns:
        Tupla (producto: Producto, tipo_codigo: str) o (None, None)
    """
    # Buscar por código principal
    try:
        producto = Producto.objects.get(codigo_principal=codigo, activo=True)
        return (producto, 'principal')
    except Producto.DoesNotExist:
        pass
    
    # Buscar por código auxiliar
    try:
        producto = Producto.objects.get(codigo_auxiliar=codigo, activo=True)
        return (producto, 'auxiliar')
    except Producto.DoesNotExist:
        pass
    
    # Buscar en códigos alternativos
    try:
        codigo_alt = CodigoAlternativo.objects.select_related('producto').get(
            codigo=codigo, activo=True
        )
        if codigo_alt.producto.activo:
            return (codigo_alt.producto, 'alternativo')
    except CodigoAlternativo.DoesNotExist:
        pass
    
    return (None, None)
