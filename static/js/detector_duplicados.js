/**
 * Sistema de Detección de Productos Duplicados
 * Para uso en módulo de ingreso de facturas
 */

class DetectorDuplicados {
    constructor() {
        this.productoActual = null;
        this.productosSimilares = [];
        this.callbackConfirmacion = null;
        this.umbralSimilitud = 0.75; // 75% de similitud mínima
    }

    /**
     * Verifica si un producto de la factura ya existe
     * @param {Object} productoFactura - Datos del producto de la factura
     * @param {Function} callback - Función a ejecutar después de la decisión
     */
    async verificarProducto(productoFactura, callback) {
        this.productoActual = productoFactura;
        this.callbackConfirmacion = callback;

        try {
            // Primero buscar por código exacto
            if (productoFactura.codigo) {
                const productoExacto = await this.buscarPorCodigoExacto(productoFactura.codigo);
                if (productoExacto) {
                    // Código ya existe, usar ese producto directamente
                    if (callback) callback('usar_existente', productoExacto);
                    return;
                }
            }

            // Buscar productos similares
            const similares = await this.buscarProductosSimilares(
                productoFactura.nombre,
                productoFactura.codigo
            );

            if (similares.length > 0) {
                // Hay productos similares, mostrar modal
                this.productosSimilares = similares;
                this.mostrarModalDuplicados();
            } else {
                // No hay similares, crear nuevo
                if (callback) callback('crear_nuevo', null);
            }

        } catch (error) {
            console.error('Error al verificar producto:', error);
            // En caso de error, permitir crear nuevo
            if (callback) callback('crear_nuevo', null);
        }
    }

    /**
     * Busca un producto por código exacto
     */
    async buscarPorCodigoExacto(codigo) {
        try {
            const response = await fetch(`/productos/api/duplicados/codigo/${encodeURIComponent(codigo)}/`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();
            
            if (data.success) {
                return data.producto;
            }
            return null;
            
        } catch (error) {
            console.error('Error buscando por código:', error);
            return null;
        }
    }

    /**
     * Busca productos similares por nombre y código
     */
    async buscarProductosSimilares(nombre, codigo = null) {
        try {
            const response = await fetch('/productos/api/duplicados/buscar/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({
                    nombre: nombre,
                    codigo: codigo,
                    umbral: this.umbralSimilitud
                })
            });

            const data = await response.json();
            
            if (data.success) {
                return data.productos || [];
            }
            return [];
            
        } catch (error) {
            console.error('Error buscando similares:', error);
            return [];
        }
    }

    /**
     * Muestra el modal con los productos similares
     */
    mostrarModalDuplicados() {
        // Rellenar datos del producto de la factura
        $('#factura-codigo').text(this.productoActual.codigo || 'N/A');
        $('#factura-nombre').text(this.productoActual.nombre);
        $('#factura-cantidad').text(this.productoActual.cantidad);
        $('#factura-precio').text('$' + parseFloat(this.productoActual.precio).toFixed(2));

        // Limpiar opciones anteriores (excepto "crear nuevo")
        const select = $('#select-producto-destino');
        select.find('option[value!="nuevo"]').remove();

        // Agregar productos similares al select
        this.productosSimilares.forEach(producto => {
            const similitudClass = producto.score_total >= 90 ? 'producto-similitud-alta' :
                                  producto.score_total >= 80 ? 'producto-similitud-media' :
                                  'producto-similitud-baja';
            
            const option = $('<option></option>')
                .val(producto.id)
                .data('producto', producto)
                .data('accion', 'vincular')
                .addClass(similitudClass)
                .html(`
                    📦 ${producto.nombre}
                    <br>&nbsp;&nbsp;&nbsp;Stock: ${producto.stock} | 
                    Precio: $${producto.precio.toFixed(2)} | 
                    Similitud: ${producto.score_total.toFixed(1)}%
                `);
            
            select.append(option);
        });

        // Seleccionar el primer similar (más parecido)
        if (this.productosSimilares.length > 0) {
            select.val(this.productosSimilares[0].id);
            this.actualizarDetallesSeleccionado();
        }

        // Mostrar el modal
        $('#modalProductosDuplicados').modal('show');
    }

    /**
     * Actualiza los detalles del producto seleccionado
     */
    actualizarDetallesSeleccionado() {
        const select = $('#select-producto-destino');
        const valorSeleccionado = select.val();
        const detallesDiv = $('#detalles-producto-seleccionado');

        if (valorSeleccionado === 'nuevo') {
            detallesDiv.hide();
        } else {
            const productoSeleccionado = select.find('option:selected').data('producto');
            if (productoSeleccionado) {
                $('#detalle-stock').text(productoSeleccionado.stock + ' unidades');
                $('#detalle-precio').text('$' + productoSeleccionado.precio.toFixed(2));
                $('#detalle-similitud').text(productoSeleccionado.score_total.toFixed(1) + '%');
                detallesDiv.show();
            }
        }
    }

    /**
     * Confirma la selección del usuario
     */
    async confirmarSeleccion() {
        const select = $('#select-producto-destino');
        const valorSeleccionado = select.val();
        const recordarMapeo = $('#check-recordar-mapeo').is(':checked');

        $('#modalProductosDuplicados').modal('hide');

        if (valorSeleccionado === 'nuevo') {
            // Crear producto nuevo
            if (this.callbackConfirmacion) {
                this.callbackConfirmacion('crear_nuevo', null);
            }
        } else {
            // Usar producto existente
            const productoSeleccionado = select.find('option:selected').data('producto');
            
            if (recordarMapeo && this.productoActual.codigo) {
                // Vincular el código alternativo
                await this.vincularCodigoAlternativo(
                    productoSeleccionado.id,
                    this.productoActual.codigo,
                    this.productoActual.nombre
                );
            }

            if (this.callbackConfirmacion) {
                this.callbackConfirmacion('usar_existente', productoSeleccionado);
            }
        }
    }

    /**
     * Vincula un código alternativo al producto
     */
    async vincularCodigoAlternativo(productoId, codigo, nombreProveedor) {
        try {
            const response = await fetch('/productos/api/duplicados/vincular/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({
                    producto_id: productoId,
                    codigo: codigo,
                    nombre_proveedor: nombreProveedor
                })
            });

            const data = await response.json();
            
            if (data.success) {
                return true;
            } else {
                console.warn('⚠ No se pudo vincular:', data.error);
                return false;
            }
            
        } catch (error) {
            console.error('Error vinculando código alternativo:', error);
            return false;
        }
    }

    /**
     * Obtiene el CSRF token de las cookies
     */
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Inicializar el detector cuando el documento esté listo
let detectorDuplicados;

$(document).ready(function() {
    detectorDuplicados = new DetectorDuplicados();

    // Event listener para el cambio de selección en el modal
    $('#select-producto-destino').on('change', function() {
        detectorDuplicados.actualizarDetallesSeleccionado();
    });

    // Event listener para el botón de confirmar
    $('#btn-confirmar-seleccion').on('click', function() {
        detectorDuplicados.confirmarSeleccion();
    });
});
