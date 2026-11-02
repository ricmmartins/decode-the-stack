(() => {
  const toggle = document.querySelector('#theme-toggle');
  const theme = document.documentElement;
  const updateToggle = () => {
    const dark = theme.dataset.theme === 'dark';
    toggle?.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    toggle?.setAttribute('title', dark ? 'Switch to light theme' : 'Switch to dark theme');
    if (toggle) toggle.textContent = dark ? '☼' : '◐';
  };
  updateToggle();
  toggle?.addEventListener('click', () => {
    const next = theme.dataset.theme === 'dark' ? 'light' : 'dark';
    theme.dataset.theme = next;
    updateToggle();
    try {
      localStorage.setItem('decode-theme', next);
    } catch (error) {
      console.warn('Theme preference could not be saved:', error);
    }
  });

  const input = document.querySelector('#site-search');
  const results = document.querySelector('#search-results');
  const status = document.querySelector('#search-status');
  if (!input || !results || !status) return;

  let index;
  fetch(`${document.querySelector('meta[name="site-base"]')?.content ?? ''}search-index.json`)
    .then((response) => {
      if (!response.ok) throw new Error(`Search index request failed (${response.status})`);
      return response.json();
    })
    .then((data) => { index = data; status.textContent = 'Search the complete edition archive.'; })
    .catch((error) => { status.textContent = 'Search is temporarily unavailable.'; console.error(error); });

  input.addEventListener('input', () => {
    results.replaceChildren();
    const query = input.value.trim().toLocaleLowerCase();
    if (!query) {
      status.textContent = index ? 'Search the complete edition archive.' : 'Loading the search index…';
      return;
    }
    if (!index) {
      status.textContent = 'Search is temporarily unavailable.';
      return;
    }
    const matches = index.filter((item) =>
      `${item.title} ${item.description} ${item.content}`.toLocaleLowerCase().includes(query)
    ).slice(0, 30);
    status.textContent = `${matches.length} ${matches.length === 1 ? 'edition' : 'editions'} found.`;
    for (const item of matches) {
      const card = document.createElement('article');
      card.className = 'edition-card';
      const date = document.createElement('p');
      date.className = 'eyebrow';
      date.textContent = item.date;
      const heading = document.createElement('h2');
      const link = document.createElement('a');
      link.href = item.url;
      link.textContent = item.title;
      heading.append(link);
      const description = document.createElement('p');
      description.textContent = item.description;
      card.append(date, heading, description);
      results.append(card);
    }
  });
})();
