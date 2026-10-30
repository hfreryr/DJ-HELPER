// Remplace le pont pywebview par des appels HTTP vers tests/ui/server.py.
window.pywebview = { api: new Proxy({}, { get: (_, name) => (name === 'then') ? undefined :
  async (...args) => {
    const r = await fetch('/api/' + String(name), {method: 'POST', body: JSON.stringify(args)});
    return r.json();
  } }) };
window.__errors = [];
window.__csp = [];
window.addEventListener('error', e => window.__errors.push(e.message));
window.addEventListener('unhandledrejection', e => window.__errors.push('rej: ' + (e.reason && e.reason.message || e.reason)));
document.addEventListener('securitypolicyviolation', e => window.__csp.push(e.violatedDirective + ' ' + e.blockedURI));
