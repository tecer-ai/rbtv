// bridge-parent.js — ES module; runs in PARENT window
// Pure messaging plumbing. No DOM mutation except message listener attachment.

const SOURCE_TAG = 'hyp';

export function createBridge(iframe) {
  if (!iframe || !iframe.contentWindow) {
    throw new TypeError('createBridge requires a valid iframe element');
  }

  const pending = new Map(); // id -> { resolve, reject, timer }
  const eventHandlers = new Map(); // type -> Set<handler>
  let idCounter = 0;

  function nextId() {
    idCounter += 1;
    return `${SOURCE_TAG}-${idCounter}-${Date.now()}`;
  }

  function postCommandEnvelope(id, type, payload) {
    iframe.contentWindow.postMessage(
      { source: SOURCE_TAG, kind: 'command', id, type, payload },
      location.origin
    );
  }

  function command(type, payload, timeoutMs = 10000) {
    return new Promise((resolve, reject) => {
      const id = nextId();
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`bridge command '${type}' timed out after ${timeoutMs}ms`));
      }, timeoutMs);

      pending.set(id, { resolve, reject, timer });
      postCommandEnvelope(id, type, payload);
    });
  }

  function on(type, handler) {
    if (typeof handler !== 'function') {
      throw new TypeError('handler must be a function');
    }
    if (!eventHandlers.has(type)) {
      eventHandlers.set(type, new Set());
    }
    eventHandlers.get(type).add(handler);

    return function unsubscribe() {
      off(type, handler);
    };
  }

  function off(type, handler) {
    const handlers = eventHandlers.get(type);
    if (handlers) {
      handlers.delete(handler);
      if (handlers.size === 0) {
        eventHandlers.delete(type);
      }
    }
  }

  function handleResponse(data) {
    const entry = pending.get(data.id);
    if (!entry) return;

    clearTimeout(entry.timer);
    pending.delete(data.id);

    if (data.ok) {
      entry.resolve(data.result);
    } else {
      entry.reject(new Error(data.error || 'bridge command failed'));
    }
  }

  function handleEvent(data) {
    const handlers = eventHandlers.get(data.type);
    if (!handlers) return;
    for (const handler of handlers) {
      try {
        handler(data.payload);
      } catch (err) {
        // Prevent one handler error from breaking others.
      }
    }
  }

  function onMessage(event) {
    if (event.origin !== location.origin) return;
    if (event.data?.source !== SOURCE_TAG) return;

    if (event.data.kind === 'response') {
      handleResponse(event.data);
    } else if (event.data.kind === 'event') {
      handleEvent(event.data);
    }
  }

  window.addEventListener('message', onMessage);

  function destroy() {
    window.removeEventListener('message', onMessage);
    for (const entry of pending.values()) {
      clearTimeout(entry.timer);
      entry.reject(new Error('bridge destroyed'));
    }
    pending.clear();
    eventHandlers.clear();
  }

  return {
    command,
    on,
    off,
    destroy,
  };
}
