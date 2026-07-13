/**
 * dashboard.js — Main dashboard page controller
 * Polls the latest reading, updates all stat cards, gauge,
 * prediction panel, and the recent readings table.
 */

'use strict';

/* ── State ────────────────────────────────────────────────────────────────── */
const POLL_INTERVAL_MS = 3000;   // Poll every 3 seconds
let   realtimeCtrl     = null;   // Rolling chart controller
let   lastReadingId    = null;   // Track last seen reading ID to detect changes

/* ── Init on DOM ready ───────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  // Build rolling UV trend chart
  realtimeCtrl = createRealtimeChart('realtimeChart', 40);

  // First load immediately, then poll
  refresh();
  setInterval(refresh, POLL_INTERVAL_MS);

  // Load recent readings table once (refreshes less frequently)
  loadRecentTable();
  setInterval(loadRecentTable, 10000);
});


/* ── Main refresh cycle ──────────────────────────────────────────────────── */

/**
 * Fetch the latest reading and update all dashboard widgets.
 */
async function refresh() {
  try {
    const r = await apiFetch('/api/latest');
    updateStatCards(r);
    updateLivePanel(r);
    updatePredictionPanel(r);
    updateGauge(r.uv_raw);

    // Push to rolling chart only when a new reading arrives
    if (r.id !== lastReadingId) {
      lastReadingId = r.id;
      const timeLabel = new Date(r.timestamp).toLocaleTimeString();
      realtimeCtrl.update(r.uv_raw, timeLabel);
    }
  } catch (e) {
    console.warn('[Dashboard] Fetch error:', e.message);
  }
}


/* ── Stat Cards ──────────────────────────────────────────────────────────── */

/**
 * Update the six summary stat cards with values from the latest reading.
 *
 * @param {Object} r - Latest reading object
 */
function updateStatCards(r) {
  setCard('statUvRaw',   r.uv_raw   ?? '—');
  setCard('statUvAvg',   r.uv_average != null ? r.uv_average.toFixed(1) : '—');
  setCard('statUvMin',   r.uv_min   ?? '—');
  setCard('statUvMax',   r.uv_max   ?? '—');
  setCard('statUvRange', r.uv_range ?? '—');
  setCard('statVoltage', r.voltage_mv != null ? r.voltage_mv.toFixed(0) : '—');
}

function setCard(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  if (String(el.textContent) !== String(value)) {
    el.textContent = value;
    flashUpdate(el);
  }
}


/* ── Live Reading Panel ──────────────────────────────────────────────────── */

/**
 * Update device metadata rows in the live reading panel.
 *
 * @param {Object} r - Latest reading object
 */
function updateLivePanel(r) {
  setText('metaDevice',    r.device_id    ?? '—');
  setText('metaTimestamp', formatTs(r.timestamp));
  setText('metaSurface',   r.surface_type ?? '—');
  setText('metaDistance',  r.distance_cm != null ? r.distance_cm + ' cm' : '—');
  setText('gaugeValue',    r.uv_raw ?? '—');
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}


/* ── Prediction Panel ────────────────────────────────────────────────────── */

/**
 * Update the prediction circle, confidence bar, and probability breakdown.
 *
 * @param {Object} r - Latest reading object
 */
function updatePredictionPanel(r) {
  const label = r.predicted_label;
  const conf  = r.confidence;

  // Prediction circle
  const circle = document.getElementById('predCircle');
  const lbl    = document.getElementById('predLabel');
  if (circle && lbl) {
    lbl.textContent = label || '—';
    circle.className = 'prediction-circle ' + (label ? label.toLowerCase() : '');
  }

  // Confidence bar
  const confPct = conf != null ? (conf * 100).toFixed(1) : null;
  const confEl  = document.getElementById('confValue');
  const confBar = document.getElementById('confBar');
  if (confEl) confEl.textContent = confPct ? confPct + '%' : '—';
  if (confBar) {
    confBar.style.width = confPct ? confPct + '%' : '0%';
    confBar.style.background = label ? labelColor(label) : '#6366f1';
  }

  // Probability breakdown is not available from /api/latest
  // so we render a simple display using confidence
  const breakdown = document.getElementById('probBreakdown');
  if (breakdown && label) {
    breakdown.innerHTML = `
      <div class="d-flex align-items-center gap-2 mb-1">
        <span class="small text-muted" style="width:70px">${label}</span>
        <div class="progress flex-fill" style="height:5px">
          <div class="progress-bar" style="width:${confPct || 0}%;background:${labelColor(label)}"></div>
        </div>
        <span class="small" style="color:${labelColor(label)}">${confPct || '—'}%</span>
      </div>
    `;
  }
}


/* ── Semi-circle gauge ───────────────────────────────────────────────────── */

/**
 * Redraw the UV gauge arc.
 *
 * @param {number|null} value
 */
function updateGauge(value) {
  if (value == null) return;
  drawGauge('uvGauge', value, 200);
}


/* ── Recent Readings Table ───────────────────────────────────────────────── */

/**
 * Load the 10 most recent readings and render them into the table.
 */
async function loadRecentTable() {
  try {
    const data = await apiFetch('/api/readings?per_page=10&page=1');
    renderRecentTable(data.readings || []);
  } catch (e) {
    console.warn('[Dashboard] Table load error:', e.message);
  }
}

/**
 * Render rows into the recent readings table.
 *
 * @param {Array} readings
 */
function renderRecentTable(readings) {
  const tbody = document.getElementById('recentTableBody');
  if (!tbody) return;

  if (!readings.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted py-3">No readings yet.</td></tr>';
    return;
  }

  tbody.innerHTML = readings.map(r => `
    <tr>
      <td class="text-muted">${r.id}</td>
      <td class="text-info small">${r.device_id}</td>
      <td><strong>${r.uv_raw ?? '—'}</strong></td>
      <td>${r.uv_average != null ? r.uv_average.toFixed(1) : '—'}</td>
      <td>${r.voltage_mv != null ? r.voltage_mv.toFixed(0) : '—'}</td>
      <td>${r.surface_type ?? '—'}</td>
      <td>${labelBadge(r.manual_label)}</td>
      <td>${labelBadge(r.predicted_label)}</td>
      <td>${r.confidence != null ? (r.confidence * 100).toFixed(1) + '%' : '—'}</td>
      <td class="text-muted small">${formatTs(r.timestamp)}</td>
    </tr>
  `).join('');
}
