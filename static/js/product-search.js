/**
 * Componente de Búsqueda de Productos Offline/Online
 * Funciona automáticamente en modo online u offline
 */

class ProductSearchComponent {
    constructor(options = {}) {
        this.containerId = options.containerId || 'product-search-container';
        this.onProductSelect = options.onProductSelect || this.defaultProductSelect;
        this.placeholder = options.placeholder || 'Buscar productos...';
        this.limit = options.limit || 20;
        this.includeAgotados = options.includeAgotados !== false;
        this.showFilters = options.showFilters !== false;
        
        this.searchTimeout = null;
        this.isSearching = false;
        this.selectedIndex = -1;
        this.currentResults = [];
        
        this.init();
    }
    
    init() {
        this.createSearchInterface();
        this.attachEventListeners();
        
        // Cargar filtros si están habilitados
        if (this.showFilters) {
            this.loadFilters();
        }
        
        console.log('ProductSearchComponent inicializado');
    }
    
    createSearchInterface() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error(`Container ${this.containerId} no encontrado`);
            return;
        }
        
        container.innerHTML = `
            <div class="product-search-wrapper">
                <!-- Barra de búsqueda principal -->
                <div class="input-group mb-3">
                    <span class="input-group-text">
                        <i class="fas fa-search"></i>
                    </span>
                    <input type="text" 
                           id="product-search-input" 
                           class="form-control" 
                           placeholder="${this.placeholder}"
                           autocomplete="off">
                    <span class="input-group-text" id="search-status">
                        <i class="fas fa-circle text-muted" title="Estado de conexión"></i>
                    </span>
                </div>
                
                ${this.showFilters ? this.createFiltersHTML() : ''}
                
                <!-- Resultados de búsqueda -->
                <div id="search-results" class="search-results" style="display: none;">
                    <div class="list-group">
                        <!-- Los resultados se cargan aquí -->
                    </div>
                </div>
                
                <!-- Indicador de carga -->
                <div id="search-loading" class="text-center p-3" style="display: none;">
                    <i class="fas fa-spinner fa-spin"></i> Buscando...
                </div>
                
                <!-- Estado sin resultados -->
                <div id="no-results" class="text-center p-3 text-muted" style="display: none;">
                    <i class="fas fa-search"></i><br>
                    <small>No se encontraron productos</small>
                </div>
                
                <!-- Información del cache -->
                <div id="cache-info" class="cache-info mt-2" style="display: none;">
                    <small class="text-muted">
                        <i class="fas fa-database"></i> 
                        Búsqueda desde cache offline - <span id="cache-count">0</span> productos disponibles
                    </small>
                </div>
            </div>
        `;
    }
    
    createFiltersHTML() {
        return `
            <div class="row mb-3">
                <div class="col-md-6">
                    <select id="categoria-filter" class="form-select form-select-sm">
                        <option value="">Todas las categorías</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <select id="marca-filter" class="form-select form-select-sm">
                        <option value="">Todas las marcas</option>
                    </select>
                </div>
            </div>
        `;
    }
    
    attachEventListeners() {
        const searchInput = document.getElementById('product-search-input');
        const resultsContainer = document.getElementById('search-results');
        
        // Búsqueda con debounce
        searchInput.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.performSearch(e.target.value);
            }, 300);
        });
        
        // Navegación con teclado
        searchInput.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e);
        });
        
        // Escuchar clicks fuera para cerrar resultados
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.product-search-wrapper')) {
                this.hideResults();
            }
        });
        
        // Escuchar cambios en filtros
        if (this.showFilters) {
            const categoriaFilter = document.getElementById('categoria-filter');
            const marcaFilter = document.getElementById('marca-filter');
            
            if (categoriaFilter) {
                categoriaFilter.addEventListener('change', () => {
                    const query = searchInput.value;
                    if (query.trim()) {
                        this.performSearch(query);
                    }
                });
            }
            
            if (marcaFilter) {
                marcaFilter.addEventListener('change', () => {
                    const query = searchInput.value;
                    if (query.trim()) {
                        this.performSearch(query);
                    }
                });
            }
        }
        
        // Escuchar actualizaciones del cache
        window.addEventListener('productsCache:updated', (e) => {
            this.updateCacheInfo();
            if (this.showFilters) {
                this.loadFilters();
            }
        });
    }
    
    async performSearch(query) {
        if (!query || query.trim().length < 2) {
            this.hideResults();
            return;
        }
        
        this.showLoading();
        this.updateConnectionStatus();
        
        try {
            const options = {
                limit: this.limit,
                includeAgotados: this.includeAgotados
            };
            
            // Obtener filtros si están habilitados
            if (this.showFilters) {
                const categoriaFilter = document.getElementById('categoria-filter');
                const marcaFilter = document.getElementById('marca-filter');
                
                if (categoriaFilter && categoriaFilter.value) {
                    options.categoria = categoriaFilter.value;
                }
                if (marcaFilter && marcaFilter.value) {
                    options.marca = marcaFilter.value;
                }
            }
            
            // Usar el OfflineManager para búsqueda automática online/offline
            const result = await window.offlineManager.searchProducts(query, options);
            
            this.currentResults = result.productos || [];
            this.selectedIndex = -1;
            
            if (result.success && this.currentResults.length > 0) {
                this.displayResults(this.currentResults, result.from_cache);
            } else {
                this.showNoResults();
            }
            
        } catch (error) {
            console.error('Error en búsqueda:', error);
            this.showError('Error en la búsqueda');
        } finally {
            this.hideLoading();
        }
    }
    
    displayResults(productos, fromCache = false) {
        const resultsContainer = document.getElementById('search-results');
        const listGroup = resultsContainer.querySelector('.list-group');
        
        listGroup.innerHTML = '';
        
        productos.forEach((producto, index) => {
            const item = document.createElement('div');
            item.className = 'list-group-item list-group-item-action product-item';
            item.dataset.index = index;
            item.dataset.productId = producto.id;
            
            // Determinar clase de stock
            let stockClass = 'text-success';
            let stockIcon = 'fas fa-check-circle';
            
            if (producto.agotado) {
                stockClass = 'text-danger';
                stockIcon = 'fas fa-times-circle';
            } else if (producto.bajo_stock) {
                stockClass = 'text-warning';
                stockIcon = 'fas fa-exclamation-triangle';
            }
            
            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center">
                            <strong>${producto.codigo_principal || producto.codigo_auxiliar || 'S/C'}</strong>
                            <span class="ms-2">${producto.nombre}</span>
                            ${fromCache ? '<i class="fas fa-database text-muted ms-2" title="Desde cache offline"></i>' : ''}
                        </div>
                        <small class="text-muted">
                            ${producto.categoria?.nombre || ''} ${producto.marca?.nombre ? '• ' + producto.marca.nombre : ''}
                        </small>
                        ${producto.descripcion ? `<br><small class="text-muted">${producto.descripcion}</small>` : ''}
                    </div>
                    <div class="text-end">
                        <div class="fw-bold text-primary">$${(producto.pvp_unidad || producto.precio_venta || 0).toFixed(2)}</div>
                        <div class="small ${stockClass}">
                            <i class="${stockIcon}"></i>
                            Stock: ${producto.stock}
                        </div>
                    </div>
                </div>
            `;
            
            // Evento click
            item.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Click en producto:', producto);
                this.selectProduct(producto, index);
            });
            
            listGroup.appendChild(item);
        });
        
        this.showResults();
        this.updateCacheInfo(fromCache);
    }
    
    selectProduct(producto, index) {
        console.log('Seleccionando producto:', producto);
        this.selectedIndex = index;
        this.highlightSelectedItem();
        
        try {
            this.onProductSelect(producto);
            console.log('onProductSelect ejecutado correctamente');
        } catch (error) {
            console.error('Error en onProductSelect:', error);
        }
        
        this.hideResults();
        
        // Limpiar búsqueda
        document.getElementById('product-search-input').value = '';
    }
    
    handleKeyNavigation(e) {
        const items = document.querySelectorAll('.product-item');
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
                this.highlightSelectedItem();
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.highlightSelectedItem();
                break;
                
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && this.currentResults[this.selectedIndex]) {
                    this.selectProduct(this.currentResults[this.selectedIndex], this.selectedIndex);
                }
                break;
                
            case 'Escape':
                this.hideResults();
                e.target.blur();
                break;
        }
    }
    
    highlightSelectedItem() {
        const items = document.querySelectorAll('.product-item');
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }
    
    async loadFilters() {
        if (!window.offlineManager) return;
        
        try {
            const stats = window.offlineManager.getProductsCacheStats();
            
            if (stats.total_productos > 0) {
                // Obtener categorías y marcas del cache
                const categorias = [...new Set(window.offlineManager.cachedProducts
                    .map(p => p.categoria)
                    .filter(c => c && c.nombre)
                )].sort((a, b) => a.nombre.localeCompare(b.nombre));
                
                const marcas = [...new Set(window.offlineManager.cachedProducts
                    .map(p => p.marca)
                    .filter(m => m && m.nombre)
                )].sort((a, b) => a.nombre.localeCompare(b.nombre));
                
                // Actualizar select de categorías
                const categoriaSelect = document.getElementById('categoria-filter');
                if (categoriaSelect) {
                    categoriaSelect.innerHTML = '<option value="">Todas las categorías</option>';
                    categorias.forEach(categoria => {
                        const option = document.createElement('option');
                        option.value = categoria.id;
                        option.textContent = categoria.nombre;
                        categoriaSelect.appendChild(option);
                    });
                }
                
                // Actualizar select de marcas
                const marcaSelect = document.getElementById('marca-filter');
                if (marcaSelect) {
                    marcaSelect.innerHTML = '<option value="">Todas las marcas</option>';
                    marcas.forEach(marca => {
                        const option = document.createElement('option');
                        option.value = marca.id;
                        option.textContent = marca.nombre;
                        marcaSelect.appendChild(option);
                    });
                }
            }
            
        } catch (error) {
            console.error('Error cargando filtros:', error);
        }
    }
    
    updateConnectionStatus() {
        const statusIcon = document.getElementById('search-status');
        if (!statusIcon) return;
        
        const icon = statusIcon.querySelector('i');
        
        if (navigator.onLine) {
            icon.className = 'fas fa-circle text-success';
            icon.title = 'Online - Búsqueda en tiempo real';
        } else {
            icon.className = 'fas fa-circle text-warning';
            icon.title = 'Offline - Búsqueda desde cache';
        }
    }
    
    updateCacheInfo(fromCache = false) {
        const cacheInfo = document.getElementById('cache-info');
        const cacheCount = document.getElementById('cache-count');
        
        if (!window.offlineManager) return;
        
        const stats = window.offlineManager.getProductsCacheStats();
        
        if (fromCache || !navigator.onLine) {
            if (cacheInfo) cacheInfo.style.display = 'block';
            if (cacheCount) cacheCount.textContent = stats.total_productos;
        } else {
            if (cacheInfo) cacheInfo.style.display = 'none';
        }
    }
    
    showResults() {
        document.getElementById('search-results').style.display = 'block';
        document.getElementById('no-results').style.display = 'none';
    }
    
    hideResults() {
        document.getElementById('search-results').style.display = 'none';
        this.selectedIndex = -1;
    }
    
    showLoading() {
        document.getElementById('search-loading').style.display = 'block';
        document.getElementById('search-results').style.display = 'none';
        document.getElementById('no-results').style.display = 'none';
    }
    
    hideLoading() {
        document.getElementById('search-loading').style.display = 'none';
    }
    
    showNoResults() {
        document.getElementById('no-results').style.display = 'block';
        document.getElementById('search-results').style.display = 'none';
    }
    
    showError(message) {
        console.error(message);
        document.getElementById('no-results').innerHTML = `
            <i class="fas fa-exclamation-triangle text-warning"></i><br>
            <small>${message}</small>
        `;
        this.showNoResults();
    }
    
    defaultProductSelect(producto) {
        console.log('Producto seleccionado:', producto);
        // Implementación por defecto - puede ser sobrescrita
    }
    
    // Métodos públicos para control externo
    clearSearch() {
        document.getElementById('product-search-input').value = '';
        this.hideResults();
    }
    
    focusSearch() {
        document.getElementById('product-search-input').focus();
    }
    
    setSearchQuery(query) {
        document.getElementById('product-search-input').value = query;
        this.performSearch(query);
    }
}

// CSS para el componente
const searchComponentCSS = `
    <style>
    .product-search-wrapper {
        position: relative;
        max-width: 100%;
    }
    
    .search-results {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        z-index: 1000;
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid #dee2e6;
        border-radius: 0.375rem;
        background: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .product-item {
        cursor: pointer;
        border: none !important;
        border-bottom: 1px solid #f8f9fa !important;
    }
    
    .product-item:hover {
        background-color: #f8f9fa;
    }
    
    .product-item.active {
        background-color: #e3f2fd;
        border-color: #2196f3 !important;
    }
    
    .cache-info {
        font-size: 0.8em;
        padding: 5px 10px;
        background: #f8f9fa;
        border-radius: 0.25rem;
    }
    
    #search-status {
        min-width: 40px;
        justify-content: center;
    }
    </style>
`;

// Inyectar CSS
if (!document.getElementById('product-search-css')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'product-search-css';
    styleElement.textContent = searchComponentCSS.replace(/<\/?style>/g, '');
    document.head.appendChild(styleElement);
}

// Exportar para uso global
window.ProductSearchComponent = ProductSearchComponent;