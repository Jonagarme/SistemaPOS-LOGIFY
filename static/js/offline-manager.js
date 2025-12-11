/**
 * Sistema POS Offline Manager usando Dexie.js
 * Maneja conectividad, cache, y sincronización de datos
 */

class OfflineManager {
    constructor() {
        this.isOnline = navigator.onLine;
        this.offlineSales = [];
        this.cachedProducts = [];
        this.cachedClients = [];
        this.syncInProgress = false;
        this.productsCacheVersion = '2.0'; // Updated version for Dexie
        this.lastProductsCacheUpdate = null;
        this.dbName = 'SistemaPOSOfflineDB';
        
        // Inicializar Dexie
        this.db = new Dexie(this.dbName);
        this.initDB();
        
        this.init();
    }
    
    initDB() {
        // Definir esquema de la base de datos
        this.db.version(1).stores({
            offlineSales: 'id, timestamp, status, synced_at',
            cachedProducts: 'id, codigo_principal, codigo_auxiliar, nombre, [categoria.id], [marca.id], searchable_text',
            cachedClients: 'id, cedula, nombre, searchable_text',
            appState: 'key' // Para guardar metadatos como lastProductsCacheUpdate
        });
        
    }
    
    async init() {
        
        // Configurar Service Worker
        await this.registerServiceWorker();
        
        // Configurar event listeners
        this.setupEventListeners();
        
        // Cargar datos iniciales
        await this.loadAppState();
        await this.loadOfflineSales();
        await this.loadProductsCache();
        await this.loadClientsCache();

        // Sincronización inicial (Inicio de Turno)
        if (this.isOnline) {
            try {
                await this.syncOfflineData();
                await this.updateProductsCache();
                await this.updateClientsCache();
            } catch (error) {
                console.warn('Error en sincronización inicial:', error);
                console.error('Detalles del error:', error.message, error.stack);
            }
        } else {
        }
        
        // Actualizar UI inicial
        this.updateOnlineStatus();
        
        // Auto-sync cada 60 segundos
        this.startAutoSync();
        
    }
    
    async loadAppState() {
        try {
            const lastUpdateState = await this.db.appState.get('lastProductsCacheUpdate');
            if (lastUpdateState) {
                this.lastProductsCacheUpdate = lastUpdateState.value;
            }
        } catch (error) {
            console.error('Error cargando estado de la app:', error);
        }
    }
    
    async saveAppState(key, value) {
        try {
            await this.db.appState.put({ key, value });
        } catch (error) {
            console.error('Error guardando estado de la app:', error);
        }
    }
    
