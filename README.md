# MyBusinessNews

Source-linked business, regional and personal-finance news directory.

## Public site
https://gmreddy0809-cloud.github.io/MyBusinessNews/

## Editorial display
Every newsroom feed supports a Telugu headline (`title_te`) and a concise, 2-sentence Telugu snippet (`snippet_te`) when one has been verified or generated from the supplied headline/official summary. If none exists, the original headline and a transparent Telugu fallback are shown. Never invent facts absent from the source title or an authorized official summary.

## Enable automatic Telugu snippets
In GitHub, open **Settings → Secrets and variables → Actions → New repository secret**.
Create a secret named `OPENAI_API_KEY` with a valid key for an account that has API billing configured. This is a separately billed API service, not included in ChatGPT Plus.
The scheduled GitHub Actions workflow enriches up to 45 new items per run (configurable via `MBN_SNIPPETS_PER_RUN`). Previously enriched fields persist on refresh. No secrets belong in HTML or committed JSON.

The site still works without the key; the accurate title/source/original link are visible, and no fabricated Telugu summaries are displayed.

## Feeds and permissions
Official feeds and publisher-granted RSS may supply brief source material. GDELT discovery supplies article titles/index timestamps, **not article body text**. The site never bypasses paywalls. Publisher directories (including CNBC-TV18, Zee Business, Upstox) are navigation/discovery lists, not claims of licensed RSS integration.

## Automatic deployment
`.github/workflows/news.yml` runs twice an hour and on changes to scripts, tests and workflow configuration, then publishes `index.html` and `data/news.json` to GitHub Pages. Check **Actions** for build or publishing failures.

The collector retains items first indexed on/after **14 Nov 2026 IST**, subject to availability, feed retention, repository size and the per-desk safety cap. This is not a guarantee of complete historical news coverage.

## Verification
`python -m unittest discover -s tests -p "test_*.py"`
