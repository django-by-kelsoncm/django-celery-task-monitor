/**
 * TaskPoll — polling de status de tarefas Celery para django-celery-task-monitor.
 *
 * Auto-contido, sem dependências externas. Uso:
 *
 *   <script src="{% static 'django_celery_task_monitor/js/task-poll.js' %}"></script>
 *   <script>
 *     TaskPoll.init('.task-status-badge', {
 *       pollInterval: 5000,
 *       onSuccess: function (data, el) { console.log('Task concluída!', data); },
 *       onError: function (data, el) { console.warn('Task falhou', data); },
 *     });
 *   </script>
 *
 * Cada elemento casado por `selector` deve expor a URL de polling via
 * `data-poll-url="..."` (renderizado automaticamente pelo template
 * `task_status_badge.html`), ou via `options.endpoint` para usar a mesma URL
 * em todos os elementos. `data-poll-interval` no elemento sobrescreve
 * `options.pollInterval` por elemento.
 */
(function (global) {
  "use strict";

  // Mapeia elemento em polling -> { intervalId }. Permite múltiplas instâncias
  // simultâneas na mesma página sem duplicar polling no mesmo elemento.
  var REGISTRY = new Map();
  var domObserver = null;

  function resolveConfig(el, options) {
    var endpoint = (options && options.endpoint) || el.getAttribute("data-poll-url");
    var pollInterval =
      parseInt(el.getAttribute("data-poll-interval"), 10) ||
      (options && options.pollInterval) ||
      5000;
    return { endpoint: endpoint, pollInterval: pollInterval };
  }

  function applyStatus(el, data) {
    if (!data || !data.status) {
      return;
    }
    el.setAttribute("data-status", data.status);
    el.className = el.className.replace(/\btask-status-badge--[a-z]+\b/gi, "").trim();
    el.classList.add("task-status-badge--" + data.status.toLowerCase());

    var label = el.querySelector(".task-status-badge__label");
    if (label && data.status_display) {
      label.textContent = data.status_display;
    }
  }

  function runPoll(el, config, options) {
    if (!config.endpoint) {
      return;
    }
    global
      .fetch(config.endpoint, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        applyStatus(el, data);
        if (options && typeof options.onUpdate === "function") {
          options.onUpdate(data, el);
        }
        if (data.is_finished) {
          stop(el);
          if (data.status === "SUCCESS") {
            if (options && typeof options.onSuccess === "function") {
              options.onSuccess(data, el);
            }
          } else if (options && typeof options.onError === "function") {
            options.onError(data, el);
          }
        }
      })
      .catch(function (error) {
        if (options && typeof options.onError === "function") {
          options.onError({ error: String(error) }, el);
        }
      });
  }

  // Marca o elemento como "em polling" via atributo no próprio DOM (e não só
  // no Map acima). Isso é essencial porque, se este script for avaliado mais
  // de uma vez na mesma página (ex.: HTML inserido novamente via AJAX, ou o
  // navegador reexecutando o script por qualquer motivo), cada execução cria
  // um Map novo e isolado — só um atributo persistido no elemento é visível
  // entre execuções distintas, evitando polling duplicado do mesmo badge.
  var ACTIVE_ATTR = "data-task-poll-active";

  /** Inicia (ou reaproveita) o polling de um único elemento. */
  function start(el, options) {
    if (el.hasAttribute(ACTIVE_ATTR) || REGISTRY.has(el)) {
      return;
    }
    var config = resolveConfig(el, options);
    if (!config.endpoint) {
      return;
    }

    el.setAttribute(ACTIVE_ATTR, "true");
    runPoll(el, config, options);
    var intervalId = global.setInterval(function () {
      runPoll(el, config, options);
    }, config.pollInterval);

    REGISTRY.set(el, { intervalId: intervalId });
  }

  /** Para o polling de um elemento específico e libera o interval. */
  function stop(el) {
    el.removeAttribute(ACTIVE_ATTR);
    var entry = REGISTRY.get(el);
    if (!entry) {
      return;
    }
    global.clearInterval(entry.intervalId);
    REGISTRY.delete(el);
  }

  /** Para o polling de todos os elementos atualmente monitorados. */
  function stopAll() {
    REGISTRY.forEach(function (_entry, el) {
      stop(el);
    });
  }

  // Observa remoções no DOM para limpar intervals automaticamente e evitar
  // memory leaks quando um badge é removido (ex.: linha de changelist recarregada via ajax).
  function ensureCleanupObserver() {
    if (domObserver || typeof MutationObserver === "undefined") {
      return;
    }
    domObserver = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        mutation.removedNodes.forEach(function (node) {
          if (!node || node.nodeType !== 1) {
            return;
          }
          if (REGISTRY.has(node)) {
            stop(node);
          }
          if (typeof node.querySelectorAll === "function") {
            node.querySelectorAll("*").forEach(function (child) {
              if (REGISTRY.has(child)) {
                stop(child);
              }
            });
          }
        });
      });
    });
    domObserver.observe(document.body, { childList: true, subtree: true });
  }

  /**
   * Inicia o polling para todos os elementos que casam com `selector`.
   *
   * @param {string} selector - Seletor CSS dos badges a monitorar.
   * @param {Object} [options]
   * @param {string} [options.endpoint] - URL de polling comum a todos os elementos
   *   (ignorado se o elemento já tiver `data-poll-url`).
   * @param {number} [options.pollInterval=5000] - Intervalo em ms.
   * @param {function} [options.onUpdate] - Chamado a cada resposta recebida.
   * @param {function} [options.onSuccess] - Chamado quando a tarefa terminar com sucesso.
   * @param {function} [options.onError] - Chamado quando a tarefa falhar ou o fetch der erro.
   * @returns {{stop: function}} Controlador para parar manualmente esta chamada de init.
   */
  function init(selector, options) {
    ensureCleanupObserver();
    var elements = Array.prototype.slice.call(document.querySelectorAll(selector));
    elements.forEach(function (el) {
      start(el, options);
    });
    return {
      stop: function () {
        elements.forEach(function (el) {
          stop(el);
        });
      },
    };
  }

  global.TaskPoll = {
    init: init,
    stop: stop,
    stopAll: stopAll,
  };

  // Auto-inicialização: qualquer elemento com `data-poll-url` (renderizado
  // pelo template `task_status_badge.html`) começa a ser monitorado assim que
  // a página carrega, sem exigir um `<script>` de inicialização manual. Uma
  // chamada manual a `TaskPoll.init(...)` feita antes deste evento (ex.: via
  // `{% task_poll_script %}`) continua tendo prioridade — elementos já
  // registrados não são reiniciados (ver `start()` acima).
  if (typeof document !== "undefined") {
    var autoInit = function () {
      init("[data-poll-url]");
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", autoInit);
    } else {
      autoInit();
    }
  }
})(typeof window !== "undefined" ? window : this);
