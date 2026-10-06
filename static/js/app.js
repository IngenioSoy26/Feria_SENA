(function () {
  'use strict';

  function getCookie(nombre) {
    if (!document.cookie || document.cookie === '') return null;
    var partes = document.cookie.split(';');
    for (var i = 0; i < partes.length; i++) {
      var par = partes[i].trim();
      if (par.indexOf(nombre + '=') === 0) {
        try {
          return decodeURIComponent(par.substring(nombre.length + 1));
        } catch (e) {
          return par.substring(nombre.length + 1);
        }
      }
    }
    return null;
  }

  window.getCookie = getCookie;
  window.SENA_CSRF_TOKEN = getCookie('csrftoken') || '';

  function fetchSeguro(url, opciones) {
    opciones = opciones || {};
    opciones.headers = opciones.headers || {};
    var metodo = (opciones.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].indexOf(metodo) !== -1) {
      if (!opciones.headers['X-CSRFToken'] && !opciones.headers['X-Csrftoken']) {
        opciones.headers['X-CSRFToken'] = window.SENA_CSRF_TOKEN || getCookie('csrftoken') || '';
      }
      if (!opciones.headers['X-Requested-With']) {
        opciones.headers['X-Requested-With'] = 'XMLHttpRequest';
      }
    }
    return fetch(url, opciones).then(function (respuesta) {
      if (respuesta.status === 403) {
        console.warn('[SENA] Permiso denegado (403) →', url);
      }
      if (respuesta.status === 401) {
        redirect('/accounts/login/?next=' + encodeURIComponent(window.location.pathname));
      }
      return respuesta;
    });
  }

  window.fetchSeguro = fetchSeguro;

  function redirect(url) {
    if (!url) return;
    window.location.href = url;
  }

  window.redirect = redirect;

  function ocultarAlertsAuto() {
    var alerts = document.querySelectorAll('.alert.auto-dismiss');
    for (var i = 0; i < alerts.length; i++) {
      (function (alerta) {
        setTimeout(function () {
          try {
            if (window.bootstrap && bootstrap.Alert) {
              bootstrap.Alert.getOrCreateInstance(alerta).close();
            } else {
              alerta.style.display = 'none';
            }
          } catch (e) {
            alerta.style.display = 'none';
          }
        }, 4500);
      })(alerts[i]);
    }
  }

  function confirmarAccion(mensaje) {
    return window.confirm(mensaje || '¿Estás seguro de realizar esta acción?');
  }

  window.confirmarAccion = confirmarAccion;

  function cargarTooltips() {
    if (window.bootstrap && bootstrap.Tooltip) {
      var elementos = document.querySelectorAll('[data-bs-toggle="tooltip"]');
      for (var i = 0; i < elementos.length; i++) {
        try { bootstrap.Tooltip.getOrCreateInstance(elementos[i]); } catch (e) {}
      }
    }
  }

  function cargarPopovers() {
    if (window.bootstrap && bootstrap.Popover) {
      var elementos = document.querySelectorAll('[data-bs-toggle="popover"]');
      for (var i = 0; i < elementos.length; i++) {
        try { bootstrap.Popover.getOrCreateInstance(elementos[i]); } catch (e) {}
      }
    }
  }

  function bindConfirmLinks() {
    var links = document.querySelectorAll('a[data-confirm], button[data-confirm], form[data-confirm]');
    for (var i = 0; i < links.length; i++) {
      (function (el) {
        var mensaje = el.getAttribute('data-confirm');
        if (el.tagName === 'FORM') {
          el.addEventListener('submit', function (e) {
            if (!confirmarAccion(mensaje)) e.preventDefault();
          });
        } else {
          el.addEventListener('click', function (e) {
            if (!confirmarAccion(mensaje)) {
              e.preventDefault();
              e.stopPropagation();
              return false;
            }
          });
        }
      })(links[i]);
    }
  }

  function inicializar() {
    ocultarAlertsAuto();
    cargarTooltips();
    cargarPopovers();
    bindConfirmLinks();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializar);
  } else {
    inicializar();
  }

  if (typeof window.htmx !== 'undefined') {
    document.body.addEventListener('htmx:afterSwap', function () {
      ocultarAlertsAuto();
      cargarTooltips();
      bindConfirmLinks();
    });
  }

  window.SENA_APP = {
    getCookie: getCookie,
    fetchSeguro: fetchSeguro,
    redirect: redirect,
    confirmarAccion: confirmarAccion,
    inicializar: inicializar
  };
})();
