(function () {
  'use strict';

  function _getFetch() {
    return (typeof window.SENA_APP !== 'undefined' && window.SENA_APP.fetchSeguro)
      ? window.SENA_APP.fetchSeguro
      : (typeof window.fetchSeguro !== 'undefined' ? window.fetchSeguro : fetch);
  }

  function _csrfHeaders() {
    var headers = {};
    var token = '';
    if (typeof window.SENA_CSRF_TOKEN !== 'undefined' && window.SENA_CSRF_TOKEN) {
      token = window.SENA_CSRF_TOKEN;
    } else if (typeof window.SENA_APP !== 'undefined' && window.SENA_APP.getCookie) {
      token = window.SENA_APP.getCookie('csrftoken') || '';
    } else if (typeof window.getCookie !== 'undefined') {
      token = window.getCookie('csrftoken') || '';
    } else {
      try {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        if (match) token = decodeURIComponent(match[1]);
      } catch (e) { token = ''; }
    }
    if (token) headers['X-CSRFToken'] = token;
    headers['X-Requested-With'] = 'XMLHttpRequest';
    headers['Content-Type'] = 'application/json';
    return headers;
  }

  function LectorQRSena(modo, endpointValidar, endpointRegistrar) {
    var self = this;
    self.modo = modo || 'ASISTENCIA';
    self.endpointValidar = endpointValidar || '';
    self.endpointRegistrar = endpointRegistrar || '';
    self.elementoLectorId = 'reader';
    self.btnActivarId = 'btn-activar-camara';
    self.btnDetenerId = 'btn-detener-camara';
    self.datosExtra = {};
    self.html5QrCode = null;
    self.scanActivo = false;
    self.procesando = false;
    self.ultimoEscaneado = '';
    self.ultimoEscaneo = 0;
    self.umbralDedupeMs = 2500;
    self.reanudarAutomatico = true;
    self.tiempoPanelMs = 1500;

    self.onValidacion = null;
    self.onAntesRegistrar = null;
    self.onResultado = null;
    self.onError = null;
    self.onActivacion = null;
    self.onDesactivacion = null;
  }

  LectorQRSena.prototype._disponibleHtml5Qr = function () {
    return typeof window.Html5Qrcode !== 'undefined';
  };

  LectorQRSena.prototype._cargarLibreria = function (callback) {
    var self = this;
    if (self._disponibleHtml5Qr()) {
      if (callback) callback(true);
      return;
    }
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js';
    script.crossOrigin = 'anonymous';
    script.onload = function () {
      if (self._disponibleHtml5Qr()) {
        if (callback) callback(true);
      } else {
        self._cargarLibreriaFallback(function (ok) {
          if (callback) callback(ok);
        });
      }
    };
    script.onerror = function () {
      self._cargarLibreriaFallback(function (ok) {
        if (callback) callback(ok);
      });
    };
    document.head.appendChild(script);
  };

  LectorQRSena.prototype._cargarLibreriaFallback = function (callback) {
    var self = this;
    if (self._disponibleHtml5Qr()) {
      if (callback) callback(true);
      return;
    }
    try {
      var staticUrl = (typeof window.STATIC_URL !== 'undefined')
        ? window.STATIC_URL
        : '/static/';
      var script = document.createElement('script');
      script.src = staticUrl + 'js/html5-qrcode.min.js';
      script.onload = function () {
        if (callback) callback(self._disponibleHtml5Qr());
      };
      script.onerror = function () {
        console.error('[LectorQRSena] No se pudo cargar html5-qrcode desde CDN ni desde static.');
        if (callback) callback(false);
      };
      document.head.appendChild(script);
    } catch (e) {
      console.error('[LectorQRSena] Excepción cargando librería QR:', e);
      if (callback) callback(false);
    }
  };

  LectorQRSena.prototype._obtenerElementos = function () {
    var el = {
      lector: document.getElementById(this.elementoLectorId),
      btnActivar: document.getElementById(this.btnActivarId),
      btnDetener: document.getElementById(this.btnDetenerId),
    };
    return el;
  };

  LectorQRSena.prototype._mostrarBoton = function (btn, mostrar) {
    if (!btn) return;
    if (mostrar) btn.classList.remove('d-none');
    else btn.classList.add('d-none');
  };

  LectorQRSena.prototype.inicializar = function () {
    var self = this;
    var el = self._obtenerElementos();
    if (!el.btnActivar) {
      console.warn('[LectorQRSena] Botón de activación no encontrado:', self.btnActivarId);
      return;
    }
    self._cargarLibreria(function (disponible) {
      if (!disponible) {
        if (self.onError) self.onError('Lector QR no disponible en este navegador.', null);
        el.btnActivar.disabled = true;
        el.btnActivar.innerHTML = '<span>Lector QR no disponible</span>';
        return;
      }
      self._bindBotones();
    });
  };

  LectorQRSena.prototype._bindBotones = function () {
    var self = this;
    var el = self._obtenerElementos();
    if (el.btnActivar) {
      el.btnActivar.addEventListener('click', function () {
        self.activarCamara();
      });
    }
    if (el.btnDetener) {
      el.btnDetener.addEventListener('click', function () {
        self.detenerCamara();
      });
    }
  };

  LectorQRSena.prototype.activarCamara = function () {
    var self = this;
    var el = self._obtenerElementos();

    if (self.scanActivo) return;
    if (!self._disponibleHtml5Qr()) {
      self._cargarLibreria(function (ok) {
        if (ok) self.activarCamara();
      });
      return;
    }

    if (!self.html5QrCode) {
      try {
        self.html5QrCode = new window.Html5Qrcode(self.elementoLectorId, {
          formatsToSupport: [window.Html5QrcodeSupportedFormats.QR_CODE],
          verbose: false,
        });
      } catch (e) {
        if (self.onError) self.onError('Error inicializando cámara: ' + e.message, e);
        return;
      }
    }

    var config = {
      fps: 10,
      qrbox: function (viewfinderWidth, viewfinderHeight) {
        var min = Math.min(viewfinderWidth, viewfinderHeight);
        var tam = Math.floor(min * 0.8);
        return { width: tam, height: tam };
      },
      aspectRatio: 1.0,
      experimentalFeatures: { useBarCodeDetectorIfSupported: true },
      rememberLastUsedCamera: true,
      showTorchButtonIfSupported: true,
      showZoomSliderIfSupported: true,
    };

    self.html5QrCode.start(
      { facingMode: 'environment' },
      config,
      function (decodedText) {
        self._onScanSuccess(decodedText);
      },
      function () {}
    ).then(function () {
      self.scanActivo = true;
      if (el.btnActivar) el.btnActivar.classList.add('d-none');
      if (el.btnDetener) el.btnDetener.classList.remove('d-none');
      if (self.onActivacion) self.onActivacion();
    }).catch(function (err) {
      self.scanActivo = false;
      console.error('[LectorQRSena] Error activando cámara:', err);
      if (self.onError) {
        var msg = 'No se pudo activar la cámara. Verifica permisos.';
        if (err && err.message) msg += ' (' + err.message + ')';
        self.onError(msg, err);
      }
      if (el.btnActivar) el.btnActivar.classList.remove('d-none');
      if (el.btnDetener) el.btnDetener.classList.add('d-none');
    });
  };

  LectorQRSena.prototype.detenerCamara = function () {
    var self = this;
    var el = self._obtenerElementos();
    if (!self.html5QrCode) {
      self.scanActivo = false;
      return Promise.resolve();
    }
    if (!self.scanActivo) return Promise.resolve();

    return self.html5QrCode.stop().then(function () {
      self.scanActivo = false;
      return self.html5QrCode.clear();
    }).then(function () {
      if (el.btnActivar) el.btnActivar.classList.remove('d-none');
      if (el.btnDetener) el.btnDetener.classList.add('d-none');
      if (self.onDesactivacion) self.onDesactivacion();
    }).catch(function (err) {
      self.scanActivo = false;
      console.warn('[LectorQRSena] Error deteniendo cámara:', err);
      if (el.btnActivar && el.btnActivar.classList.contains('d-none')) {
        el.btnActivar.classList.remove('d-none');
      }
      if (el.btnDetener) el.btnDetener.classList.add('d-none');
    });
  };

  LectorQRSena.prototype._pausarEscaneo = function () {
    var self = this;
    if (self.html5QrCode && self.scanActivo) {
      try {
        self.html5QrCode.pause();
      } catch (e) {}
    }
  };

  LectorQRSena.prototype._reanudarEscaneo = function () {
    var self = this;
    if (self.html5QrCode && self.scanActivo) {
      try {
        self.html5QrCode.resume();
      } catch (e) {}
    }
  };

  LectorQRSena.prototype._onScanSuccess = function (decodedText) {
    var self = this;
    var ahora = Date.now();
    var tokenLimpio = (decodedText || '').toString().trim();

    if (!tokenLimpio) return;
    if (self.procesando) return;
    if (self.ultimoEscaneado === tokenLimpio && (ahora - self.ultimoEscaneo) < self.umbralDedupeMs) {
      return;
    }
    self.ultimoEscaneado = tokenLimpio;
    self.ultimoEscaneo = ahora;
    self.procesando = true;
    self._pausarEscaneo();

    var payloadValidar = { token: tokenLimpio };
    if (self.datosExtra && typeof self.datosExtra === 'object') {
      Object.keys(self.datosExtra).forEach(function (k) {
        if (!(k in payloadValidar)) payloadValidar[k] = self.datosExtra[k];
      });
    }

    var fetchFn = _getFetch();
    var headers = _csrfHeaders();

    Promise.resolve()
      .then(function () {
        if (self.onValidacion && typeof self.onValidacion === 'function') {
          return fetchFn(self.endpointValidar, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payloadValidar),
          }).then(function (resp) {
            return resp.json().then(function (json) {
              var pasa = self.onValidacion(json);
              return { pasa: pasa, respuesta: json };
            });
          });
        }
        return { pasa: true, respuesta: null };
      })
      .then(function (validacion) {
        if (!validacion.pasa) {
          if (self.onResultado && validacion.respuesta) {
            self.onResultado(validacion.respuesta);
          } else if (self.onError) {
            self.onError((validacion.respuesta && validacion.respuesta.mensaje) || 'Validación fallida', validacion.respuesta);
          }
          return;
        }

        var payloadRegistrar = { token: tokenLimpio };
        if (self.onAntesRegistrar && typeof self.onAntesRegistrar === 'function') {
          var customPayload = self.onAntesRegistrar(tokenLimpio);
          if (customPayload && typeof customPayload === 'object') {
            payloadRegistrar = customPayload;
          }
        }

        return fetchFn(self.endpointRegistrar, {
          method: 'POST',
          headers: _csrfHeaders(),
          body: JSON.stringify(payloadRegistrar),
        }).then(function (resp) {
          if (resp.status === 401) {
            if (typeof window.SENA_APP !== 'undefined' && window.SENA_APP.redirect) {
              window.SENA_APP.redirect('/accounts/login/?next=' + encodeURIComponent(window.location.pathname));
            } else {
              window.location.href = '/accounts/login/?next=' + encodeURIComponent(window.location.pathname);
            }
            return null;
          }
          return resp.json();
        }).then(function (resultado) {
          if (!resultado) return;
          if (self.onResultado) self.onResultado(resultado);
        });
      })
      .catch(function (err) {
        console.error('[LectorQRSena] Error procesando QR:', err);
        if (self.onError) {
          self.onError('Error de conexión al procesar el código QR.', err);
        }
      })
      .finally(function () {
        self.procesando = false;
        if (self.reanudarAutomatico) {
          setTimeout(function () {
            self._reanudarEscaneo();
          }, self.tiempoPanelMs);
        }
      });
  };

  window.LectorQRSena = LectorQRSena;
})();
