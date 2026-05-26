/* ExpoEpics — app.js */

/* ── Auto-dismiss alerts ── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });
});

/* ── Login tabs ── */
function initLoginTabs() {
  const btns   = document.querySelectorAll('.tab-btn');
  const input  = document.getElementById('selected-tab');
  const panels = {
    docente:    document.getElementById('creds-docente'),
    estudiante: document.getElementById('creds-estudiante'),
    juez:       document.getElementById('creds-juez'),
  };

  function activate(tab) {
    btns.forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    Object.entries(panels).forEach(([k, el]) => {
      if (el) el.classList.toggle('hidden', k !== tab);
    });
    if (input) input.value = tab;
  }

  btns.forEach(btn => {
    btn.addEventListener('click', () => activate(btn.dataset.tab));
  });

  // Restore active tab from hidden input on page load
  if (input && input.value) activate(input.value);
}

/* ── Tarea comment inline toggle ── */
function toggleComment(id) {
  const el = document.getElementById('comment-form-' + id);
  if (el) el.classList.toggle('hidden');
}

/* ── Confirm dialogs ── */
function confirmAction(msg) {
  return confirm(msg || '¿Estás seguro?');
}

document.addEventListener('DOMContentLoaded', () => {
  initLoginTabs();

  // Add confirm to danger forms
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('submit', function (e) {
      if (!confirmAction(this.dataset.confirm)) e.preventDefault();
    });
    el.addEventListener('click', function (e) {
      if (this.tagName === 'A' && !confirmAction(this.dataset.confirm)) e.preventDefault();
    });
  });
});

/* ── Dashboard Chart.js ── */
function renderDashboardCharts(cursosData, estadosData) {
  const cursoCtx  = document.getElementById('chartCursos');
  const estadoCtx = document.getElementById('chartEstados');

  if (cursoCtx && cursosData && cursosData.length) {
    new Chart(cursoCtx, {
      type: 'bar',
      data: {
        labels: cursosData.map(d => d.nombre),
        datasets: [{
          label: 'Proyectos',
          data:  cursosData.map(d => d.total),
          backgroundColor: cursosData.map(d => d.color || '#2563eb'),
          borderRadius: 6,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: '#e2e8f0' } },
          x: { grid: { display: false } }
        }
      }
    });
  }

  const colorMap = {
    'Aprobado':    '#16a34a',
    'En revisión': '#d97706',
    'Registrado':  '#2563eb',
    'Rechazado':   '#dc2626',
    'Presentado':  '#7c3aed',
  };

  if (estadoCtx && estadosData && estadosData.length) {
    new Chart(estadoCtx, {
      type: 'doughnut',
      data: {
        labels: estadosData.map(d => d.estado),
        datasets: [{
          data: estadosData.map(d => d.total),
          backgroundColor: estadosData.map(d => colorMap[d.estado] || '#94a3b8'),
          borderWidth: 0,
          hoverOffset: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { font: { size: 12 }, padding: 14 }
          }
        },
        cutout: '65%',
      }
    });
  }
}
