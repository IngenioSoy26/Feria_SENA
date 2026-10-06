/* ============================================================
 * Service Worker - Sistema Gestión Feria SENA
 * Estrategia: App Shell (Cache-First para estáticos) +
 *             Network-First para HTML dinámico +
 *             Offline Fallback explícito.
 * ============================================================ */

const VERSION = 'sena-feria-v1.0.0';
const STATIC_CACHE = `static-${VERSION}`;
const RUNTIME_CACHE = `runtime-${VERSION}`;

const APP_SHELL_STATIC = [
  '/',
  '/offline.html',
  '/static/css/sena.css',
  '/static/js/app.js',
  '/static/js/lector_qr.js',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
];

const EXTENSIONES_IMAGEN = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'ico', 'webp'];
const EXTENSIONES_ESTATICAS = ['css', 'js', 'woff', 'woff2', 'ttf', 'otf', 'eot'].concat(
  EXTENSIONES_IMAGEN
);

function esExtensionEstatica(url) {
  const cleanUrl = url.split('?')[0];
  for (const ext of EXTENSIONES_ESTATICAS) {
    if (cleanUrl.endsWith('.' + ext)) return true;
  }
  return false;
}

function esSolicitudPost(request) {
  return request.method === 'POST';
}

function esSolicitudHtml(request) {
  const accept = request.headers.get('accept') || '';
  return (
    accept.includes('text/html') &&
    !esSolicitudPost(request)
  );
}

/* ---------------- Instalación (App Shell) ---------------- */

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll(APP_SHELL_STATIC))
      .then(() => self.skipWaiting())
      .catch((err) => console.warn('[SW] Instalación parcial, error:', err))
  );
});

/* ---------------- Activación ---------------- */

self.addEventListener('activate', (event) => {
  const cachesEsperados = [STATIC_CACHE, RUNTIME_CACHE];
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        keys.filter((key) => !cachesEsperados.includes(key))
      )
      .then((keysEliminar) =>
        Promise.all(keysEliminar.map((key) => caches.delete(key)))
      )
      .then(() => self.clients.claim())
  );
});

/* ---------------- Estrategias ---------------- */

async function estrategiaCacheFirstConFallback(request) {
  const cache = await caches.open(STATIC_CACHE);
  const hit = await cache.match(request);
  if (hit) return hit;

  const runtime = await caches.open(RUNTIME_CACHE);
  const hitRuntime = await runtime.match(request);
  if (hitRuntime) return hitRuntime;

  try {
    const respuesta = await fetch(request);
    if (respuesta && respuesta.status === 200 && respuesta.type === 'basic') {
      if (esExtensionEstatica(request.url)) {
        runtime.put(request, respuesta.clone());
      }
    }
    return respuesta;
  } catch (err) {
    return caches.match('/offline.html');
  }
}

async function estrategiaNetworkFirstHtml(request) {
  try {
    const respuesta = await fetch(request);
    if (respuesta && respuesta.status === 200 && respuesta.type === 'basic') {
      const clon = respuesta.clone();
      const runtime = await caches.open(RUNTIME_CACHE);
      runtime.put(request, clon).catch(() => {});
    }
    return respuesta;
  } catch (err) {
    const desdeCache = await caches.match(request);
    if (desdeCache) return desdeCache;
    return caches.match('/offline.html');
  }
}

/* ---------------- Fetch ---------------- */

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  if (url.origin !== location.origin) return;

  if (esSolicitudPost(request)) {
    return;
  }

  if (request.mode === 'navigate' || esSolicitudHtml(request)) {
    event.respondWith(estrategiaNetworkFirstHtml(request));
    return;
  }

  if (esExtensionEstatica(url.pathname)) {
    event.respondWith(estrategiaCacheFirstConFallback(request));
    return;
  }

  event.respondWith(
    fetch(request).catch(() =>
      caches.match(request).then((r) => r || caches.match('/offline.html'))
    )
  );
});

/* ---------------- Mensajes ---------------- */

self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