    // Registrar Service Worker
    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/static/js/sw.js');
                
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            this.showUpdateNotification();
                        }
                    });
                });
                
            } catch (error) {
                console.error('Error registrando Service Worker:', error);
            }
        }
    }
    
    // Configurar event listeners
    setupEventListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateOnlineStatus();
            this.syncOfflineData();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateOnlineStatus();
        });
        
        this.interceptSaleForms();
        this.setupManualSyncButton();
    }
    
    updateOnlineStatus() {
        let indicator = document.getElementById('connection-indicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'connection-indicator';
            indicator.style.cssText = `
                position: fixed;
                top: 70px;
                right: 20px;
                padding: 6px 12px;
                border-radius: 15px;
                font-size: 11px;
                font-weight: bold;
                z-index: 9999;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                backdrop-filter: blur(5px);
                border: 1px solid rgba(255,255,255,0.2);
            `;
            document.body.appendChild(indicator);
        }
        
        if (this.isOnline) {
            indicator.innerHTML = '<i class="fas fa-wifi"></i> ONLINE';
            indicator.style.backgroundColor = 'rgba(40, 167, 69, 0.9)';
            indicator.style.color = 'white';
        } else {
            indicator.innerHTML = '<i class="fas fa-wifi-slash"></i> OFFLINE';
            indicator.style.backgroundColor = 'rgba(220, 53, 69, 0.9)';
            indicator.style.color = 'white';
        }
        
        this.updatePendingSalesCounter();
    }
    
    interceptSaleForms() {
        const saleForm = document.querySelector('form[action*="procesar-venta"]');
        if (saleForm) {
            saleForm.addEventListener('submit', (event) => {
                if (!this.isOnline) {
                    event.preventDefault();
                    this.handleOfflineSale(event.target);
                }
            });
        }
    }
    
    async handleOfflineSale(form) {
        try {
            const formData = new FormData(form);
            const saleData = {};
            
            for (let [key, value] of formData.entries()) {
                saleData[key] = value;
            }
            
            const offlineId = 'offline_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            
            const offlineSale = {
                id: offlineId,
                timestamp: Date.now(),
                data: saleData,
                status: 'pending_sync',
                attempts: 0,
                created_offline: true,
                customer_name: saleData.cliente_nombre || 'Cliente General',
                total: parseFloat(saleData.total) || 0
            };
            
            // Guardar en Dexie
            await this.db.offlineSales.add(offlineSale);
            
            // Actualizar lista local y UI
            this.offlineSales.push(offlineSale);
            this.updatePendingSalesCounter();
            
            this.showOfflineSaleConfirmation(offlineSale);
            form.reset();
            
        } catch (error) {
            console.error('Error procesando venta offline:', error);
            this.showError('Error guardando venta offline. Inténtalo de nuevo.');
        }
    }
    
    async loadOfflineSales() {
        try {
            this.offlineSales = await this.db.offlineSales
                .where('status')
                .equals('pending_sync')
                .toArray();
                
            this.updatePendingSalesCounter();
        } catch (error) {
            console.error('Error cargando ventas offline:', error);
        }
    }
    
    async syncOfflineData() {
        if (this.syncInProgress || !this.isOnline || this.offlineSales.length === 0) {
            return;
        }
        
        this.syncInProgress = true;
        this.showSyncProgress();
        
        let syncedCount = 0;
        let errorCount = 0;
        
        try {
            // Recargar para asegurar que tenemos lo último
            await this.loadOfflineSales();
            
            for (const sale of this.offlineSales) {
                try {
                    await this.syncSingleSale(sale);
                    syncedCount++;
                } catch (error) {
                    errorCount++;
                    console.error('Error sincronizando venta:', sale.id, error);
                }
            }
            
            // Recargar después de sincronizar
            await this.loadOfflineSales();
            this.showSyncResult(syncedCount, errorCount);
            
        } catch (error) {
            console.error('Error en sincronización general:', error);
            this.showError('Error durante la sincronización');
        } finally {
            this.syncInProgress = false;
            this.hideSyncProgress();
        }
    }
    
    async syncSingleSale(sale) {
        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
            
            const response = await fetch('/ventas/procesar-venta/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(sale.data)
            });
            
            if (response.ok) {
                // Actualizar en Dexie
                await this.db.offlineSales.update(sale.id, {
                    status: 'synced',
                    synced_at: Date.now()
                });
            } else {
                // Incrementar intentos
                await this.db.offlineSales.update(sale.id, {
                    attempts: (sale.attempts || 0) + 1,
                    last_attempt: Date.now()
                });
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
        } catch (error) {
            // Incrementar intentos en caso de error de red
            await this.db.offlineSales.update(sale.id, {
                attempts: (sale.attempts || 0) + 1,
                last_attempt: Date.now()
            });
            throw error;
        }
    }

    startAutoSync() {
        setInterval(() => {
            if (this.isOnline && this.offlineSales.length > 0 && !this.syncInProgress) {
                this.syncOfflineData();
            }
            
            // Actualizar cache de productos y clientes cada 30 minutos si hay conexión
            if (this.isOnline && !this.syncInProgress) {
                const now = Date.now();
                if (!this.lastProductsCacheUpdate || (now - this.lastProductsCacheUpdate) > 1800000) {
                    this.updateProductsCache();
                    this.updateClientsCache();
                }
            }
        }, 60000);
    }

    async loadProductsCache() {
        try {
            this.cachedProducts = await this.db.cachedProducts.toArray();
        } catch (error) {
            console.error('Error cargando productos desde cache:', error);
        }
    }

    async loadClientsCache() {
        try {
            this.cachedClients = await this.db.cachedClients.toArray();
        } catch (error) {
            console.error('❌ Error cargando clientes desde cache:', error);
            console.error('Detalles:', error.message, error.stack);
        }
    }
    
    async updateProductsCache() {
        if (!this.isOnline) return;
        
        try {
            const timestamp = Date.now();
            const response = await fetch(`/productos/api/cache/?timestamp=${timestamp}`);
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            if (data.success && data.productos) {
                await this.db.transaction('rw', this.db.cachedProducts, this.db.appState, async () => {
                    await this.db.cachedProducts.clear();
                    
                    const productosConTimestamp = data.productos.map(producto => ({
                        ...producto,
                        cache_timestamp: Date.now(),
                        cache_metadata: data.metadata
                    }));
                    
                    await this.db.cachedProducts.bulkAdd(productosConTimestamp);
                    await this.db.appState.put({ key: 'lastProductsCacheUpdate', value: timestamp });
                });
                
                this.cachedProducts = data.productos;
                this.lastProductsCacheUpdate = timestamp;
                
                this.showToast(`Productos sincronizados: ${data.productos.length}`, 'info');
                
                window.dispatchEvent(new CustomEvent('productsCache:updated', {
                    detail: { products: this.cachedProducts, metadata: data.metadata }
                }));
            }
            
        } catch (error) {
            console.error('Error actualizando cache de productos:', error);
        }
    }

    async updateClientsCache() {
        
        if (!this.isOnline) {
            console.log('⚠️ Sin conexión - no se pueden actualizar clientes');
            return;
        }
        
        try {
            const response = await fetch('/clientes/api/cache/');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.clientes && data.clientes.length > 0) {
                
                await this.db.transaction('rw', this.db.cachedClients, async () => {
                    await this.db.cachedClients.clear();
                    await this.db.cachedClients.bulkAdd(data.clientes);
                });
                
                this.cachedClients = data.clientes;
                this.showToast(`Clientes sincronizados: ${data.clientes.length}`, 'success');
            } else {
                console.warn('⚠️ No hay clientes para guardar en cache');
            }
            
        } catch (error) {
            console.error('❌ Error actualizando cache de clientes:', error);
            console.error('Detalles del error:', error.message, error.stack);
        }
    }

    async searchProductsOffline(query, options = {}) {
        const { categoria, marca, limit = 20, includeAgotados = true } = options;
        
        try {
            if (this.cachedProducts.length > 0) {
                let resultados = this.cachedProducts;
                
                if (query && query.trim()) {
                    const queryLower = query.toLowerCase().trim();
                    resultados = resultados.filter(producto => 
                        (producto.searchable_text && producto.searchable_text.includes(queryLower)) ||
                        (producto.nombre && producto.nombre.toLowerCase().includes(queryLower)) ||
                        (producto.codigo_principal && producto.codigo_principal.toLowerCase().includes(queryLower)) ||
                        (producto.codigo_auxiliar && producto.codigo_auxiliar.toLowerCase().includes(queryLower))
                    );
                }
                
                if (categoria) resultados = resultados.filter(p => p.categoria && p.categoria.id == categoria);
                if (marca) resultados = resultados.filter(p => p.marca && p.marca.id == marca);
                if (!includeAgotados) resultados = resultados.filter(p => !p.agotado);
                
                const total = resultados.length;
                resultados = resultados.slice(0, limit);
                
                return {
                    success: true,
                    productos: resultados.map(p => ({ ...p, from_cache: true })),
                    count: total,
                    from_cache: true
                };
            } 
            
            let collection = this.db.cachedProducts.toCollection();
            
            if (query && query.trim()) {
                const queryLower = query.toLowerCase().trim();
                collection = this.db.cachedProducts
                    .filter(p => 
                        (p.nombre && p.nombre.toLowerCase().includes(queryLower)) ||
                        (p.codigo_principal && p.codigo_principal.toLowerCase().includes(queryLower))
                    );
            }
            
            if (categoria) collection = collection.filter(p => p.categoria && p.categoria.id == categoria);
            if (marca) collection = collection.filter(p => p.marca && p.marca.id == marca);
            if (!includeAgotados) collection = collection.filter(p => !p.agotado);
            
            const resultados = await collection.limit(limit).toArray();
            
            return {
                success: true,
                productos: resultados.map(p => ({ ...p, from_cache: true })),
                count: resultados.length,
                from_cache: true
            };
            
        } catch (error) {
            console.error('Error en búsqueda offline:', error);
            return { success: false, productos: [], error: error.message };
        }
    }

    async searchClientsOffline(query) {
        try {
            if (!query || !query.trim()) return { success: true, clientes: [] };
            
            const queryLower = query.toLowerCase().trim();
            let resultados = [];
            
            if (this.cachedClients && this.cachedClients.length > 0) {
                resultados = this.cachedClients.filter(cliente => 
                    (cliente.searchable_text && cliente.searchable_text.includes(queryLower)) ||
                    (cliente.nombre && cliente.nombre.toLowerCase().includes(queryLower)) ||
                    (cliente.cedula && cliente.cedula.includes(queryLower))
                );
            } else {
                resultados = await this.db.cachedClients
                    .filter(cliente => 
                        (cliente.searchable_text && cliente.searchable_text.includes(queryLower)) ||
                        (cliente.nombre && cliente.nombre.toLowerCase().includes(queryLower)) ||
                        (cliente.cedula && cliente.cedula.includes(queryLower))
                    )
                    .limit(10)
                    .toArray();
            }
            
            return {
                success: true,
                clientes: resultados.slice(0, 10).map(c => ({
                    id: c.id,
                    cedula_ruc: c.cedula,
                    nombre: c.nombre,
                    documento: c.cedula,
                    telefono: c.telefono,
                    from_cache: true
                }))
            };
            
        } catch (error) {
            console.error('Error buscando clientes offline:', error);
            return { success: false, clientes: [], error: error.message };
        }
    }

    async searchClients(query) {
        if (this.isOnline) {
            try {
                const response = await fetch(`/clientes/buscar/?search=${encodeURIComponent(query)}`);
                if (response.ok) {
                    const data = await response.json();
                    if (!data.modo_offline) {
                        return { success: true, clientes: data.clientes, from_cache: false };
                    }
                }
            } catch (error) {
                console.log('Error buscando clientes online, intentando offline...');
            }
        }
        
        return await this.searchClientsOffline(query);
    }

    async getProductFromCache(productId) {
        try {
            const producto = await this.db.cachedProducts.get(parseInt(productId));
            const finalProduct = producto || await this.db.cachedProducts.get(productId);
            
            if (finalProduct) {
                return { success: true, producto: { ...finalProduct, from_cache: true } };
            }
            return { success: false, error: 'Producto no encontrado en cache' };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    async searchProducts(query, options = {}) {
        if (this.isOnline) {
            try {
                const params = new URLSearchParams({
                    q: query || '',
                    limite: options.limit || 20
                });
                
                if (options.categoria) params.append('categoria', options.categoria);
                if (options.marca) params.append('marca', options.marca);
                
                const response = await fetch(`/productos/api/buscar/?${params}`);
                
                if (response.ok) {
                    const data = await response.json();
                    return { ...data, from_cache: false };
                }
            } catch (error) {
                console.log('Error en búsqueda online, usando cache offline');
            }
        }
        
        console.log('Usando búsqueda offline desde cache (Dexie)');
        return await this.searchProductsOffline(query, options);
    }

    updatePendingSalesCounter() {
        const counter = document.getElementById('offline-counter');
        const count = this.offlineSales.length;
        
        if (count > 0) {
            if (counter) {
                counter.textContent = count;
                counter.style.display = 'block';
            } else {
                // Crear badge si no existe en el navbar (esto depende de tu HTML)
                // Aquí asumimos que hay un contenedor o lo agregamos al indicador
                const indicator = document.getElementById('connection-indicator');
                if (indicator) {
                    let badge = indicator.querySelector('.badge');
                    if (!badge) {
                        badge = document.createElement('span');
                        badge.className = 'badge bg-warning text-dark ms-2';
                        badge.style.borderRadius = '50%';
                        indicator.appendChild(badge);
                    }
                    badge.textContent = count;
                    badge.title = `${count} ventas pendientes de sincronizar`;
                }
            }
        } else {
            if (counter) counter.style.display = 'none';
            const indicator = document.getElementById('connection-indicator');
            if (indicator) {
                const badge = indicator.querySelector('.badge');
                if (badge) badge.remove();
            }
        }
    }
    
    showOfflineSaleConfirmation(sale) {
        this.showToast(`Venta guardada offline. Se sincronizará cuando haya conexión.`, 'warning');
    }
    
    showSyncProgress() {
        this.showToast('Sincronizando ventas pendientes...', 'info');
    }
    
    hideSyncProgress() {
        // Opcional: ocultar toast
    }
    
    showSyncResult(synced, errors) {
        if (synced > 0) {
            this.showToast(`${synced} ventas sincronizadas correctamente`, 'success');
        }
        if (errors > 0) {
            this.showToast(`${errors} ventas no pudieron sincronizarse`, 'error');
        }
    }
    
    showToast(message, type = 'info') {
        
        // Si existe una función global de notificaciones, usarla
        if (typeof showNotification === 'function') {
            showNotification(message, type);
            return;
        }
        
        // Fallback: crear elemento flotante
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} position-fixed`;
        toast.style.cssText = 'bottom: 20px; right: 20px; z-index: 10000; min-width: 250px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); animation: slideIn 0.3s ease-out;';
        toast.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <span>${message}</span>
                <button type="button" class="btn-close small" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    showError(message) {
        this.showToast(message, 'error');
    }
    
    setupManualSyncButton() {
        let syncButton = document.getElementById('manual-sync-btn');
        
        if (!syncButton && this.offlineSales.length > 0) {
            syncButton = document.createElement('button');
            syncButton.id = 'manual-sync-btn';
            syncButton.innerHTML = '<i class="fas fa-sync"></i> Sincronizar';
            syncButton.className = 'btn btn-primary btn-sm';
            syncButton.style.cssText = `
                position: fixed;
                top: 110px;
                left: 20px;
                z-index: 9998;
                font-size: 10px;
                padding: 4px 8px;
                border-radius: 12px;
                backdrop-filter: blur(5px);
                border: 1px solid rgba(255,255,255,0.2);
            `;
            
            syncButton.addEventListener('click', () => {
                if (this.isOnline) {
                    this.syncOfflineData();
                } else {
                    this.showError('Sin conexión a internet');
                }
            });
            document.body.appendChild(syncButton);
        } else if (syncButton && this.offlineSales.length === 0) {
            syncButton.remove();
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.offlineManager = new OfflineManager();
});