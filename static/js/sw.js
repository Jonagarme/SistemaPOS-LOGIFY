// Service Worker para Sistema POS Offline
const CACHE_NAME = 'sistema-pos-v1.0';
const OFFLINE_URL = '/offline/';

// Recursos críticos para cachear
const CRITICAL_RESOURCES = [
    '/',
    '/static/css/bootstrap.min.css',
    '/static/css/custom.css',
    '/static/js/bootstrap.bundle.min.js',
    '/static/js/offline-manager.js',
    '/ventas/nueva/',
    '/productos/api/buscar/',
    OFFLINE_URL
];

// Recursos de productos y ventas para cache dinámico
const DYNAMIC_CACHE = 'sistema-pos-dynamic-v1.0';

// Instalación del Service Worker
self.addEventListener('install', event => {
    console.log('Service Worker: Instalando...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Cacheando recursos críticos');
                return cache.addAll(CRITICAL_RESOURCES);
            })
            .then(() => {
                console.log('Service Worker: Instalación completa');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('Service Worker: Error en instalación', error);
            })
    );
});

// Activación del Service Worker
self.addEventListener('activate', event => {
    console.log('Service Worker: Activando...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(cacheName => {
                            // Eliminar caches antiguos
                            return cacheName !== CACHE_NAME && cacheName !== DYNAMIC_CACHE;
                        })
                        .map(cacheName => {
                            console.log('Service Worker: Eliminando cache antiguo', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            })
            .then(() => {
                console.log('Service Worker: Activación completa');
                return self.clients.claim();
            })
    );
});

// Interceptar requests
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Solo manejar requests del mismo origen
    if (url.origin !== location.origin) {
        return;
    }
    
    // Estrategia Cache First para recursos estáticos
    if (request.destination === 'style' || 
        request.destination === 'script' || 
        request.destination === 'image') {
        
        event.respondWith(cacheFirst(request));
        return;
    }
    
    // Estrategia Network First para API y páginas
    if (url.pathname.startsWith('/api/') || 
        url.pathname.startsWith('/ventas/') ||
        url.pathname.startsWith('/productos/')) {
        
        event.respondWith(networkFirst(request));
        return;
    }
    
    // Estrategia Stale While Revalidate para páginas principales
    event.respondWith(staleWhileRevalidate(request));
});

// Estrategia Cache First
async function cacheFirst(request) {
    try {
        const cache = await caches.open(CACHE_NAME);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('Cache First error:', error);
        return new Response('Recurso no disponible offline', { status: 503 });
    }
}

