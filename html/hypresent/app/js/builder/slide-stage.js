// slide-stage.js — full-size in-place slide inspector (read-only)

import { getSlideSrcdoc } from './previews.js';

export function createSlideStage(opts) {
  const { container, getLibraryPath, getSlideRecord, onAdd, isAdded } = opts;
  if (!container) return { open() {}, close() {} };

  let currentId = null;
  let keyHandler = null;
  let frame = null;
  let iframe = null;
  let prevBtn = null;
  let nextBtn = null;
  let addBtn = null;
  let titleEl = null;
  let errorEl = null;

  function ensureBuilt() {
    if (container.querySelector('.slide-stage')) return;

    const stage = document.createElement('div');
    stage.className = 'slide-stage';
    stage.dataset.testid = 'slide-stage';

    const bar = document.createElement('div');
    bar.className = 'slide-stage-bar';

    prevBtn = document.createElement('button');
    prevBtn.type = 'button';
    prevBtn.className = 'ss-prev';
    prevBtn.textContent = '‹ Prev';
    prevBtn.addEventListener('click', () => navigate(-1));
    bar.appendChild(prevBtn);

    nextBtn = document.createElement('button');
    nextBtn.type = 'button';
    nextBtn.className = 'ss-next';
    nextBtn.textContent = 'Next ›';
    nextBtn.addEventListener('click', () => navigate(1));
    bar.appendChild(nextBtn);

    titleEl = document.createElement('span');
    titleEl.className = 'ss-title';
    bar.appendChild(titleEl);

    addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.className = 'ss-add';
    addBtn.addEventListener('click', () => {
      if (currentId && typeof onAdd === 'function') {
        onAdd(currentId);
        refreshAddState(currentId);
      }
    });
    bar.appendChild(addBtn);

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'ss-close';
    closeBtn.textContent = '✕';
    closeBtn.setAttribute('aria-label', 'Close');
    closeBtn.addEventListener('click', close);
    bar.appendChild(closeBtn);

    stage.appendChild(bar);

    const body = document.createElement('div');
    body.className = 'slide-stage-body';

    frame = document.createElement('div');
    frame.className = 'slide-stage-frame';

    iframe = document.createElement('iframe');
    iframe.setAttribute('tabindex', '-1');
    frame.appendChild(iframe);

    errorEl = document.createElement('div');
    errorEl.className = 'slide-stage-error';
    errorEl.textContent = "Couldn't load this slide.";
    errorEl.style.display = 'none';

    body.appendChild(frame);
    body.appendChild(errorEl);
    stage.appendChild(body);

    container.appendChild(stage);
  }

  function getVisibleIds() {
    return Array.from(container.querySelectorAll('.slide-card:not(.hidden)')).map(c => c.dataset.slideId);
  }

  function refreshAddState(id) {
    if (!addBtn) return;
    const added = typeof isAdded === 'function' ? isAdded(id) : false;
    addBtn.textContent = added ? 'Added' : 'Add to presentation';
    addBtn.classList.toggle('is-added', added);
    addBtn.disabled = added;
  }

  function updateNav(index, total) {
    if (prevBtn) prevBtn.disabled = index <= 0;
    if (nextBtn) nextBtn.disabled = index >= total - 1;
  }

  function renderSlide(id) {
    currentId = id;
    const rec = typeof getSlideRecord === 'function' ? getSlideRecord(id) : null;
    if (titleEl) {
      titleEl.textContent = rec && rec.title ? rec.title : id;
      titleEl.dataset.slideId = id;
    }

    if (iframe) {
      iframe.srcdoc = '';
    }
    if (errorEl) {
      errorEl.style.display = 'none';
    }
    if (frame) {
      frame.style.display = '';
    }

    const libraryPath = typeof getLibraryPath === 'function' ? getLibraryPath() : null;
    if (libraryPath && id) {
      getSlideSrcdoc(libraryPath, id)
        .then(srcdoc => {
          if (currentId === id && iframe) {
            iframe.srcdoc = srcdoc;
          }
        })
        .catch(() => {
          if (currentId === id) {
            if (frame) frame.style.display = 'none';
            if (errorEl) errorEl.style.display = '';
          }
        });
    }

    refreshAddState(id);
  }

  function navigate(delta) {
    const ids = getVisibleIds();
    const idx = ids.indexOf(currentId);
    if (idx === -1) return;
    const nextIdx = idx + delta;
    if (nextIdx < 0 || nextIdx >= ids.length) return;
    renderSlide(ids[nextIdx]);
    updateNav(nextIdx, ids.length);
  }

  function open(slideId) {
    ensureBuilt();
    const stage = container.querySelector('.slide-stage');
    if (!stage) return;

    const ids = getVisibleIds();
    const idx = ids.indexOf(slideId);
    if (idx === -1) return;

    renderSlide(slideId);
    updateNav(idx, ids.length);

    stage.classList.add('is-open');

    if (!keyHandler) {
      keyHandler = (e) => {
        if (!stage.classList.contains('is-open')) return;
        const tag = document.activeElement && document.activeElement.tagName;
        const typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
        if (e.key === 'Escape') {
          e.preventDefault();
          close();
        } else if (e.key === 'ArrowLeft' && !typing) {
          e.preventDefault();
          if (prevBtn && !prevBtn.disabled) navigate(-1);
        } else if (e.key === 'ArrowRight' && !typing) {
          e.preventDefault();
          if (nextBtn && !nextBtn.disabled) navigate(1);
        }
      };
      document.addEventListener('keydown', keyHandler);
    }
  }

  function close() {
    const stage = container.querySelector('.slide-stage');
    if (stage) {
      stage.classList.remove('is-open');
    }
    if (iframe) {
      iframe.srcdoc = '';
    }
    currentId = null;

    if (keyHandler) {
      document.removeEventListener('keydown', keyHandler);
      keyHandler = null;
    }

    // Return focus to the originating card if it still exists
    if (stage && stage.dataset.lastSlideId) {
      const card = container.querySelector('.slide-card[data-slide-id="' + stage.dataset.lastSlideId + '"]');
      if (card) card.focus();
    }
  }

  return { open, close };
}
