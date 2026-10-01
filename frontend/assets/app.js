(() => {
  const assistant = document.querySelector('#assistant');
  const launcher = document.querySelector('#launcher');
  const close = document.querySelector('#close-chat');
  const form = document.querySelector('#chat-form');
  const input = document.querySelector('#message-input');
  const send = document.querySelector('#send-button');
  const messages = document.querySelector('#messages');
  const status = document.querySelector('#status');
  let busy = false;
  const history = [];

  document.querySelectorAll('[data-open-assistant]').forEach(button => {
    button.addEventListener('click', () => setOpen(true));
  });

  function setOpen(open) {
    assistant.classList.toggle('open', open);
    assistant.setAttribute('aria-hidden', String(!open));
    launcher.setAttribute('aria-expanded', String(open));
    launcher.hidden = open;
    document.body.style.overflow = open && window.matchMedia('(max-width: 520px)').matches ? 'hidden' : '';
    if (open) window.setTimeout(() => input.focus(), 120);
    else launcher.focus();
  }

  function scrollToEnd() {
    messages.scrollTop = messages.scrollHeight;
  }

  function appendInlineFormatting(container, value) {
    const pattern = /(\*\*[^*]+\*\*|\[S\d+\])/g;
    let cursor = 0;
    for (const match of value.matchAll(pattern)) {
      if (match.index > cursor) {
        container.append(document.createTextNode(value.slice(cursor, match.index)));
      }
      if (match[0].startsWith('**')) {
        const strong = document.createElement('strong');
        strong.textContent = match[0].slice(2, -2);
        container.append(strong);
      } else {
        const citation = document.createElement('span');
        citation.className = 'citation-ref';
        citation.textContent = match[0];
        container.append(citation);
      }
      cursor = match.index + match[0].length;
    }
    if (cursor < value.length) container.append(document.createTextNode(value.slice(cursor)));
  }

  function renderAssistantText(container, text) {
    const lines = String(text || '').replace(/\r\n/g, '\n').split('\n');
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      const value = line.trim();
      if (!value) {
        const spacer = document.createElement('span');
        spacer.className = 'response-spacer';
        container.append(spacer);
        continue;
      }
      const next = lines[index + 1]?.trim() || '';
      if (value.includes('|') && /^\|?[\s:|-]+\|[\s:|-]*\|?$/.test(next)) {
        const parseCells = row => row.replace(/^\||\|$/g, '').split('|').map(cell => cell.trim());
        const wrapper = document.createElement('div');
        wrapper.className = 'response-table-wrap';
        const table = document.createElement('table');
        const head = document.createElement('thead');
        const headRow = document.createElement('tr');
        parseCells(value).forEach(cell => {
          const heading = document.createElement('th');
          appendInlineFormatting(heading, cell);
          headRow.append(heading);
        });
        head.append(headRow);
        table.append(head);
        const body = document.createElement('tbody');
        index += 2;
        while (index < lines.length && lines[index].includes('|')) {
          const row = document.createElement('tr');
          parseCells(lines[index].trim()).forEach(cell => {
            const data = document.createElement('td');
            appendInlineFormatting(data, cell);
            row.append(data);
          });
          body.append(row);
          index += 1;
        }
        index -= 1;
        table.append(body);
        wrapper.append(table);
        container.append(wrapper);
        continue;
      }
      const headingMatch = value.match(/^#{1,4}\s+(.+)$/);
      const bulletMatch = value.match(/^[-*\u2022]\s+(.+)$/);
      const numberedMatch = value.match(/^(\d+)[.)]\s+(.+)$/);
      const element = document.createElement(headingMatch ? 'h3' : 'p');
      if (bulletMatch || numberedMatch) element.className = 'response-list-item';
      if (bulletMatch) element.dataset.marker = '\u2022';
      if (numberedMatch) element.dataset.marker = `${numberedMatch[1]}.`;
      appendInlineFormatting(
        element,
        headingMatch?.[1] || bulletMatch?.[1] || numberedMatch?.[2] || value,
      );
      container.append(element);
    }
  }

  function message(role, text, data) {
    const item = document.createElement('div');
    item.className = `message ${role}-message`;
    const label = document.createElement('span');
    label.className = 'message-label';
    label.textContent = role === 'user' ? 'You' : 'Assistant';
    const body = document.createElement('div');
    body.className = 'message-body';
    if (role === 'assistant') renderAssistantText(body, text);
    else {
      const paragraph = document.createElement('p');
      paragraph.textContent = text;
      body.append(paragraph);
    }
    item.append(label, body);

    if (data?.grounding === 'unverified_llm') {
      const groundingNotice = document.createElement('div');
      groundingNotice.className = 'grounding-notice';
      groundingNotice.textContent = 'General AI guidance - no matching local source was found';
      item.append(groundingNotice);
    }

    if (data?.sources?.length) {
      const sources = document.createElement('div');
      sources.className = 'sources';
      const title = document.createElement('strong');
      title.textContent = 'Official sources';
      sources.append(title);
      data.sources.forEach((source, index) => {
        const link = document.createElement('a');
        link.href = source.source_url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = `[S${index + 1}] ${source.title}${source.provision ? ` - ${source.provision}` : ''}`;
        sources.append(link);
      });
      item.append(sources);
    }
    if (data?.disclaimer) {
      const note = document.createElement('p');
      note.className = 'disclaimer';
      note.textContent = data.disclaimer;
      item.append(note);
    }
    messages.append(item);
    scrollToEnd();
  }

  function resizeInput() {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 110)}px`;
  }

  async function submit(text) {
    const query = text.trim();
    if (!query || busy) return;
    busy = true;
    send.disabled = true;
    input.disabled = true;
    message('user', query);
    history.push({ role: 'user', content: query });
    input.value = '';
    resizeInput();
    status.textContent = 'Checking indexed legal sources';
    status.className = 'status loading';
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query, history: history.slice(-10) }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'The service returned an error.');
      message('assistant', data.answer || 'No answer was returned.', data);
      history.push({ role: 'assistant', content: data.answer || '' });
    } catch (error) {
      message('assistant', `${error.message || 'I could not reach the legal information service.'} Please try again.`);
    } finally {
      busy = false;
      send.disabled = false;
      input.disabled = false;
      status.textContent = '';
      status.className = 'status';
      input.focus();
    }
  }

  launcher.addEventListener('click', () => setOpen(true));
  close.addEventListener('click', () => setOpen(false));
  form.addEventListener('submit', event => { event.preventDefault(); submit(input.value); });
  input.addEventListener('input', resizeInput);
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit(input.value);
    }
  });
  document.querySelectorAll('.suggestions button').forEach(button => {
    button.addEventListener('click', () => submit(button.textContent));
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && assistant.classList.contains('open')) setOpen(false);
  });
})();
