'use strict';

// A display-only link guard. This does not replace the backend SSRF policy,
// since the browser is not asked to fetch or validate the source here.
function aegisSafeSourceUrl(value) {
  if (typeof value !== 'string' || !/^https?:\/\//i.test(value.trim())) return '';
  try {
    const url = new URL(value.trim());
    if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password) return '';
    return url.href;
  } catch (_) {
    return '';
  }
}

if (typeof module !== 'undefined' && module.exports) module.exports = { aegisSafeSourceUrl };
