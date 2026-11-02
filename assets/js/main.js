(() => {
  const toggle = document.getElementById('theme-toggle');
  const updateCommentTheme = () => {
    const frame = document.querySelector('iframe.giscus-frame');
    frame?.contentWindow?.postMessage({
      giscus: { setConfig: { theme: document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light' } },
    }, 'https://giscus.app');
  };
  document.addEventListener('load', (event) => {
    if (event.target instanceof HTMLIFrameElement && event.target.classList.contains('giscus-frame')) {
      updateCommentTheme();
    }
  }, true);
  const updateThemeLabel = () => {
    if (!toggle) return;
    const label = document.documentElement.dataset.theme === 'dark'
      ? 'Switch to light theme' : 'Switch to dark theme';
    toggle.setAttribute('aria-label', label);
    toggle.setAttribute('title', label);
  };

  updateThemeLabel();
  updateCommentTheme();
  toggle?.addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    updateThemeLabel();
    try {
      localStorage.setItem('pref-theme', theme);
    } catch (error) {
      console.warn('The theme preference could not be saved:', error);
    }
  });

  const topLink = document.getElementById('top-link');
  if (topLink) {
    const updateTopLink = () => topLink.classList.toggle('hidden', window.scrollY <= window.innerHeight);
    window.addEventListener('scroll', updateTopLink, { passive: true });
    updateTopLink();
  }

  const searchInput = document.getElementById('site-search');
  const searchStatus = document.getElementById('search-status');
  const searchResults = document.getElementById('search-results');
  if (searchInput && searchStatus && searchResults) {
    const baseURL = document.querySelector('meta[name="site-base"]')?.content || window.location.origin + '/';
    const searchIndexURL = new URL('search-index.json', baseURL);
    let searchIndex;

    const renderSearchResults = (query) => {
      searchResults.replaceChildren();
      const terms = query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
      if (!terms.length) {
        searchStatus.textContent = 'Enter a search term to find editions.';
        return;
      }

      const matches = searchIndex
        .map((item) => {
          const title = String(item.title || '').toLocaleLowerCase();
          const description = String(item.description || '').toLocaleLowerCase();
          const content = String(item.content || '').toLocaleLowerCase();
          const allText = `${title} ${description} ${content}`;
          if (!terms.every((term) => allText.includes(term))) return null;
          const score = terms.reduce((total, term) =>
            total + (title.includes(term) ? 5 : 0) +
              (description.includes(term) ? 3 : 0) +
              (content.includes(term) ? 1 : 0), 0);
          return { item, score };
        })
        .filter(Boolean)
        .sort((left, right) => right.score - left.score || right.item.date.localeCompare(left.item.date))
        .slice(0, 30);

      searchStatus.textContent = matches.length
        ? `${matches.length} ${matches.length === 1 ? 'edition' : 'editions'} found.`
        : 'No editions matched that search.';

      for (const { item } of matches) {
        const url = new URL(item.url, baseURL);
        if (url.origin !== window.location.origin) continue;

        const card = document.createElement('article');
        card.className = 'post-entry edition-card';
        const meta = document.createElement('div');
        meta.className = 'edition-meta';
        const date = document.createElement('time');
        date.dateTime = item.date || '';
        date.textContent = item.date || '';
        meta.append(date);

        const header = document.createElement('header');
        header.className = 'entry-header';
        const title = document.createElement('h2');
        const link = document.createElement('a');
        link.href = url.href;
        link.textContent = item.title || 'Untitled edition';
        title.append(link);
        header.append(title);

        const description = document.createElement('div');
        description.className = 'entry-content';
        const paragraph = document.createElement('p');
        paragraph.textContent = item.description || '';
        description.append(paragraph);
        card.append(meta, header, description);
        searchResults.append(card);
      }

      const locationURL = new URL(window.location.href);
      locationURL.searchParams.set('q', query);
      window.history.replaceState({}, '', locationURL);
    };

    fetch(searchIndexURL)
      .then((response) => {
        if (!response.ok) throw new Error(`Search index request failed (${response.status})`);
        return response.json();
      })
      .then((index) => {
        if (!Array.isArray(index)) throw new TypeError('Search index is not an array.');
        searchIndex = index;
        const query = new URLSearchParams(window.location.search).get('q') || '';
        searchInput.value = query;
        renderSearchResults(query);
        searchInput.addEventListener('input', () => renderSearchResults(searchInput.value));
      })
      .catch((error) => {
        console.error('The edition search could not be loaded:', error);
        searchStatus.textContent = 'Search is temporarily unavailable.';
      });
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch((error) => {
      console.error('The offline service worker could not be registered:', error);
    });
  }
})();
