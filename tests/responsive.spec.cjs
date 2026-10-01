const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const targetUrl = process.env.TARGET_URL || 'http://127.0.0.1:8000';
const artifactDir = process.env.PW_ARTIFACT_DIR || path.join(process.cwd(), 'test-artifacts');
fs.mkdirSync(artifactDir, { recursive: true });

const viewports = [
  { name: 'mobile-320', width: 320, height: 568 },
  { name: 'mobile-375', width: 375, height: 812 },
  { name: 'mobile-430', width: 430, height: 932 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'laptop-1024', width: 1024, height: 768 },
  { name: 'laptop-1366', width: 1366, height: 768 },
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'desktop-1920', width: 1920, height: 1080 },
  { name: 'desktop-short-1900', width: 1900, height: 590 },
];

function check(condition, message) {
  if (!condition) throw new Error(message);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  try {
    for (const viewport of viewports) {
      console.log(`Testing ${viewport.name}`);
      const page = await browser.newPage({ viewport });
      await page.route('**/api/chat', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            answer: '**Seedha jawab**\n\nArticle 25 concerns equality of citizens. [S1]\n\n| Provision | Meaning |\n|---|---|\n| **Article 25** | Equal protection of law |\n\n- Official text check karein.\n- Qualified lawyer se mashwara karein.',
            scope: 'pakistan_law', grounding: 'rag', language: 'english', request_id: 'test',
            disclaimer: 'Legal information only—not legal advice.',
            sources: [{
              id: 'constitution', title: 'Constitution of the Islamic Republic of Pakistan, 1973 — a deliberately long official document title',
              source_name: 'National Assembly of Pakistan',
              source_url: 'https://na.gov.pk/a/very/long/source/path/that/must/wrap/without/horizontal/overflow/document.pdf',
              document_type: 'constitution', provision: 'Article 25', effective_status: 'current',
            }],
          }),
        });
      });
      await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 10000 });
      await page.getByRole('heading', { name: /Pakistani law/i }).waitFor();
      await page.getByRole('heading', { name: /Why this assistant was created/i }).waitFor();
      await page.getByRole('heading', { name: 'Hammad Younis Abbasi' }).waitFor();
      const profileImageLoaded = await page.locator('.brand-mark img').evaluate(image => image.complete && image.naturalWidth > 0);
      check(profileImageLoaded, `${viewport.name}: img.png profile image did not load`);
      console.log('  loaded');
      const rootOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
      check(!rootOverflow, `${viewport.name}: page has horizontal overflow`);
      await page.locator('#launcher').click();
      console.log('  opened');
      await page.getByLabel('Ask a question about Pakistani law').fill('What does Article 25 mean?');
      await page.getByLabel('Ask a question about Pakistani law').press('Enter');
      console.log('  submitted');
      await page.getByText(/Article 25 concerns equality/i).waitFor();
      check(await page.locator('.response-table-wrap table').isVisible(), `${viewport.name}: response table was not rendered`);
      console.log('  answered');
      const assistantBox = await page.locator('#assistant').boundingBox();
      console.log('  assistant box', JSON.stringify(assistantBox));
      check(assistantBox.x >= -1 && assistantBox.y >= -1, `${viewport.name}: assistant starts off-screen`);
      check(assistantBox.x + assistantBox.width <= viewport.width + 1, `${viewport.name}: assistant exceeds viewport width`);
      if (viewport.width > 520) check(assistantBox.width <= 421, `${viewport.name}: desktop assistant became full-screen`);
      const overflow = await page.evaluate(() => document.querySelector('#assistant').scrollWidth > document.querySelector('#assistant').clientWidth);
      check(!overflow, `${viewport.name}: assistant has horizontal overflow`);
      await page.screenshot({ path: path.join(artifactDir, `${viewport.name}.png`), fullPage: true });
      await page.getByRole('button', { name: 'Close legal assistant' }).click();
      check(await page.locator('#launcher').isVisible(), `${viewport.name}: launcher did not return`);
      results.push({ viewport: viewport.name, status: 'passed' });
      await page.close();
    }

    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    let requests = 0;
    await page.route('**/api/chat', async route => {
      requests += 1;
      await new Promise(resolve => setTimeout(resolve, 120));
      await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Test network error' }) });
    });
    console.log('Testing keyboard and error behavior');
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 10000 });
    await page.locator('#launcher').click();
    const field = page.getByLabel('Ask a question about Pakistani law');
    await field.fill('Line one');
    await field.press('Shift+Enter');
    await field.type('Line two');
    check((await field.inputValue()).includes('\n'), 'Shift+Enter did not create a new line');
    await page.getByRole('button', { name: 'Send message' }).dblclick();
    await page.getByText(/Test network error/i).waitFor();
    check(requests === 1, `duplicate-submit protection failed: ${requests} requests`);
    results.push({ interaction: 'keyboard, error, duplicate submission', status: 'passed' });
    await page.close();
    console.log(JSON.stringify(results, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
