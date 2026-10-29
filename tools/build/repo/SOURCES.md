# Sources and legal basis

## Source

**cookislandslaws.gov.ck**, the consolidated legislation of the Cook Islands, "managed on behalf of the Legislative
Service in accordance with the requirements of the Legislative Service Act 1968-69" (the site's disclaimer). It is an
Angular single-page app over a JSON API at `https://cookislandslaws.gov.ck/api/` (the bundle also names the API's
former hosts at LexisNexis, `cookislands.lexisnexis.com`). Endpoints used:

- `retrieve_all_act`: the list of Acts ({{ACT_LIST}} entries on {{FETCHED_ON}}).
- `retrieve_toc/<Act name>`: an Act's table of contents, including the subsidiary legislation made under it.
- `display_pages/<law name>`: a law's front page (name, Table of Amendments, long title, enacting words).
- `display_pages/<node id>`: one section, regulation, clause, rule, schedule, form or schedule part, as XHTML.
- `historical_amadments/<Act name>` was tried for every law and returns `[]`: there are no past versions.

## Checks before fetching (2026-10-29)

- robots.txt: `https://cookislandslaws.gov.ck/robots.txt` answers 404 (an IIS error page), so there are no rules,
  none naming ClaudeBot, Claude-Web, anthropic-ai or GPTBot, and no Crawl-delay. `parliament.gov.ck` (which links
  the database) has `Crawl-delay: 10` for its own pages, which were not crawled.
- Terms: the site has a Disclaimer (no liability; not a substitute for legal advice) and a Privacy Policy; no terms
  of use. Nothing forbids automated access or reuse.

## Legal basis for reuse

Copyright Act 2013 (Cook Islands), section 3 (Interpretation), as consolidated on the same site: "work" "(c) does not
include any work that is an official text, or a translation, of a legislative, administrative, or legal nature."

## Fetch rate

One process, at most 3 requests in flight, retries waiting 3-12 s. The server answers one request in about 1 s
and seemed to handle them in turn, so the crawl ran at about 1.3 requests a second.
