(function () {
    'use strict';

    const KPIS = [
        'participantes_registrados',
        'aprendices',
        'instructores',
        'invitados',
        'proyectos',
        'instituciones',
        'programas_tecnicos',
        'asistentes',
        'ausentes',
        'porcentaje_asistencia',
        'refrigerios_entregados',
        'refrigerios_pendientes',
        'porcentaje_refrigerios',
        'certificados_entregados',
        'certificados_pendientes',
        'porcentaje_certificados',
        'operadores_conectados',
    ];

    const TIPOS_GRAFICOS = [
        'participantes_x_institucion',
        'participantes_x_programa',
        'proyectos_x_institucion',
        'proyectos_x_programa',
        'participantes_x_proyecto',
        'participantes_x_instructor',
        'distribucion_tipo_persona',
        'asistencia_general',
        'asistencia_x_institucion',
        'asistencia_x_programa',
        'refrigerios_x_tipo',
        'certificados_tiempo',
    ];

    const GRAFICOS_HORIZONTALES = ['participantes_x_proyecto', 'participantes_x_instructor'];
    const GRAFICOS_APILADOS = ['asistencia_x_institucion', 'asistencia_x_programa'];

    const MAX_RETRIES_CHART = 200;
    let retriesChart = 0;
    let appIniciada = false;

    let instanciasGraficos = {};

    function logInfo(msg) {
        try { console.info('[DASHBOARD-SENA]', msg); } catch (e) {}
    }

    function logWarn(msg) {
        try { console.warn('[DASHBOARD-SENA]', msg); } catch (e) {}
    }

    function logError(msg, err) {
        try { console.error('[DASHBOARD-SENA]', msg, err || ''); } catch (e) {}
    }

    function getQueryString() {
        const params = new URLSearchParams(window.location.search);
        return params.toString() ? '?' + params.toString() : '';
    }

    function formatNumber(n) {
        if (n === null || n === undefined || isNaN(n)) return '0';
        if (typeof n === 'number' && !Number.isInteger(n)) {
            return n.toLocaleString('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%';
        }
        return Number(n).toLocaleString('es-CO');
    }

    function aplicarKpis(kpis) {
        for (const k of KPIS) {
            if (kpis[k] === undefined) continue;
            const el = document.getElementById('kpi-' + k);
            if (el) {
                if (k.startsWith('porcentaje_')) {
                    el.textContent = formatNumber(kpis[k]) + (String(kpis[k]).includes('%') ? '' : '%');
                } else {
                    el.textContent = formatNumber(kpis[k]);
                }
            }
        }
        const refPend = document.getElementById('kpi-refrigerios_pendientes_label');
        if (refPend) {
            refPend.textContent = 'Pendientes: ' + formatNumber(kpis.refrigerios_pendientes || 0);
        }
        const lbl = document.getElementById('evento-actual-label');
        if (lbl && kpis.evento_nombre) {
            lbl.textContent = 'Evento: ' + kpis.evento_nombre;
        }
    }

    function cargarKpis() {
        logInfo('Cargando KPIs...');
        return fetch('/dashboard/api/kpis/' + getQueryString(), {
            method: 'GET',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin',
        })
            .then(function (r) { return r.ok ? r.json() : Promise.reject('HTTP ' + r.status); })
            .then(function (res) {
                if (res && res.ok && res.kpis) {
                    aplicarKpis(res.kpis);
                    logInfo('KPIs actualizados OK');
                } else {
                    logWarn('Respuesta KPIs vacía o invalida');
                }
                return res;
            })
            .catch(function (err) {
                logError('Error cargando KPIs:', err);
            });
    }

    function crearOpcionesChart(tipo) {
        const base = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 600 },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: { font: { family: "'Work Sans', sans-serif", size: 11 } },
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.85)',
                    titleFont: { family: "'Work Sans', sans-serif" },
                    bodyFont: { family: "'Work Sans', sans-serif" },
                    padding: 10,
                },
            },
            scales: {},
        };

        const tiposEscala = ['participantes_x_institucion', 'participantes_x_programa',
            'proyectos_x_institucion', 'proyectos_x_programa',
            'participantes_x_proyecto', 'participantes_x_instructor',
            'asistencia_x_institucion', 'asistencia_x_programa',
            'refrigerios_x_tipo'];

        if (tiposEscala.includes(tipo)) {
            if (GRAFICOS_HORIZONTALES.includes(tipo)) {
                base.indexAxis = 'y';
                base.scales.x = { beginAtZero: true, ticks: { precision: 0 } };
                base.scales.y = { ticks: { autoSkip: false, font: { size: 10 } } };
            } else {
                base.scales.y = { beginAtZero: true, ticks: { precision: 0 } };
                base.scales.x = { ticks: { autoSkip: true, maxRotation: 45, minRotation: 0, font: { size: 10 } } };
            }
            if (GRAFICOS_APILADOS.includes(tipo)) {
                base.scales.x.stacked = true;
                base.scales.y.stacked = true;
            }
        }

        if (tipo === 'refrigerios_x_tipo') {
            if (!base.scales.y) base.scales.y = {};
            base.scales.y.beginAtZero = true;
        }

        if (tipo === 'certificados_tiempo') {
            base.scales = {
                y: { beginAtZero: true, ticks: { precision: 0 } },
                x: { ticks: { font: { size: 10 } } },
            };
            base.elements = {
                line: { tension: 0.3, fill: true, borderWidth: 2 },
                point: { radius: 3, hoverRadius: 5 },
            };
        }

        if (tipo === 'distribucion_tipo_persona' || tipo === 'asistencia_general') {
            base.plugins.legend.position = 'bottom';
            base.cutout = tipo === 'distribucion_tipo_persona' ? '55%' : '0%';
        }

        return base;
    }

    function instanciarGrafico(idCanvas, payload, reintentos) {
        const canvas = document.getElementById(idCanvas);
        if (!canvas || !payload) return;
        if (reintentos === undefined) reintentos = 0;

        if (typeof window.Chart !== 'function') {
            if (reintentos >= 60) {
                logError('instanciarGrafico abortó después de 60 reintentos: Chart is not defined para', idCanvas);
                return;
            }
            setTimeout(function () { instanciarGrafico(idCanvas, payload, reintentos + 1); }, 120);
            return;
        }

        try {
            if (instanciasGraficos[idCanvas]) {
                instanciasGraficos[idCanvas].destroy();
                instanciasGraficos[idCanvas] = null;
            }

            const ctx = canvas.getContext('2d');
            const tipo = payload.type || 'bar';

            const data = {
                labels: payload.labels || [],
                datasets: (payload.datasets || []).map(function (ds) {
                    return Object.assign({}, ds, {
                        borderRadius: tipo === 'bar' ? 4 : 0,
                        borderSkipped: tipo === 'bar' ? false : undefined,
                    });
                }),
            };

            instanciasGraficos[idCanvas] = new Chart(ctx, {
                type: tipo,
                data: data,
                options: crearOpcionesChart(tipo),
            });
        } catch (err) {
            logError('Excepción en new Chart para canvas ' + idCanvas, err);
        }
    }

    function grafico(idCanvas, tipo) {
        if (typeof window.Chart !== 'function') {
            logInfo('Chart aún no cargado, difiriendo fetch de gráfico ' + tipo);
            setTimeout(function () { grafico(idCanvas, tipo); }, 150);
            return Promise.resolve(null);
        }
        const params = new URLSearchParams(window.location.search);
        params.append('tipo', tipo);
        const qs = '?' + params.toString();

        return fetch('/dashboard/api/graficos/' + qs, {
            method: 'GET',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin',
        })
            .then(function (r) { return r.ok ? r.json() : Promise.reject('HTTP ' + r.status); })
            .then(function (res) {
                if (res && res.ok && res.graficos && res.graficos[tipo]) {
                    instanciarGrafico(idCanvas, res.graficos[tipo]);
                }
                return res;
            })
            .catch(function (err) {
                logError('Error cargando gráfico ' + tipo + ' (fetch):', err);
            });
    }

    function cargarTodosGraficos() {
        logInfo('Cargando ' + TIPOS_GRAFICOS.length + ' gráficos...');
        const promesas = TIPOS_GRAFICOS.map(function (t) { return grafico('chart-' + t, t); });
        return Promise.all(promesas).then(function () { logInfo('Gráficos programados OK'); });
    }

    function actualizarTodo() {
        return Promise.all([cargarKpis(), cargarTodosGraficos()]);
    }

    function onFiltroChange() {
        const selects = document.querySelectorAll('.filtro-select');
        const params = new URLSearchParams();
        selects.forEach(function (s) { if (s.value) params.set(s.name, s.value); });
        const nuevo = params.toString();
        const actual = new URLSearchParams(window.location.search).toString();
        if (nuevo !== actual) {
            const url = window.location.pathname + (nuevo ? '?' + nuevo : '');
            window.history.replaceState({}, '', url);
        }
        actualizarTodo();
    }

    function limpiarFiltros() {
        const selects = document.querySelectorAll('.filtro-select');
        selects.forEach(function (s) { s.value = ''; });
        window.history.replaceState({}, '', window.location.pathname);
        actualizarTodo();
    }

    function iniciarApp() {
        appIniciada = true;
        logInfo('App iniciada OK; chart disponible? -> ' + (typeof window.Chart === 'function'));
        actualizarTodo().then(function () {
            logInfo('Actualización inicial completada');
        });

        setInterval(cargarKpis, 30000);
        setInterval(cargarTodosGraficos, 60000);

        const btnActualizar = document.getElementById('btn-actualizar');
        if (btnActualizar) {
            btnActualizar.addEventListener('click', function (ev) {
                ev.preventDefault();
                const btn = ev.currentTarget;
                const textoOriginal = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = '<i class="bi bi-arrow-clockwise me-2"></i>Actualizando...';
                actualizarTodo().finally(function () {
                    btn.disabled = false;
                    btn.innerHTML = textoOriginal;
                });
            });
        }

        const filtros = document.querySelectorAll('.filtro-select');
        filtros.forEach(function (s) { s.addEventListener('change', onFiltroChange); });

        const btnLimpiar = document.getElementById('btn-limpiar-filtros');
        if (btnLimpiar) {
            btnLimpiar.addEventListener('click', function (ev) {
                ev.preventDefault();
                limpiarFiltros();
            });
        }
    }

    function esperarChart() {
        retriesChart++;
        if (typeof window.Chart === 'function') {
            logInfo('Chart.js listo después de ' + retriesChart + ' chequeos');
            iniciarApp();
            return;
        }
        if (window.__SENA_CHART_READY__ === true) {
            logInfo('SENA_CHART_READY flag=true, iniciando app');
            iniciarApp();
            return;
        }
        if (retriesChart >= MAX_RETRIES_CHART) {
            logError('Chart.js NUNCA se cargó después de ' + MAX_RETRIES_CHART + ' intentos (30s). Revisa CDN https://cdn.jsdelivr.net/npm/chart.js@4.4.4/ o la política CSP/CORS');
            const placeholders = document.querySelectorAll('canvas[id^="chart-"]');
            placeholders.forEach(function (c) {
                try {
                    const wrapper = c.parentNode;
                    const div = document.createElement('div');
                    div.className = 'alert alert-warning small m-2';
                    div.innerHTML = '⚠ <b>Chart.js no disponible</b><br>No se pudo descargar desde CDN. Revisa conexión a internet o CSP del navegador.';
                    wrapper.insertBefore(div, c);
                } catch (e) {}
            });
            return;
        }
        setTimeout(esperarChart, 150);
    }

    document.addEventListener('SENA_CHART_READY', function () {
        logInfo('Evento SENA_CHART_READY recibido');
        if (!appIniciada) iniciarApp();
    });
    document.addEventListener('SENA_CHART_FAILED', function () {
        logError('Evento SENA_CHART_FAILED recibido');
        if (!appIniciada) esperarChart();
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', esperarChart);
    } else {
        esperarChart();
    }

    window.Dashboard = {
        cargar_kpis: cargarKpis,
        grafico: grafico,
        actualizarTodo: actualizarTodo,
    };
})();
