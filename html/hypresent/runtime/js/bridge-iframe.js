// bridge-iframe.js — ES module; runs INSIDE the iframe
// Pure messaging plumbing. No DOM mutation. Attaches message listener on load.

const SOURCE_TAG = 'hyp';

const dispatchTable = new Map();

// Seed with two test handlers so T4 is verifiable without feature modules.
dispatchTable.set('noop', () => undefined);
dispatchTable.set('ping', () => ({ pong: true }));

export function register(type, handler) {
  dispatchTable.set(type, handler);
}

export function emit(type, payload) {
  window.parent.postMessage(
    { source: SOURCE_TAG, kind: 'event', type, payload },
    location.origin
  );
}

async function handleCommand(data) {
  const handler = dispatchTable.get(data.type);

  if (handler === undefined) {
    window.parent.postMessage(
      {
        source: SOURCE_TAG,
        kind: 'response',
        id: data.id,
        ok: false,
        error: `unknown command: ${data.type}`,
      },
      location.origin
    );
    return;
  }

  try {
    const result = await handler(data.payload);
    window.parent.postMessage(
      {
        source: SOURCE_TAG,
        kind: 'response',
        id: data.id,
        ok: true,
        result,
      },
      location.origin
    );
  } catch (err) {
    window.parent.postMessage(
      {
        source: SOURCE_TAG,
        kind: 'response',
        id: data.id,
        ok: false,
        error: String(err),
      },
      location.origin
    );
  }
}

function onMessage(event) {
  if (event.origin !== location.origin) return;
  if (event.data?.source !== SOURCE_TAG) return;
  if (event.data?.kind !== 'command') return;

  handleCommand(event.data);
}

window.addEventListener('message', onMessage);
