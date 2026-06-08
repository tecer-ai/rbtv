// browse-pane.js — section-grouped browse + language filter + tray-state badges

import { mountPreviews } from './previews.js';

export function renderBrowse(data, { onTag, libraryPath, onExpand }) {
  const groupsContainer = document.getElementById('browse-groups');
  const emptyState = document.getElementById('browse-empty');

  groupsContainer.innerHTML = '';
  if (emptyState) {
    emptyState.style.display = 'none';
  }

  if (!data || !data.sections || !data.slides) {
    if (emptyState) {
      emptyState.style.display = '';
    }
    return;
  }

  // Build section groups in manifest order
  data.sections.forEach(sectionName => {
    const sectionSlides = data.slides.filter(s => s.section === sectionName);
    if (sectionSlides.length === 0) return;

    const group = document.createElement('section');
    group.className = 'browse-group browse-sec';
    group.dataset.section = sectionName;

    const header = document.createElement('header');

    const label = document.createElement('h2');
    label.className = 'browse-group-label';
    label.textContent = sectionName;
    header.appendChild(label);

    const count = document.createElement('span');
    count.className = 'n';
    count.textContent = sectionSlides.length + (sectionSlides.length === 1 ? ' slide' : ' slides');
    header.appendChild(count);

    const rule = document.createElement('span');
    rule.className = 'rule';
    header.appendChild(rule);

    group.appendChild(header);

    const grid = document.createElement('div');
    grid.className = 'slide-grid';

    sectionSlides.forEach(slide => {
      const card = document.createElement('article');
      card.className = 'slide-card';
      card.dataset.slideId = slide.id;
      card.dataset.lang = slide.lang || '';
      card.tabIndex = 0;
      card.setAttribute('aria-label', slide.title || slide.id);

      const badge = document.createElement('span');
      badge.className = 's-badge';
      card.appendChild(badge);

      const thumbWrapper = document.createElement('div');
      thumbWrapper.className = 'slide-thumb-wrapper';

      const iframe = document.createElement('iframe');
      iframe.dataset.slideId = slide.id;
      iframe.setAttribute('tabindex', '-1');
      // srcdoc intentionally empty — previews mounted lazily below
      thumbWrapper.appendChild(iframe);

      const expandBtn = document.createElement('button');
      expandBtn.type = 'button';
      expandBtn.className = 's-expand';
      expandBtn.setAttribute('aria-label', 'Expand slide');
      expandBtn.title = 'Expand';
      // magnifier glyph (inline SVG)
      expandBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>';
      expandBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (typeof onExpand === 'function') onExpand(slide.id);
      });
      thumbWrapper.appendChild(expandBtn);

      const addPill = document.createElement('span');
      addPill.className = 's-add';
      addPill.textContent = '+ Add';
      thumbWrapper.appendChild(addPill);

      card.appendChild(thumbWrapper);

      const cap = document.createElement('div');
      cap.className = 's-cap';

      const title = document.createElement('h3');
      title.className = 'slide-title';
      title.textContent = slide.title || slide.id;
      cap.appendChild(title);

      const meta = document.createElement('div');
      meta.className = 'slide-meta';

      const langBadge = document.createElement('span');
      langBadge.className = 'lang-badge';
      langBadge.textContent = slide.lang || '';
      meta.appendChild(langBadge);

      const kindBadge = document.createElement('span');
      kindBadge.className = 'kind-badge';
      kindBadge.textContent = slide.kind === 'template' ? 'template' : '';
      meta.appendChild(kindBadge);

      cap.appendChild(meta);
      card.appendChild(cap);

      card.addEventListener('click', () => onTag(slide));
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onTag(slide);
        }
      });
      grid.appendChild(card);
    });

    group.appendChild(grid);
    groupsContainer.appendChild(group);
  });

  if (libraryPath) {
    // IO root must be the SCROLL CONTAINER (.builder-browse), not the groups
    // div — with a non-scrolling root every thumb intersects forever and the
    // mount-cap eviction never finds candidates.
    const scrollRoot = document.getElementById('builder-browse') || groupsContainer;
    mountPreviews(libraryPath, scrollRoot);
  }
}

export function applyLangFilter(selectedLang) {
  // Strict language match (owner correction 2026-06-07): PT shows ONLY
  // pt-tagged slides. The old id-suffix "language-neutral" heuristic leaked
  // other-language slides into every filter. Untagged slides (no lang in the
  // manifest) stay visible under any filter — they are unclassifiable.
  const cards = document.querySelectorAll('.slide-card');
  cards.forEach(card => {
    const lang = card.dataset.lang;
    const show = selectedLang === 'all' || !lang || lang === selectedLang;
    card.classList.toggle('hidden', !show);
  });
}

// Sync browse cards with the tray: added cards show their 1-based position badge.
export function markTrayState(orderIds) {
  const cards = document.querySelectorAll('.slide-card');
  cards.forEach(card => {
    const idx = orderIds.indexOf(card.dataset.slideId);
    const added = idx !== -1;
    card.classList.toggle('is-added', added);
    const badge = card.querySelector('.s-badge');
    if (badge) badge.textContent = added ? String(idx + 1) : '';
    card.setAttribute('aria-pressed', added ? 'true' : 'false');
  });
}
