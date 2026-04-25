// Service worker for the PS×PC crossplay PWA.
//
// Strategy:
// - Static assets (HTML/CSS/JS/icons/manifest): cache-first, precached on install.
// - games.json: network-first with a cache fallback, so a fresh open always
//   pulls the newest catalog but the app still boots offline.
// - Everything else (RAWG CDN covers, Safari-opened image searches): pass-through.

const CACHE_VERSION = "v3";
const STATIC_CACHE = `pscrossplay-static-${CACHE_VERSION}`;
const RUNTIME_CACHE = `pscrossplay-runtime-${CACHE_VERSION}`;

const PRECACHE_URLS = [
  "./",
  "./index.html",
  "./app.js",
  "./style.css",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/apple-touch-icon.png",
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== STATIC_CACHE && k !== RUNTIME_CACHE)
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Only handle same-origin requests; let cross-origin (RAWG images,
  // google.com search from card taps) pass through.
  if (url.origin !== self.location.origin) return;

  // games.json: always try network first, fall back to whatever's cached.
  if (url.pathname.endsWith("/games.json")) {
    event.respondWith(networkFirst(req));
    return;
  }

  // Everything else on our origin: cache-first.
  event.respondWith(cacheFirst(req));
});

async function cacheFirst(req) {
  const cached = await caches.match(req);
  if (cached) return cached;
  const resp = await fetch(req);
  if (resp.ok) {
    const cache = await caches.open(STATIC_CACHE);
    cache.put(req, resp.clone());
  }
  return resp;
}

async function networkFirst(req) {
  const cache = await caches.open(RUNTIME_CACHE);
  try {
    const resp = await fetch(req, { cache: "no-store" });
    if (resp.ok) cache.put(req, resp.clone());
    return resp;
  } catch (e) {
    const cached = await cache.match(req);
    if (cached) return cached;
    throw e;
  }
}

// Allow the app to request an immediate games.json refresh by posting a
// `{type: "refresh-games"}` message.
self.addEventListener("message", event => {
  if (event.data?.type === "refresh-games") {
    event.waitUntil(
      fetch("./games.json", { cache: "no-store" }).then(resp => {
        if (resp.ok) {
          return caches.open(RUNTIME_CACHE).then(c => c.put("./games.json", resp));
        }
      })
    );
  }
});
