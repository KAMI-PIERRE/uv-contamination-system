/**
 * api.js — Shared API helpers and UI utilities
 * Loaded on every page via base.html
 */

'use strict';

/* ── Core fetch wrapper ──────────────────────────────────────────────────── */

/**
 * Fetch a JSON endpoint and return parsed data.
 * Throws an Error with server message on non-2xx status.
 *
 * @param {string} url - Relative or absolute URL
 * @param {RequestInit} [options] - Optional fetch init overrides
 * @returns {Promise<any>} Parsed JSON response
 */
async function apiFetch(url, options = {}) {
  const defaults = {
    headers: {
      'Content-Type': 'application/json',
      'Accept':       'application/json',
    },
  };

  const config = {
    ...defaults,
    ...options,
    headers: {
      ...defaults.headers,
      ...(options.headers || {}),
    },
  };

  const res = await fetch(url, config);

  // Try to parse JSON even for error responses
  let data;
  try {
    data = await res.json();
  } catch (_) {
    data = {};
  }

  if (!res.ok) {
    const msg = data.error || data.message || `HTTP ${res.status}`;
    throw new Error(msg);
  }

  return data;
}


/* ── Toast notifications ─────────────────────────────────────────────────── */

/**
 * Display a Bootstrap toast notification.
 *
 * @param {string} message - Text to display
 * @param {'primary'|'success'|'danger'|'warning'|'info'} [type] - Colour variant
 */
function showToast(message, type = 'primary') {
  const toastEl = document.getElementById('appToast');
  const msgEl   = document.getElementById('toastMessage');
  if (!toastEl || !msgEl) return;

  // Update colour class
  toastEl.className = toastEl.className
    .replace(/text-bg-\w+/, `text-bg-${type}`);

  msgEl.textContent = message;

  const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
  toast.show();
}


/* ── Label badge helper ──────────────────────────────────────────────────── */

/**
 * Return an HTML badge string for a contamination label.
 *
 * @param {string|null} label
 * @returns {string} HTML span element
 */
function labelBadge(label) {
  if (!label) return '<span class="badge-unknown">—</span>';
  switch (label.toLowerCase()) {
    case 'clean':    return `<span class="badge-clean">${label}</span>`;
    case 'dirty':    return `<span class="badge-dirty">${label}</span>`;
    case 'critical': return `<span class="badge-critical">${label}</span>`;
    default:         return `<span class="badge-unknown">${label}</span>`;
  }
}


/* ── Label colour helper (for Chart.js) ─────────────────────────────────── */

/**
 * Return a CSS colour string for a contamination label.
 *
 * @param {string|null} label
 * @returns {string} CSS colour
 */
function labelColor(label) {
  if (!label) return '#64748b';
  switch (label.toLowerCase()) {
    case 'clean':    return '#10b981';
    case 'dirty':    return '#f59e0b';
    case 'critical': return '#ef4444';
    default:         return '#6366f1';
  }
}


/* ── Timestamp formatter ────────────────────────────────────────────────── */

/**
 * Format an ISO timestamp string to a human-readable local time.
 *
 * @param {string|null} iso - ISO 8601 string
 * @returns {string} Formatted string or '—'
 */
function formatTs(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(undefined, {
      year:   'numeric',
      month:  'short',
      day:    '2-digit',
      hour:   '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch (_) {
    return iso;
  }
}


/* ── Flash animation on value update ────────────────────────────────────── */

/**
 * Briefly flash a DOM element to signal a value changed.
 *
 * @param {HTMLElement} el
 */
function flashUpdate(el) {
  if (!el) return;
  el.classList.remove('value-updated');
  // Trigger reflow to restart animation
  void el.offsetWidth;
  el.classList.add('value-updated');
}