// Estrategia Network First
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('Network First: Sin conexión, buscando en cache');
        
        const cache = await caches.open(DYNAMIC_CACHE);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Si es una venta, manejar offline
        if (request.url.includes('/ventas/procesar-venta/')) {
            return handleOfflineSale(request);
        }
        
        // Respuesta offline genérica
        return new Response(
            JSON.stringify({ 
                error: 'Sin conexión a internet',
                offline: true,
                timestamp: Date.now()
            }),
            { 
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Estrategia Stale While Revalidate
async function staleWhileRevalidate(request) {
    const cache = await caches.open(CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    const fetchPromise = fetch(request)
        .then(networkResponse => {
            if (networkResponse.ok) {
                cache.put(request, networkResponse.clone());
            }
            return networkResponse;
        })
        .catch(() => cachedResponse);
    
    return cachedResponse || await fetchPromise;
}

// Manejar ventas offline
async function handleOfflineSale(request) {
    try {
        // Leer datos de la venta del request
        const formData = await request.formData();
        const ventaData = Object.fromEntries(formData);
        
        // Generar ID temporal para la venta offline
        const offlineId = 'offline_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        // Estructura de venta offline
        const offlineSale = {
            id: offlineId,
            timestamp: Date.now(),
            data: ventaData,
            status: 'pending_sync',
            attempts: 0,
            created_offline: true
        };
        
        // Guardar en IndexedDB (implementaremos esto después)
        await saveOfflineSale(offlineSale);
        
        // Respuesta simulando éxito
        return new Response(
            JSON.stringify({
                success: true,
                offline: true,
                numero_venta: offlineId,
                total: ventaData.total || 0,
                message: 'Venta guardada offline. Se sincronizará cuando haya conexión.'
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            }
        );
        
    } catch (error) {
        console.error('Error manejando venta offline:', error);
        return new Response(
            JSON.stringify({ 
                error: 'Error guardando venta offline',
                offline: true 
            }),
            { 
                status: 500,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Placeholder para guardar venta offline (implementaremos IndexedDB después)
async function saveOfflineSale(saleData) {
    // Esta función se implementará con IndexedDB
    console.log('Guardando venta offline:', saleData);
    
    // Por ahora usar localStorage como fallback
    const offlineSales = JSON.parse(localStorage.getItem('offline_sales') || '[]');
    offlineSales.push(saleData);
    localStorage.setItem('offline_sales', JSON.stringify(offlineSales));
}

// Escuchar mensajes del cliente
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'SYNC_OFFLINE_SALES') {
        // Iniciar sincronización de ventas offline
        syncOfflineSales();
    }
    
    if (event.data && event.data.type === 'UPDATE_PRODUCTS_CACHE') {
        // Actualizar cache de productos
        updateProductsCache();
    }
    
    if (event.data && event.data.type === 'INVALIDATE_PRODUCTS_CACHE') {
        // Invalidar cache de productos para forzar actualización
        invalidateProductsCache();
    }
});

// Actualizar cache de productos
async function updateProductsCache() {
    try {
        console.log('SW: Actualizando cache de productos...');
        
        const timestamp = Date.now();
        const response = await fetch(`/productos/api/cache/?timestamp=${timestamp}`);
        
        if (response.ok) {
            const data = await response.json();
            
            // Notificar al cliente sobre la actualización
            const clients = await self.clients.matchAll();
            clients.forEach(client => {
                client.postMessage({
                    type: 'PRODUCTS_CACHE_UPDATED',
                    productsCount: data.productos?.length || 0,
                    timestamp: timestamp
                });
            });
            
            console.log(`SW: Cache de productos actualizado - ${data.productos?.length || 0} productos`);
        }
        
    } catch (error) {
        console.error('SW: Error actualizando cache de productos:', error);
    }
}

// Invalidar cache de productos
async function invalidateProductsCache() {
    try {
        const cache = await caches.open(DYNAMIC_CACHE);
        const keys = await cache.keys();
        
        // Eliminar entradas relacionadas con productos
        const productsCacheKeys = keys.filter(request => 
            request.url.includes('/productos/api/')
        );
        
        await Promise.all(productsCacheKeys.map(key => cache.delete(key)));
        
        console.log('SW: Cache de productos invalidado');
        
        // Notificar al cliente
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'PRODUCTS_CACHE_INVALIDATED'
            });
        });
        
    } catch (error) {
        console.error('SW: Error invalidando cache de productos:', error);
    }
}

// Sincronización de ventas offline (básica)
async function syncOfflineSales() {
    try {
        const offlineSales = JSON.parse(localStorage.getItem('offline_sales') || '[]');
        const pendingSales = offlineSales.filter(sale => sale.status === 'pending_sync');
        
        for (const sale of pendingSales) {
            try {
                // Intentar enviar venta al servidor
                const response = await fetch('/ventas/procesar-venta/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': sale.data.csrfmiddlewaretoken || ''
                    },
                    body: JSON.stringify(sale.data)
                });
                
                if (response.ok) {
                    // Marcar como sincronizada
                    sale.status = 'synced';
                    sale.synced_at = Date.now();
                    console.log('Venta sincronizada:', sale.id);
                } else {
                    sale.attempts = (sale.attempts || 0) + 1;
                    console.error('Error sincronizando venta:', sale.id);
                }
                
            } catch (error) {
                sale.attempts = (sale.attempts || 0) + 1;
                console.error('Error en sincronización:', error);
            }
        }
        
        // Actualizar localStorage
        localStorage.setItem('offline_sales', JSON.stringify(offlineSales));
        
        // Notificar al cliente sobre el estado de sincronización
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_COMPLETE',
                syncedCount: pendingSales.filter(s => s.status === 'synced').length,
                pendingCount: pendingSales.filter(s => s.status === 'pending_sync').length
            });
        });
        
    } catch (error) {
        console.error('Error en sincronización general:', error);
    }
}

// Background Sync (si el navegador lo soporta)
self.addEventListener('sync', event => {
    if (event.tag === 'offline-sales-sync') {
        console.log('Background Sync: Sincronizando ventas offline');
        event.waitUntil(syncOfflineSales());
    }
});