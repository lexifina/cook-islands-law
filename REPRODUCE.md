# Reproducing this repository

Built on 2026-10-29 from the cookislandslaws.gov.ck API (retrieved 2026-10-29), by the scripts in `tools/build/`
(copied there as run).

| Script | sha256 |
| --- | --- |
| fetch.py | `06a37248873570dad748e094c02296d7311234dfd3dc3ee0127bcc4df698478c` |
| build.py | `f5c9aef818aa982420ce2f497f3d6cfe4b975c023be87b7ac0c989f7519973ed` |
| docs.py | `70882693f9d21e55e6611e371e8361302426ff42bdaa9f92f110be8a0b9ca840` |

## Steps

```sh
# 1. The list of Acts and each Act's table of contents (about 270 requests).
python fetch.py list
# 2. Each law's front page and every table-of-contents entry (about 22,000 requests; resumable).
#    Answers that fail twice with 404/500 are cached as .err files and not asked again.
python fetch.py pages
# 3. Build. --today dates the documentation commit and is the latest date allowed.
python build.py ../cook-islands-law --today 2026-10-29
```

## robots.txt and bulk data

Checked on 2026-10-29: `https://cookislandslaws.gov.ck/robots.txt` answers 404, so there are no rules at all, none
aimed at AI crawlers (ClaudeBot, Claude-Web, anthropic-ai, GPTBot) and no Crawl-delay. The site offers no bulk
download; its API serves one table of contents per Act and one entry per request. Hence the crawl.

## Fetch rate

No Crawl-delay is set. `fetch.py` is one process with at most 3 requests in flight. Each answer took about 1 s and
the server appeared to answer them one at a time, so the crawl ran at about 1.3 requests a second (about 4.5 hours
for the whole database). A failed request is retried up to 4 times, waiting 3, 6, 9 and 12 s (5-20 s on network
errors). Every answer is kept under `.cache/` (git-ignored); [`data/source-sha256.tsv`](data/source-sha256.tsv) lists
the sha256 of each. With the same answers `build.py` gives the same commit hashes: it writes the whole history in one
`git fast-import` stream, sorted, with fixed dates.

## What the build produced

- 662 laws: 272 Acts, 390 pieces of subsidiary legislation; 20669 unit files.
- 659 commits: 658 consolidated (one per law) and one documentation commit.
- In-force dates from 1908-08-04 to 2026-10-29.
- 79 rows in `data/unreadable.csv` (entries the site would not serve, laws with later dates).

## Checks

```sh
git rev-list --merges --count main                  # 0
git log --format='%(trailers:key=In-force,valueonly)' main | grep . | sort -c -r   # dates never go back
python tools/in_force_on.py 2026-10-29 acts/banking-act-2011 s4
```

Rebuilding twice from the same cache gives the same `git rev-parse HEAD`.
