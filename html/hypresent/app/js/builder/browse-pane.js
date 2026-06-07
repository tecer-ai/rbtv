// browse-pane.js — section-grouped browse + language filter

import { mountPreviews } from './previews.js';

export function renderBrowse(data, { onTag, libraryPath }) {
  const groupsContainer = document.getElementById('browse-groups');
  const emptyState = document.getElementById('browse-empty');
  const langFilter = document.getElementById('lang-filter');

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
    const group = document.createElement('div');
    group.className = 'browse-group';

    const label = document.createElement('div');
    label.className = 'browse-group-label';
    label.textContent = sectionName;
    group.appendChild(label);

    // Slides in this section, in manifest order
    const sectionSlides = data.slides.filter(s => s.section === sectionName);
    sectionSlides.forEach(slide => {
      const card = document.createElement('div');
      card.className = 'slide-card';
      card.dataset.slideId = slide.id;
      card.dataset.lang = slide.lang || '';

      const title = document.createElement('div');
      title.className = 'slide-title';
      title.textContent = slide.title || slide.id;
      card.appendChild(title);

      const meta = document.createElement('div');
      meta.className = 'slide-meta';

      const kindBadge = document.createElement('span');
      kindBadge.className = 'kind-badge';
      kindBadge.textContent = slide.kind === 'template' ? 'template' : 'ready';
      meta.appendChild(kindBadge);

      const langBadge = document.createElement('span');
      langBadge.className = 'lang-badge';
      langBadge.textContent = slide.lang || '';
      meta.appendChild(langBadge);

      card.appendChild(meta);

      const thumbWrapper = document.createElement('div');
      thumbWrapper.className = 'slide-thumb-wrapper';

      const iframe = document.createElement('iframe');
      iframe.dataset.slideId = slide.id;
      // srcdoc intentionally empty — previews mounted by PB-T9
      thumbWrapper.appendChild(iframe);

      card.appendChild(thumbWrapper);

      card.addEventListener('click', () => onTag(slide));
      group.appendChild(card);
    });

    if (sectionSlides.length > 0) {
      groupsContainer.appendChild(group);
    }
  });

  // Populate language filter
  if (langFilter) {
    const distinctLangs = [...new Set(data.slides.map(s => s.lang).filter(Boolean))];
    // Keep the existing "all" option
    const existingOptions = Array.from(langFilter.options);
    const allOption = existingOptions.find(o => o.value === 'all');
    langFilter.innerHTML = '';
    if (allOption) {
      langFilter.appendChild(allOption);
    } else {
      const optAll = document.createElement('option');
      optAll.value = 'all';
      optAll.textContent = 'all';
      langFilter.appendChild(optAll);
    }
    distinctLangs.forEach(lang => {
      const opt = document.createElement('option');
      opt.value = lang;
      opt.textContent = lang;
      langFilter.appendChild(opt);
    });
  }

  if (libraryPath) {
    mountPreviews(libraryPath, groupsContainer);
  }
}

export function applyLangFilter(selectedLang) {
  const cards = document.querySelectorAll('.slide-card');
  cards.forEach(card => {
    const id = card.dataset.slideId;
    const lang = card.dataset.lang;
    let show = false;
    if (selectedLang === 'all') {
      show = true;
    } else if (lang === selectedLang) {
      show = true;
    } else if (!id.endsWith('.' + lang)) {
      show = true;
    }
    card.classList.toggle('hidden', !show);
  });
}
