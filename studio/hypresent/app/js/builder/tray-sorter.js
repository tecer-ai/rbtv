// tray-sorter.js — hand-rolled pointer-events reorder (D4-S4)
// Only pointer* + keydown + rAF + getBoundingClientRect. No native DnD API.

export function attachSorter(listEl, { onReorder, onDomChange }) {
  listEl.style.touchAction = 'none';

  let draggedRow = null;
  let startIndex = -1;
  let preDragOrder = [];
  let pointerId = null;
  let movePending = false;
  let lastClientY = 0;
  let keydownHandler = null;
  let cancelled = false;
  let grabOffsetY = 0;   // pointer offset inside the row at grab time
  let translateY = 0;    // transform currently applied to the dragged row

  function getRowOrder() {
    return Array.from(listEl.children)
      .filter(li => li.classList.contains('tray-row'))
      .map(li => li.dataset.uid);
  }

  function restorePreDragOrder() {
    const currentMap = new Map();
    Array.from(listEl.children).forEach(li => {
      if (li.classList.contains('tray-row')) {
        currentMap.set(li.dataset.uid, li);
      }
    });
    preDragOrder.forEach(uid => {
      const li = currentMap.get(uid);
      if (li) listEl.appendChild(li);
    });
    if (onDomChange) onDomChange();
  }

  function cleanup() {
    if (keydownHandler) {
      document.removeEventListener('keydown', keydownHandler);
      keydownHandler = null;
    }
    if (draggedRow) {
      draggedRow.classList.remove('tray-drag-ghost');
      draggedRow.style.transform = '';
      if (pointerId !== null) {
        try {
          draggedRow.releasePointerCapture(pointerId);
        } catch (_e) {
          // ignore
        }
      }
    }
    draggedRow = null;
    startIndex = -1;
    preDragOrder = [];
    pointerId = null;
    movePending = false;
    lastClientY = 0;
    cancelled = false;
    grabOffsetY = 0;
    translateY = 0;
  }

  function onPointerDown(e) {
    const removeBtn = e.target.closest('.tray-remove');
    const dupBtn = e.target.closest('.tray-duplicate');
    if (removeBtn || dupBtn) return;

    const row = e.target.closest('.tray-row');
    if (!row || row.parentElement !== listEl) return;

    // Prevent default to avoid text selection / native scrolling
    e.preventDefault();

    draggedRow = row;
    startIndex = Array.from(listEl.children).filter(li => li.classList.contains('tray-row')).indexOf(row);
    preDragOrder = getRowOrder();
    pointerId = e.pointerId;
    cancelled = false;
    grabOffsetY = e.clientY - row.getBoundingClientRect().top;
    translateY = 0;

    row.setPointerCapture(e.pointerId);
    row.classList.add('tray-drag-ghost');
    lastClientY = e.clientY;

    keydownHandler = (ev) => {
      if (ev.key === 'Escape') {
        ev.preventDefault();
        cancelled = true;
        restorePreDragOrder();
        cleanup();
      }
    };
    document.addEventListener('keydown', keydownHandler);
  }

  function findInsertionIndex(clientY) {
    const siblings = Array.from(listEl.children).filter(li => li.classList.contains('tray-row') && li !== draggedRow);
    for (let i = 0; i < siblings.length; i++) {
      const rect = siblings[i].getBoundingClientRect();
      const mid = rect.top + rect.height / 2;
      if (clientY < mid) {
        return i;
      }
    }
    return siblings.length;
  }

  function moveDraggedRow() {
    if (!draggedRow || cancelled) return;
    const others = Array.from(listEl.children).filter(li => li.classList.contains('tray-row') && li !== draggedRow);
    const targetIndex = findInsertionIndex(lastClientY);
    const referenceNode = others[targetIndex] || null;
    if (referenceNode !== draggedRow.nextSibling) {
      listEl.insertBefore(draggedRow, referenceNode);
      if (onDomChange) onDomChange();
    }
  }

  // Keep the ghost under the pointer. getBoundingClientRect() includes the
  // currently applied transform, so subtract it to recover the layout top —
  // computing from the raw rect (the old code) feeds the transform back into
  // itself and the ghost drifts away from the cursor.
  function applyGhostTransform() {
    if (!draggedRow) return;
    const layoutTop = draggedRow.getBoundingClientRect().top - translateY;
    translateY = (lastClientY - grabOffsetY) - layoutTop;
    draggedRow.style.transform = `translateY(${Math.round(translateY)}px)`;
  }

  function onPointerMove(e) {
    if (!draggedRow || cancelled) return;
    e.preventDefault();
    lastClientY = e.clientY;

    if (!movePending) {
      movePending = true;
      requestAnimationFrame(() => {
        movePending = false;
        if (draggedRow && !cancelled) {
          moveDraggedRow();
          applyGhostTransform();
        }
      });
    }
  }

  function finishDrag() {
    if (!draggedRow || cancelled) return;
    const newOrder = getRowOrder();
    cleanup();
    onReorder(newOrder);
  }

  function onPointerUp(e) {
    if (!draggedRow || cancelled) return;
    e.preventDefault();
    finishDrag();
  }

  function onPointerCancel(e) {
    if (!draggedRow || cancelled) return;
    e.preventDefault();
    finishDrag();
  }

  function onPointerLeave(e) {
    if (!draggedRow || cancelled) return;
    // Only finish if leaving the list element itself
    if (e.target === listEl) {
      finishDrag();
    }
  }

  listEl.addEventListener('pointerdown', onPointerDown);
  listEl.addEventListener('pointermove', onPointerMove);
  listEl.addEventListener('pointerup', onPointerUp);
  listEl.addEventListener('pointercancel', onPointerCancel);
  listEl.addEventListener('pointerleave', onPointerLeave);
}
