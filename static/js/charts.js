/**
 * charts.js — Chart initialisation helpers for the dashboard
 * Provides the real-time UV trend chart and semi-circular gauge.
 */

'use strict';

/* ── Chart.js global defaults ────────────────────────────────────────────── */
Chart.defaults.color          = '#94a3b8';
Chart.defaults.borderColor    = '#2d3748';
Chart.defaults.backgroundColor= 'rgba(99,102,241,0.6)';
Chart.defaults.font.family    = "'Segoe UI', system-ui, sans-serif";
Chart.defaults.font.size      = 12;


/* ══════════════════════════════ REAL-TIME LINE CHART ══ */

/**
 * Create and manage the rolling real-time UV sparkline chart.
 *
 * @param {string} canvasId - ID of the <canvas> element
 * @param {number} [maxPoints=30] - Maximum data points to keep
 * @returns {{ update: (value: number, label: string) => void }} Controller
 */
function createRealtimeChart(canvasId, maxPoints = 30) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return { update: () => {} };

  const chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'UV Raw',
        data: [],
        borderColor:     'rgba(99,102,241,0.9)',
        backgroundColor: 'rgba(99,102,241,0.08)',
        fill:       true,
        tension:    0.4,
        pointRadius: 2,
        pointHoverRadius: 4,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 300 },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `UV: ${ctx.parsed.y}`,
          }
        }
      },
      scales: {
        x: {
          ticks: { color: '#64748b', maxTicksLimit: 5, maxRotation: 0 },
          grid:  { color: '#21262d' },
        },
        y: {
          ticks: { color: '#64748b' },
          grid:  { color: '#21262d' },
          beginAtZero: true,
        }
      }
    }
  });

  /**
   * Push a new data point onto the rolling chart.
   *
   * @param {number} value   - UV raw value
   * @param {string} label   - X-axis label (usually time string)
   */
  function update(value, label) {
    const d = chart.data;
    d.labels.push(label);
    d.datasets[0].data.push(value);

    // Trim to maxPoints
    if (d.labels.length > maxPoints) {
      d.labels.shift();
      d.datasets[0].data.shift();
    }

    chart.update('none'); // 'none' skips animation for smooth scrolling
  }

  return { update, chart };
}


/* ══════════════════════════════ SEMI-CIRCLE GAUGE ══ */

/**
 * Draw a semi-circular gauge arc on a canvas.
 * Represents the current UV raw value as a coloured arc.
 *
 * @param {string} canvasId - ID of the <canvas> element
 * @param {number} value    - Current value
 * @param {number} [max=200] - Maximum expected value
 */
function drawGauge(canvasId, value, max = 200) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx  = canvas.getContext('2d');
  const W    = canvas.width;
  const H    = canvas.height;
  const cx   = W / 2;
  const cy   = H - 8;
  const r    = Math.min(W, H * 2) / 2 - 14;

  ctx.clearRect(0, 0, W, H);

  const startAngle = Math.PI;         // 180° — left
  const endAngle   = 0;               // 0°   — right
  const pct        = Math.min(value / max, 1);
  const fillAngle  = Math.PI + (Math.PI * pct);

  // Track arc (background)
  ctx.beginPath();
  ctx.arc(cx, cy, r, Math.PI, 0, false);
  ctx.strokeStyle = '#2d3748';
  ctx.lineWidth   = 14;
  ctx.lineCap     = 'round';
  ctx.stroke();

  // Fill arc (value)
  const gradient = ctx.createLinearGradient(cx - r, cy, cx + r, cy);
  gradient.addColorStop(0,   '#10b981'); // green  = clean
  gradient.addColorStop(0.5, '#f59e0b'); // orange = dirty
  gradient.addColorStop(1,   '#ef4444'); // red    = critical

  ctx.beginPath();
  ctx.arc(cx, cy, r, Math.PI, fillAngle, false);
  ctx.strokeStyle = gradient;
  ctx.lineWidth   = 14;
  ctx.lineCap     = 'round';
  ctx.stroke();

  // Tick marks
  const ticks = 5;
  for (let i = 0; i <= ticks; i++) {
    const angle = Math.PI + (Math.PI / ticks) * i;
    const innerR = r - 20;
    const outerR = r - 10;
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(angle) * innerR, cy + Math.sin(angle) * innerR);
    ctx.lineTo(cx + Math.cos(angle) * outerR, cy + Math.sin(angle) * outerR);
    ctx.strokeStyle = '#4a5568';
    ctx.lineWidth   = 1.5;
    ctx.stroke();
  }
}
