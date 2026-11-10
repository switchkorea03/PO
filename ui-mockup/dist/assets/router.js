const ROUTES = [
  [/^\/$/, () => ({ screen: 'dashboard' })],
  [/^\/orders$/, () => ({ screen: 'orders' })],
  [/^\/orders\/([^/]+)$/, match => ({ screen: 'order-detail', id: decodeURIComponent(match[1]) })],
  [/^\/review\/([^/]+)$/, match => ({ screen: 'po-review', id: decodeURIComponent(match[1]) })],
  [/^\/operations\/([^/]+)$/, match => ({ screen: 'operations', section: match[1] })],
  [/^\/master$/, () => ({ screen: 'master-data' })]
];

export function parseRoute(hash = globalThis.location?.hash || '#/') {
  const raw = hash.replace(/^#/, '') || '/';
  const [path, queryString = ''] = raw.split('?');
  const query = Object.fromEntries(new URLSearchParams(queryString));
  for (const [pattern, makeRoute] of ROUTES) {
    const match = path.match(pattern);
    if (match) {
      const route = makeRoute(match);
      return Object.keys(query).length ? { ...route, query } : route;
    }
  }
  return { screen: 'not-found' };
}

export function navigate(path) {
  globalThis.location.hash = path.startsWith('#') ? path : `#${path}`;
}
