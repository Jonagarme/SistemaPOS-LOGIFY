/**
 * Sistema POS Offline Manager
 * Maneja conectividad, cache, y sincronización de datos
 */

class OfflineManager {
    constructor() {
        this.isOnline = navigator.onLine;
        this.offlineSales = [];
        this.cachedProducts = [];
        this.syncInProgress = false;
        this.productsCacheVersion = '1.0';
        this.lastProductsCacheUpdate = null;
        this.dbName = 'SistemaPOSOffline';
        this.dbVersion = 1;
        this.db = null;
        
        this.init();
    }
    
    async init() {
        console.log('🚀 Iniciando Sistema Offline POS');
        
        // Verificar disponibilidad de APIs
        if (!this.checkBrowserSupport()) {
            console.warn('⚠️ Algunas funciones offline no están disponibles en este navegador');
        }
        
        // Configurar Service Worker
        await this.registerServiceWorker();
        
        // Configurar IndexedDB
        await this.initIndexedDB();
        
        // Configurar event listeners
        this.setupEventListeners();
        
        // Actualizar UI inicial
        this.updateOnlineStatus();
        
        // Cargar ventas offline pendientes
        await this.loadOfflineSales();
        
        // Cargar y actualizar cache de productos
        await this.loadProductsCache();
        
        // Solo actualizar cache si estamos online
        if (this.isOnline) {
            try {
                await this.updateProductsCache();
            } catch (error) {
                console.warn('Error inicial cargando cache de productos:', error);
                // No es crítico, continuar sin cache de productos
            }
        } else {
            console.log('📡 Iniciando en modo offline - usando cache existente');
        }
        
        // Auto-sync cada 30 segundos si hay conexión
        this.startAutoSync();
        
        console.log('✅ Sistema Offline POS iniciado correctamente');
    }
    
    // Verificar soporte del navegador
    checkBrowserSupport() {
        const features = {
            serviceWorker: 'serviceWorker' in navigator,
            indexedDB: 'indexedDB' in window,
            fetch: 'fetch' in window,
            localStorage: 'localStorage' in window
        };
        
        console.log('🔍 Soporte del navegador:', features);
        
        // Retornar true si tiene las características mínimas
        return features.indexedDB && features.fetch && features.localStorage;
    }
    
    // Registrar Service Worker
    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/static/js/sw.js');
                console.log('Service Worker registrado:', registration.scope);
                
