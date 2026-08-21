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
 * `data-poll-url="..."` (renderizado automaticamente pelos templates
 * `task_status_badge.html`/`task_status_panel.html`), ou via
 * `options.endpoint` para usar a mesma URL em todos os elementos.
 * `data-poll-interval` no elemento sobrescreve `options.pollInterval` por
 * elemento.
 *
 * Elementos com um `.task-status-panel__message` interno (renderizado por
 * `task_status_panel.html`) recebem, além do badge curto, uma frase
 * completa de status ("Tarefa em processamento há 12s.", "Processamento em
 * 42%.", ...) que é recalculada a cada segundo no cliente — sem round-trip
 * ao servidor — para o relógio de tempo decorrido andar suavemente entre um
 * poll e outro. Customize os textos via `options.messages` (ver
 * `DEFAULT_MESSAGES` abaixo) ou globalmente via `TaskPoll.configure({messages: {...}})`.
 */
(function (global) {
  "use strict";

  // Mapeia elemento em polling -> { intervalId, tickId, lastData }. Permite
  // múltiplas instâncias simultâneas na mesma página sem duplicar polling
  // no mesmo elemento.
  var REGISTRY = new Map();
  var domObserver = null;

  var DEFAULT_MESSAGES = {
    none: "Nenhuma tarefa em andamento.",
    queued: "Tarefa enfileirada.",
    running: "Tarefa em processamento há {time}.",
    progress: "Processamento em {percent}%.",
    success: "Tarefa finalizada com sucesso.",
    failure: "Tarefa finalizada com erro.",
    revoked: "Tarefa cancelada.",
  };

  var globalMessages = DEFAULT_MESSAGES;

  /** Sobrescreve os textos padrão para todas as chamadas futuras de `init()`. */
  function configure(options) {
    if (options && options.messages) {
      globalMessages = mergeMessages(options.messages);
    }
  }

  function mergeMessages(overrides) {
    var merged = {};
    var key;
    for (key in globalMessages) {
      if (Object.prototype.hasOwnProperty.call(globalMessages, key)) {
        merged[key] = globalMessages[key];
      }
    }
    if (overrides) {
      for (key in overrides) {
        if (Object.prototype.hasOwnProperty.call(overrides, key)) {
          merged[key] = overrides[key];
        }
      }
    }
    return merged;
  }

  function resolveConfig(el, options) {
    var endpoint = (options && options.endpoint) || el.getAttribute("data-poll-url");
    var pollInterval =
      parseInt(el.getAttribute("data-poll-interval"), 10) ||
      (options && options.pollInterval) ||
      5000;
    return { endpoint: endpoint, pollInterval: pollInterval };
  }

  /** "125" -> "2min 05s" (compacto, pt-BR). */
  function formatDuration(totalSeconds) {
    totalSeconds = Math.max(0, Math.floor(totalSeconds));
    var hours = Math.floor(totalSeconds / 3600);
    var minutes = Math.floor((totalSeconds % 3600) / 60);
    var seconds = totalSeconds % 60;
    var parts = [];
    if (hours) {
      parts.push(hours + "h");
    }
    if (hours || minutes) {
      parts.push(minutes + "min");
    }
    parts.push(seconds + "s");
    return parts.join(" ");
  }

  /**
   * Monta a frase de status a partir do payload JSON do endpoint de polling.
   * Espelha (propositalmente com o mesmo texto padrão) a função
   * `_compose_status_message` em `models.py`.
   */
  function composeMessage(data, messages) {
    if (!data || !data.status) {
      return messages.none;
    }
    if (data.status === "SUCCESS") {
      return messages.success;
    }
    if (data.status === "FAILURE") {
      return messages.failure;
    }
    if (data.status === "REVOKED") {
      return messages.revoked;
    }
    if (!data.started_at) {
      return messages.queued;
    }
    var elapsedSeconds = (Date.now() - new Date(data.started_at).getTime()) / 1000;
    var message = messages.running.replace("{time}", formatDuration(elapsedSeconds));
    if (data.progress && typeof data.progress.percent === "number") {
      message += " " + messages.progress.replace("{percent}", data.progress.percent);
    }
    return message;
  }

  function applyStatus(el, data) {
    if (!data || !data.status) {
      return;
    }
    el.setAttribute("data-status", data.status);
    el.className = el.className
      .replace(/\btask-status-badge--[a-z]+\b/gi, "")
      .replace(/\btask-status-panel--[a-z]+\b/gi, "")
      .trim();
    var statusClass = data.status.toLowerCase();
    if (el.classList.contains("task-status-badge") || el.querySelector(".task-status-badge__label")) {
      el.classList.add("task-status-badge--" + statusClass);
    }
    if (el.classList.contains("task-status-panel") || el.querySelector(".task-status-panel__message")) {
      el.classList.add("task-status-panel--" + statusClass);
    }

    var label = el.querySelector(".task-status-badge__label");
    if (label && data.status_display) {
      label.textContent = data.status_display;
    }

    if (data.started_at) {
      el.setAttribute("data-started-at", data.started_at);
    } else {
      el.removeAttribute("data-started-at");
    }
  }

  function renderMessage(el, data, messages) {
    var messageEl = el.querySelector(".task-status-panel__message");
    if (messageEl) {
      messageEl.textContent = composeMessage(data, messages);
    }
  }

  function runPoll(el, config, options, messages, entry) {
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
        renderMessage(el, data, messages);
        entry.lastData = data;
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
    var messages = mergeMessages(options && options.messages);

    el.setAttribute(ACTIVE_ATTR, "true");
    var entry = { intervalId: null, tickId: null, lastData: null };
    REGISTRY.set(el, entry);

    function poll() {
      runPoll(el, config, options, messages, entry);
    }
    poll();
    entry.intervalId = global.setInterval(poll, config.pollInterval);

    // Painéis (com `.task-status-panel__message`) ganham um relógio local de
    // 1s para o "há X tempo" andar suavemente entre um poll e outro, sem
    // esperar o próximo `pollInterval` (que costuma ser bem maior que 1s).
    if (el.querySelector(".task-status-panel__message")) {
      entry.tickId = global.setInterval(function () {
        if (entry.lastData && !entry.lastData.is_finished) {
          renderMessage(el, entry.lastData, messages);
        }
      }, 1000);
    }
  }

  /** Para o polling de um elemento específico e libera os intervals. */
  function stop(el) {
    el.removeAttribute(ACTIVE_ATTR);
    var entry = REGISTRY.get(el);
    if (!entry) {
      return;
    }
    global.clearInterval(entry.intervalId);
    if (entry.tickId) {
      global.clearInterval(entry.tickId);
    }
    REGISTRY.delete(el);
  }

  /** Para o polling de todos os elementos atualmente monitorados. */
  function stopAll() {
    REGISTRY.forEach(function (_entry, el) {
      stop(el);
    });
  }

  // Observa remoções no DOM para limpar intervals automaticamente e evitar
  // memory leaks quando um badge/painel é removido (ex.: linha de changelist
  // recarregada via ajax).
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
   * @param {string} selector - Seletor CSS dos badges/painéis a monitorar.
   * @param {Object} [options]
   * @param {string} [options.endpoint] - URL de polling comum a todos os elementos
   *   (ignorado se o elemento já tiver `data-poll-url`).
   * @param {number} [options.pollInterval=5000] - Intervalo em ms.
   * @param {Object} [options.messages] - Sobrescreve os textos padrão (pt-BR) usados
   *   nos painéis — chaves: `none`, `queued`, `running` (usa `{time}`),
   *   `progress` (usa `{percent}`), `success`, `failure`, `revoked`.
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
    configure: configure,
  };

  // Auto-inicialização: qualquer elemento com `data-poll-url` (renderizado
  // pelos templates `task_status_badge.html`/`task_status_panel.html`)
  // começa a ser monitorado assim que a página carrega, sem exigir um
  // `<script>` de inicialização manual. Uma chamada manual a
  // `TaskPoll.init(...)` feita antes deste evento (ex.: via
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
