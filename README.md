# MyBusinessNews

Source-linked business, regional and personal-finance news directory.

## Public site
https://gmreddy0809-cloud.github.io/MyBusinessNews/

## Editorial display
Every newsroom feed supports a Telugu headline (`title_te`) and a concise, 2-sentence Telugu snippet (`snippet_te`) when one has been verified or generated from the supplied headline/official summary. If none exists, the original headline and a transparent Telugu fallback are shown. Never invent facts absent from the source title or an authorized official summary.

## Enable automatic Telugu snippets
In GitHub, open **Settings → Secrets and variables → Actions → New repository secret**.
Create a secret named `OPENAI_API_KEY` with a valid key for an account that has API billing configured. This is a separately billed API service, not included in ChatGPT Plus.
The code supports enrichment of up to 45 new items per run (configurable via `MBN_SNIPPETS_PER_RUN`), but the current GitHub Actions workflow explicitly sets `MBN_SNIPPETS_PER_RUN: '0'`: no paid automatic Telugu generation is currently enabled. Before enabling nonzero enrichment, configure the API key, confirm separate API billing and test generated content editorially. Previously enriched fields persist on refresh. No secrets belong in HTML or committed JSON.

The site still works without the key; the accurate title/source/original link are visible, and no fabricated Telugu summaries are displayed.

## Feeds and permissions
Official feeds and publisher-granted RSS may supply brief source material. GDELT discovery supplies article titles/index timestamps, **not article body text**. The site never bypasses paywalls. Publisher directories (including CNBC-TV18, Zee Business, Upstox) are navigation/discovery lists, not claims of licensed RSS integration.

## Reuters headline discovery

A dedicated Reuters-attributed Google News RSS search now runs in the half-hour
collector for India, World, business and regional stories. It stores Reuters
headlines, source credit, Google News redirect links and Google RSS index times.
This is **not a Reuters-owned RSS feed**, not a Reuters Connect subscription,
and does not grant rights to copy Reuters article bodies or images. Search
coverage is best effort and may miss individual articles. Reuters stories are
shown in their corresponding news tabs; search for `Reuters` to filter them.
Check `data/news.json -> source_status.reuters_discovery` for per-run results.

## Hyderabad Realty desk

The `#hyderabad-realty` tab is a dedicated **Hyderabad real-estate** index, separate
from the general Hyderabad business feed. Every half-hour refresh attempts 11
Google News RSS searches: real estate reports (JLL, CBRE, Cushman & Wakefield,
Knight Frank, Colliers, Savills, ANAROCK and others), office leases and property
transactions, residential sales and launches, land deals, and TG-RERA/HMDA news.
Searches rotate additional property micro-markets, associations and research
firms. The collector enforces an explicit Hyderabad or metropolitan-place cue
**in the headline** so that general national property reports are not mislabeled
as city developments. It tags accepted items as `Real Estate` and as
`Reports`, `Deals`, `Residential`, `Retail`, `Regulation`, or `Market News`. Retail coverage includes Hyderabad shopping streets, high-street rent rankings and mall/retail-space leasing.

The publisher is credited and the link opens a Google News click-through, not
a licensed syndication feed. Google RSS time is not verified original publication
time. Results are not exhaustive: a press release or report might not be indexed.
Official research pages and the TG-RERA portal are linked in the tab for manual
checks. The X link is an external live keyword search, **not an automatically
ingested X feed or an independent verification**. No unverified social claim is
promoted to a news story. Check
`data/news.json -> source_status.hyderabad_real_estate_discovery` for query
success, warnings, by-source counts and by-kind counts. Refresh failures do not
erase the previously indexed data.

## Hyderabad Mail local reporting

Hyderabad Mail (https://hyderabadmail.com/) has local Hyderabad-area news and a
dedicated [Real Estate section](https://hyderabadmail.com/category/real-estate/).
The `hyderabad_mail_rss` collector requests the site's public `/feed/` and
attempts the conventional WordPress `/category/real-estate/feed/` endpoint
(the category feed has not been independently confirmed to work). It accepts
only direct `hyderabadmail.com` article URLs with dated RSS entries, stores
**headlines, source, feed timestamps and publisher categories only**, and
does not copy article text/images. Failures are recorded independently in
`data/news.json -> source_status.hyderabad_mail_rss`. RSS access and coverage
are not guaranteed.

Hyderabad Mail items that clearly concern property, HMDA, TG-RERA or a
commercial deal appear under Hyderabad Realty (and other applicable business
views); city-local non-business headlines remain under the TG/AP+TG general
news views. A Hyderabad general story is not automatically classified as a
business article. The Hyderabad Realty source list links to the publisher's
Real Estate category as a manual fallback.

## Feedspot Telugu newsroom source expansion

Reference: https://rss.feedspot.com/telugu_news_rss_feeds/ (curated list
updated Aug 20, 2026). The regional Google News discovery pool includes 23
additional publisher-domain candidates from that list, making 73 configured
AP/TG publisher searches in total (priorities each run, others rotating).
Names in this discovery list are **not** the same as licensed publisher RSS
connections. Google News may index few or no headlines from some sources.
General AP/TG news is retained without business-only topic restrictions.

The AP, TG, AP+TG, Hyderabad and Telugu Publications views show a "తెలుగు
RSS సోర్సులు" source-directory panel with 10 publisher-supplied links as
reported by Feedspot; publishers can change or close these endpoints, and
their current response and reuse permissions have not all been verified.
Listings marked "Generate RSS" by Feedspot are not evidence that a publisher
offers a native RSS feed. These extra feeds are **navigation links**, not
ingested by the `publications.py` permission-restricted collector.
Use `data/news.json -> source_status.regional_discovery` to inspect actual
source-by-source Google News coverage rather than assuming all work.

## Automatic deployment
`.github/workflows/news.yml` runs twice an hour and on changes to scripts, tests and workflow configuration, then publishes `index.html` and `data/news.json` to GitHub Pages. Check **Actions** for build or publishing failures.

The collector retains items first indexed on/after **14 Nov 2026 IST**, subject to availability, feed retention, repository size and the per-desk safety cap. This is not a guarantee of complete historical news coverage.

## Verification
`python -m unittest discover -s tests -p "test_*.py"`

## Personal Finance source discovery
The PF collector uses a rotating Google News RSS search across **22 Indian financial publishers** and four personal-finance query families, plus category-scoped discovery for Upstox, Moneycontrol, Business Standard and NDTV Profit. It attempts ten feed searches each 30-minute run, so all 22 publishers receive source-topic coverage across approximately 5.5 hours if scheduled workflows keep succeeding.

Only dated, publisher-attributed, editorially relevant headline links are stored. Google News RSS links are Google click-throughs, not guaranteed original publisher URLs. The collector rejects non-PF articles that Google search sometimes includes and removes previously indexed false positives. A successful search does not prove every original article is indexed. This is a best-effort headline directory; content licensing, indexing limitations and downtime may affect coverage. For unindexed items, users can open the publisher-specific Google News searches from the PF source directory.

Look at `data/news.json → source_status.personal_finance_discovery` for per-run successes, failures and candidate counts; distinguish this from the final curated PF total. Never republish full stories or infer snippets from headlines without supporting facts.