                // Manejar actualizaciones del SW
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            this.showUpdateNotification();
                        }
                    });
                });
                
                // Recibir mensajes del Service Worker
                navigator.serviceWorker.addEventListener('message', event => {
                    this.handleServiceWorkerMessage(event.data);
                });
                
            } catch (error) {
                console.error('Error registrando Service Worker:', error);
            }
        }
    }
    
    // Configurar IndexedDB
    async initIndexedDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);
            
            request.onerror = () => {
                console.error('Error abriendo IndexedDB');
                reject(request.error);
            };
            
            request.onsuccess = () => {
                this.db = request.result;
                console.log('IndexedDB configurado correctamente');
                resolve();
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Store para ventas offline
                if (!db.objectStoreNames.contains('offlineSales')) {
                    const salesStore = db.createObjectStore('offlineSales', { keyPath: 'id' });
                    salesStore.createIndex('timestamp', 'timestamp', { unique: false });
                    salesStore.createIndex('status', 'status', { unique: false });
                }
                
                // Store para productos en cache
                if (!db.objectStoreNames.contains('cachedProducts')) {
                    const productsStore = db.createObjectStore('cachedProducts', { keyPath: 'id' });
                    productsStore.createIndex('codigo', 'codigo', { unique: false });
                    productsStore.createIndex('nombre', 'nombre', { unique: false });
                }
                
                // Store para clientes en cache
                if (!db.objectStoreNames.contains('cachedClients')) {
                    const clientsStore = db.createObjectStore('cachedClients', { keyPath: 'id' });
                    clientsStore.createIndex('cedula', 'cedula', { unique: false });
                }
                
                console.log('IndexedDB estructura creada');
            };
        });
    }
    
    // Configurar event listeners
    setupEventListeners() {
        // Detectar cambios de conectividad
        window.addEventListener('online', () => {
            console.log('🌐 Conexión restaurada');
            this.isOnline = true;
            this.updateOnlineStatus();
            this.syncOfflineData();
        });
        
        window.addEventListener('offline', () => {
            console.log('📡 Sin conexión a internet');
            this.isOnline = false;
            this.updateOnlineStatus();
        });
        
        // Interceptar formularios de venta
        this.interceptSaleForms();
        
        // Botón de sincronización manual
        this.setupManualSyncButton();
    }
    
    // Actualizar indicador visual de conectividad
    updateOnlineStatus() {
        // Crear o actualizar indicador de conexión
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
        
        // Mostrar contador de ventas pendientes
        this.updatePendingSalesCounter();
    }
    
    // Interceptar formularios de venta para modo offline
    interceptSaleForms() {
        // Buscar formularios de venta
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
    
    // Manejar venta offline
    async handleOfflineSale(form) {
        try {
            // Extraer datos del formulario
            const formData = new FormData(form);
            const saleData = {};
            
            for (let [key, value] of formData.entries()) {
                saleData[key] = value;
            }
            
            // Generar ID único para venta offline
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
            
            // Guardar en IndexedDB
            await this.saveOfflineSale(offlineSale);
            
            // Mostrar confirmación
            this.showOfflineSaleConfirmation(offlineSale);
            
            // Limpiar formulario
            form.reset();
            
        } catch (error) {
            console.error('Error procesando venta offline:', error);
            this.showError('Error guardando venta offline. Inténtalo de nuevo.');
        }
    }
    
    // Guardar venta offline en IndexedDB
    async saveOfflineSale(saleData) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['offlineSales'], 'readwrite');
            const store = transaction.objectStore('offlineSales');
            
            const request = store.add(saleData);
            
            request.onsuccess = () => {
                this.offlineSales.push(saleData);
                this.updatePendingSalesCounter();
                console.log('Venta offline guardada:', saleData.id);
                resolve();
            };
            
            request.onerror = () => {
                console.error('Error guardando venta offline');
                reject(request.error);
            };
        });
    }
    
    // Cargar ventas offline pendientes
    async loadOfflineSales() {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['offlineSales'], 'readonly');
            const store = transaction.objectStore('offlineSales');
            const index = store.index('status');
            
            const request = index.getAll('pending_sync');
            
            request.onsuccess = () => {
                this.offlineSales = request.result;
                this.updatePendingSalesCounter();
                console.log(`Cargadas ${this.offlineSales.length} ventas offline pendientes`);
                resolve();
            };
            
            request.onerror = () => {
                console.error('Error cargando ventas offline');
                reject(request.error);
            };
        });
    }
    
    // Sincronizar datos offline
    async syncOfflineData() {
        if (this.syncInProgress || !this.isOnline || this.offlineSales.length === 0) {
            return;
        }
        
        this.syncInProgress = true;
        this.showSyncProgress();
        
        let syncedCount = 0;
        let errorCount = 0;
        
        try {
            for (const sale of this.offlineSales) {
                if (sale.status === 'pending_sync') {
                    try {
                        await this.syncSingleSale(sale);
                        syncedCount++;
                    } catch (error) {
                        errorCount++;
                        console.error('Error sincronizando venta:', sale.id, error);
                    }
                }
            }
            
            // Recargar ventas pendientes
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
    
    // Sincronizar una venta individual
    async syncSingleSale(sale) {
        try {
            // Obtener CSRF token
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
                // Marcar como sincronizada en IndexedDB
                await this.updateSaleStatus(sale.id, 'synced');
                console.log('Venta sincronizada exitosamente:', sale.id);
            } else {
                // Incrementar intentos
                await this.incrementSaleAttempts(sale.id);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
        } catch (error) {
            await this.incrementSaleAttempts(sale.id);
            throw error;
        }
    }
    
    // Actualizar estado de venta en IndexedDB
    async updateSaleStatus(saleId, newStatus) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['offlineSales'], 'readwrite');
            const store = transaction.objectStore('offlineSales');
            
            const getRequest = store.get(saleId);
            
            getRequest.onsuccess = () => {
                const sale = getRequest.result;
                if (sale) {
                    sale.status = newStatus;
                    sale.synced_at = Date.now();
                    
                    const putRequest = store.put(sale);
                    putRequest.onsuccess = () => resolve();
                    putRequest.onerror = () => reject(putRequest.error);
                } else {
                    reject(new Error('Venta no encontrada'));
                }
            };
            
            getRequest.onerror = () => reject(getRequest.error);
        });
    }
    
    // Incrementar intentos de sincronización
    async incrementSaleAttempts(saleId) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['offlineSales'], 'readwrite');
            const store = transaction.objectStore('offlineSales');
            
            const getRequest = store.get(saleId);
            
            getRequest.onsuccess = () => {
                const sale = getRequest.result;
                if (sale) {
                    sale.attempts = (sale.attempts || 0) + 1;
                    sale.last_attempt = Date.now();
                    
                    const putRequest = store.put(sale);
                    putRequest.onsuccess = () => resolve();
                    putRequest.onerror = () => reject(putRequest.error);
                } else {
                    reject(new Error('Venta no encontrada'));
                }
            };
            
            getRequest.onerror = () => reject(getRequest.error);
        });
    }
    
    // Auto-sincronización
    startAutoSync() {
        setInterval(() => {
            if (this.isOnline && this.offlineSales.length > 0 && !this.syncInProgress) {
                console.log('Auto-sync: Iniciando sincronización automática');
                this.syncOfflineData();
            }
            
            // Actualizar cache de productos cada 30 minutos si hay conexión
            if (this.isOnline && !this.syncInProgress) {
                const lastUpdate = this.lastProductsCacheUpdate;
                const now = Date.now();
                if (!lastUpdate || (now - lastUpdate) > 1800000) { // 30 minutos
                    console.log('Auto-sync: Actualizando cache de productos');
                    this.updateProductsCache();
                }
            }
        }, 60000); // Cada 60 segundos
    }
    
    // =====================================
    // GESTIÓN DE CACHE DE PRODUCTOS
    // =====================================
    
    // Cargar productos desde IndexedDB
    async loadProductsCache() {
        try {
            const transaction = this.db.transaction(['cachedProducts'], 'readonly');
            const store = transaction.objectStore('cachedProducts');
            const request = store.getAll();
            
            return new Promise((resolve, reject) => {
                request.onsuccess = () => {
                    this.cachedProducts = request.result;
                    console.log(`Cargados ${this.cachedProducts.length} productos desde cache`);
                    
                    // Actualizar timestamp del último cache
                    if (this.cachedProducts.length > 0) {
                        this.lastProductsCacheUpdate = this.cachedProducts[0].cache_timestamp || Date.now();
                    }
                    
                    resolve();
                };
                
                request.onerror = () => {
                    console.error('Error cargando productos desde cache');
                    reject(request.error);
                };
            });
            
        } catch (error) {
            console.error('Error en loadProductsCache:', error);
        }
    }
    
    // Actualizar cache de productos desde el servidor
    async updateProductsCache() {
        if (!this.isOnline) {
            console.log('Sin conexión: No se puede actualizar cache de productos');
            return;
        }
        
        try {
            console.log('Actualizando cache de productos...');
            
            const timestamp = Date.now();
            const response = await fetch(`/productos/api/cache/?timestamp=${timestamp}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.productos) {
                await this.saveProductsToCache(data.productos, data.metadata);
                this.cachedProducts = data.productos;
                this.lastProductsCacheUpdate = timestamp;
                
                console.log(`Cache de productos actualizado: ${data.productos.length} productos`);
                
                // Mostrar notificación más discreta
                const now = new Date();
                const timeString = now.toLocaleTimeString();
                this.showToast(`Cache actualizado (${timeString}): ${data.productos.length} productos`, 'info');
                
                // Disparar evento personalizado para notificar a otros componentes
                window.dispatchEvent(new CustomEvent('productsCache:updated', {
                    detail: { products: this.cachedProducts, metadata: data.metadata }
                }));
            } else {
                console.warn('Respuesta de cache de productos sin datos válidos:', data);
                this.showToast('Cache de productos actualizado pero sin datos', 'warning');
            }
            
        } catch (error) {
            console.error('Error actualizando cache de productos:', error);
            
            // Mostrar error específico según el tipo
            let errorMessage = 'Error actualizando cache de productos';
            if (error.message.includes('500')) {
                errorMessage = 'Error del servidor al obtener productos';
            } else if (error.message.includes('404')) {
                errorMessage = 'Endpoint de productos no encontrado';
            } else if (!navigator.onLine) {
                errorMessage = 'Sin conexión a internet';
            }
            
            this.showToast(errorMessage, 'error');
            
            // Si hay productos en cache, usar esos
            if (this.cachedProducts.length > 0) {
                console.log(`Usando ${this.cachedProducts.length} productos desde cache existente`);
            }
        }
    }
    
    // Guardar productos en IndexedDB
    async saveProductsToCache(productos, metadata) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['cachedProducts'], 'readwrite');
            const store = transaction.objectStore('cachedProducts');
            
            // Limpiar cache anterior
            const clearRequest = store.clear();
            
            clearRequest.onsuccess = () => {
                // Agregar timestamp a cada producto
                const productosConTimestamp = productos.map(producto => ({
                    ...producto,
                    cache_timestamp: Date.now(),
                    cache_metadata: metadata
                }));
                
                // Guardar nuevos productos
                let savedCount = 0;
                let hasError = false;
                
                productosConTimestamp.forEach(producto => {
                    const addRequest = store.add(producto);
                    
                    addRequest.onsuccess = () => {
                        savedCount++;
                        if (savedCount === productosConTimestamp.length && !hasError) {
                            console.log(`Guardados ${savedCount} productos en cache`);
                            resolve();
                        }
                    };
                    
                    addRequest.onerror = () => {
                        hasError = true;
                        console.error('Error guardando producto en cache:', producto.id);
                        if (!hasError) reject(addRequest.error);
                    };
                });
            };
            
            clearRequest.onerror = () => {
                reject(clearRequest.error);
            };
        });
    }
    
    // Buscar productos en cache offline
    async searchProductsOffline(query, options = {}) {
        const {
            categoria = '',
            marca = '',
            limit = 20,
            includeAgotados = true
        } = options;
        
        try {
            let resultados = [...this.cachedProducts];
            
            // Filtrar por texto de búsqueda
            if (query && query.trim()) {
                const queryLower = query.toLowerCase().trim();
                resultados = resultados.filter(producto => 
                    producto.searchable_text.includes(queryLower) ||
                    producto.codigo_principal.toLowerCase().includes(queryLower) ||
                    producto.codigo_auxiliar.toLowerCase().includes(queryLower)
                );
            }
            
            // Filtrar por categoría
            if (categoria && categoria !== '') {
                resultados = resultados.filter(producto => 
                    producto.categoria.id == categoria
                );
            }
            
            // Filtrar por marca
            if (marca && marca !== '') {
                resultados = resultados.filter(producto => 
                    producto.marca.id == marca
                );
            }
            
            // Filtrar productos agotados si no se incluyen
            if (!includeAgotados) {
                resultados = resultados.filter(producto => !producto.agotado);
            }
            
            // Limitar resultados
            if (limit > 0) {
                resultados = resultados.slice(0, limit);
            }
            
            // Agregar información de estado offline
            resultados = resultados.map(producto => ({
                ...producto,
                from_cache: true,
                cache_age: Date.now() - (producto.cache_timestamp || 0)
            }));
            
            return {
                success: true,
                productos: resultados,
                count: resultados.length,
                query: query,
                from_cache: true,
                cache_size: this.cachedProducts.length,
                timestamp: Date.now()
            };
            
        } catch (error) {
            console.error('Error en búsqueda offline:', error);
            return {
                success: false,
                productos: [],
                count: 0,
                error: error.message,
                from_cache: true
            };
        }
    }
    
    // Obtener producto por ID desde cache
    async getProductFromCache(productId) {
        try {
            const producto = this.cachedProducts.find(p => p.id == productId);
            
            if (producto) {
                return {
                    success: true,
                    producto: {
                        ...producto,
                        from_cache: true,
                        cache_age: Date.now() - (producto.cache_timestamp || 0)
                    }
                };
            } else {
                return {
                    success: false,
                    error: 'Producto no encontrado en cache',
                    producto: null
                };
            }
            
        } catch (error) {
            console.error('Error obteniendo producto desde cache:', error);
            return {
                success: false,
                error: error.message,
                producto: null
            };
        }
    }
    
    // Buscar productos (online/offline automático)
    async searchProducts(query, options = {}) {
        if (this.isOnline) {
            // Intentar búsqueda online primero
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
                    return {
                        ...data,
                        from_cache: false
                    };
                }
                
            } catch (error) {
                console.log('Error en búsqueda online, usando cache offline');
            }
        }
        
        // Usar cache offline como fallback
        console.log('Usando búsqueda offline desde cache');
        return await this.searchProductsOffline(query, options);
    }
    
    // Obtener estadísticas del cache de productos
    getProductsCacheStats() {
        const totalProductos = this.cachedProducts.length;
        const productosAgotados = this.cachedProducts.filter(p => p.agotado).length;
        const productosBajoStock = this.cachedProducts.filter(p => p.bajo_stock).length;
        const cacheAge = this.lastProductsCacheUpdate ? Date.now() - this.lastProductsCacheUpdate : 0;
        
        return {
            total_productos: totalProductos,
            productos_agotados: productosAgotados,
            productos_bajo_stock: productosBajoStock,
            cache_version: this.productsCacheVersion,
            cache_age_minutes: Math.floor(cacheAge / 60000),
            last_update: this.lastProductsCacheUpdate ? new Date(this.lastProductsCacheUpdate).toLocaleString() : 'Nunca'
        };
    }
    
    // Forzar actualización del cache de productos
    async forceUpdateProductsCache() {
        if (!this.isOnline) {
            this.showError('Sin conexión: No se puede actualizar cache');
            return false;
        }
        
        try {
            this.showToast('Actualizando cache de productos...', 'info');
            await this.updateProductsCache();
            return true;
        } catch (error) {
            this.showError('Error actualizando cache de productos');
            return false;
        }
    }
    
    // Configurar botón de sincronización manual
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
        }
    }
    
    // Actualizar contador de ventas pendientes
    updatePendingSalesCounter() {
        let counter = document.getElementById('pending-sales-counter');
        
        if (this.offlineSales.length > 0) {
            if (!counter) {
                counter = document.createElement('div');
                counter.id = 'pending-sales-counter';
                counter.style.cssText = `
                    position: fixed;
                    top: 150px;
                    left: 20px;
                    background: rgba(255, 193, 7, 0.9);
                    color: #856404;
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 10px;
                    font-weight: bold;
                    z-index: 9997;
                    backdrop-filter: blur(5px);
                    border: 1px solid rgba(255,193,7,0.3);
                `;
                document.body.appendChild(counter);
            }
            
            counter.textContent = `📋 ${this.offlineSales.length} venta(s) pendiente(s)`;
            
            // Configurar botón de sincronización
            this.setupManualSyncButton();
            
        } else if (counter) {
            counter.remove();
            const syncBtn = document.getElementById('manual-sync-btn');
            if (syncBtn) syncBtn.remove();
        }
    }
    
    // Mostrar confirmación de venta offline
    showOfflineSaleConfirmation(sale) {
        const modal = this.createModal('Venta Guardada Offline', `
            <div class="alert alert-warning">
                <i class="fas fa-wifi" style="color: #dc3545;"></i>
                <strong>Sin conexión a internet</strong>
            </div>
            <p><strong>Venta guardada exitosamente en modo offline:</strong></p>
            <ul>
                <li><strong>ID Temporal:</strong> ${sale.id}</li>
                <li><strong>Cliente:</strong> ${sale.customer_name}</li>
                <li><strong>Total:</strong> $${sale.total.toFixed(2)}</li>
                <li><strong>Fecha:</strong> ${new Date(sale.timestamp).toLocaleString()}</li>
            </ul>
            <div class="alert alert-info">
                <i class="fas fa-sync"></i>
                La venta se sincronizará automáticamente cuando se restaure la conexión.
            </div>
        `);
        
        modal.show();
    }
    
    // Utilidades de UI
    showSyncProgress() {
        let progress = document.getElementById('sync-progress');
        if (!progress) {
            progress = document.createElement('div');
            progress.id = 'sync-progress';
            progress.innerHTML = '<i class="fas fa-sync fa-spin"></i> Sincronizando...';
            progress.style.cssText = `
                position: fixed;
                top: 130px;
                right: 10px;
                background: #17a2b8;
                color: white;
                padding: 8px 12px;
                border-radius: 20px;
                font-size: 12px;
                z-index: 9996;
            `;
            document.body.appendChild(progress);
        }
    }
    
    hideSyncProgress() {
        const progress = document.getElementById('sync-progress');
        if (progress) progress.remove();
    }
    
    showSyncResult(syncedCount, errorCount) {
        const message = syncedCount > 0 
            ? `✅ ${syncedCount} venta(s) sincronizada(s)` 
            : '⚠️ No se pudo sincronizar ninguna venta';
            
        this.showToast(message, syncedCount > 0 ? 'success' : 'warning');
    }
    
    showError(message) {
        this.showToast(message, 'error');
    }
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'warning'}`;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 10000;
            min-width: 300px;
            text-align: center;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 4000);
    }
    
    createModal(title, content) {
        const modalHtml = `
            <div class="modal fade" id="offlineModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${content}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-primary" data-bs-dismiss="modal">Entendido</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const existingModal = document.getElementById('offlineModal');
        if (existingModal) existingModal.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        return new bootstrap.Modal(document.getElementById('offlineModal'));
    }
    
    // Manejar mensajes del Service Worker
    handleServiceWorkerMessage(data) {
        if (data.type === 'SYNC_COMPLETE') {
            console.log(`Sync completo: ${data.syncedCount} sincronizadas, ${data.pendingCount} pendientes`);
            this.loadOfflineSales(); // Recargar estado
        }
        
        if (data.type === 'PRODUCTS_CACHE_UPDATED') {
            console.log(`Cache de productos actualizado: ${data.productsCount} productos`);
            this.loadProductsCache(); // Recargar productos desde IndexedDB
            this.showToast(`Cache actualizado: ${data.productsCount} productos`, 'success');
        }
        
        if (data.type === 'PRODUCTS_CACHE_INVALIDATED') {
            console.log('Cache de productos invalidado');
            this.updateProductsCache(); // Actualizar inmediatamente
        }
    }
    
    // Solicitar actualización del cache de productos al Service Worker
    requestProductsCacheUpdate() {
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({
                type: 'UPDATE_PRODUCTS_CACHE'
            });
        }
    }
    
    // Invalidar cache de productos
    invalidateProductsCache() {
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({
                type: 'INVALIDATE_PRODUCTS_CACHE'
            });
        }
    }
    
    // Mostrar notificación de actualización del SW
    showUpdateNotification() {
        const updateNotification = this.createModal('Actualización Disponible', `
            <div class="alert alert-info">
                <i class="fas fa-download"></i>
                <strong>Nueva versión disponible</strong>
            </div>
            <p>Hay una actualización del sistema disponible. ¿Deseas instalarla ahora?</p>
            <small class="text-muted">La página se recargará automáticamente.</small>
        `);
        
        // Agregar botón de actualización
        const updateButton = document.createElement('button');
        updateButton.className = 'btn btn-success me-2';
        updateButton.textContent = 'Actualizar Ahora';
        updateButton.onclick = () => {
            if (navigator.serviceWorker.controller) {
                navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
            }
            window.location.reload();
        };
        
        const modalFooter = document.querySelector('#offlineModal .modal-footer');
        modalFooter.insertBefore(updateButton, modalFooter.firstChild);
        
        updateNotification.show();
    }
}

// Inicializar el sistema offline cuando la página esté lista
document.addEventListener('DOMContentLoaded', () => {
    // Solo inicializar si estamos en páginas relevantes
    const relevantPages = ['/ventas/', '/productos/', '/dashboard/', '/'];
    const currentPath = window.location.pathname;
    
    const isRelevantPage = relevantPages.some(page => 
        currentPath === page || currentPath.startsWith(page)
    );
    
    if (isRelevantPage) {
        window.offlineManager = new OfflineManager();
    }
});

// Exportar para uso global
window.OfflineManager = OfflineManager;