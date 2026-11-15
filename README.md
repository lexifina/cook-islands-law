# Cook Islands: law history in git


The law of the Cook Islands as a git history: one file per section (or regulation, rule, clause, schedule or form), one commit per version on the day it took effect. The official site keeps only the current text of each law, so each law has one version so far, credited to the publisher of the consolidation; the amending laws, and the days their changes took effect, are in each law's Table of Amendments and in the history note under each provision. A later consolidation is added as a new commit, so `git log` and `git blame` show each change from this version on.

Part of [lexifina/global-law](https://github.com/lexifina/global-law), one git history for every country's law: this is the Cook Islands' national law, which global-law reads at `cook-islands/national/acts/`.

**What is in it now:** 272 Acts and 388 pieces of subsidiary legislation made under them, each in its current consolidation as retrieved on 29 October 2026, with in-force days from 4 August 1908 to 29 October 2026; four more catalogue entries, the Appropriation Acts 2022 to 2025, have no text on the site. [`laws.csv`](laws.csv) lists every law with its day and folder; [`data/amendments.csv`](data/amendments.csv) lists the 5,542 rows of the Tables of Amendments and history notes, with the amending law and day each names.

Each Act is a folder in `acts/`, and each piece of subsidiary legislation one in `subsidiary/`, named after its title, with one file per provision, plus `title.md` (its name, Table of Amendments, long title and enacting words) and `index.txt` (its files in order): `acts/employment-relations-act-2012/s37.md` is section 37, Annual leave, of the Employment Relations Act 2012. Two older combined folders in `subsidiary/` are kept unchanged beside the four orders they held; [`data/path-corrections.json`](data/path-corrections.json) maps them, and they are not extra laws.

The text is in English, as cookislandslaws.gov.ck prints it, with each provision's history notes at its end; the Cook Islands Māori text of the Constitution Act, `subsidiary/papa-ture-metua-o-te-kuki-airani-ture-nui-1964/`, is here as the site files it.

## Questions as git commands

| Question | Command |
| --- | --- |
| Every change to section 37 of the Employment Relations Act (one so far, the current consolidation) | `git log -p --word-diff -- acts/employment-relations-act-2012/s37.md` |
| Which amending laws changed section 37, and from what day? | `grep -h '^\[' acts/employment-relations-act-2012/s37.md` |
| Every version of the Act, with the day each took effect | `git log --format="%h %(trailers:key=In-force,valueonly,separator=) %an" -- acts/employment-relations-act-2012` |
| Section 37 in one of those versions | `git show <commit>:acts/employment-relations-act-2012/s37.md` |

**Outside git**, we also host this record publicly, for free:

- **[Ask Claude about Cook Islands law](https://global-law.lexifina.com/v1/try_claude?country=cook-islands)**: opens Claude with a first question ready.
- **[Ask ChatGPT](https://global-law.lexifina.com/v1/try_chatgpt?country=cook-islands)**: the same question in ChatGPT.
- **[Search Cook Islands law on our site](https://lexifina.com/law?country=cook-islands&q=annual+leave)**: a search for "annual leave", with each provision's text and its versions, no account needed.
- **[Developer REST API](https://global-law.lexifina.com/v1/search_law?query=annual+leave&jurisdiction=cook-islands)**: the same search as JSON, with no key. See the [documentation here](https://lexifina.com/api/global-law).

Both assistants read the record through the free Global law connector (MCP, `https://global-law.lexifina.com/mcp`); the first time, the chat gives you the link that adds it. Ask in English.

**Host it yourself easily.** All it takes is git and Python, and the tools run on your machine:

```sh
git clone --depth 1 https://github.com/lexifina/global-law && cd global-law
python3 tools/countries.py add cook-islands/national/acts
python3 tools/law.py show 2026-11-01 cook-islands/national/acts/acts/employment-relations-act-2012/s37.md
```

Opened in Claude Code, Cursor, VS Code or Codex, the clone also starts a local MCP server with the same tools ([MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md)).

## Dates

Each commit is dated at noon, Pacific/Rarotonga, and carries its day in its `In-force:` trailer, with `In-force-basis:` naming the evidence:

- the latest day, on or before the retrieval day, on which the law's own record says a change took effect (a commencement in its Table of Amendments, or the day in a history note); for a law never amended, its own commencement; failing that, its assent or signature;
- for the 22 laws whose record gives no day, the retrieval day, 29 October 2026 (`In-force-basis: retrieved`);
- git cannot store dates before 1970, so the 103 laws in force earlier are dated 1970-01-01, with the real day in `In-force:`; `tools/in_force_on.py` reads the trailers, not the commit dates.

Every law-text commit is authored by `Cook Islands Legislative Service`, the publisher of the consolidation: no line is credited to an amending law, because without the earlier text nobody can tell which words an amendment wrote. Corrections are appended as their own commits (`Kind: correction`, with `Corrects:` and `Supersedes:`), and the commits they correct stay as published.

## How it is checked

- The build scripts are in `tools/build/` as they were run, with their sha256 in [`REPRODUCE.md`](REPRODUCE.md); [`data/source-sha256.tsv`](data/source-sha256.tsv) lists the sha256 of every answer from the site the build read.
- Rebuilding from the same answers gives the same commit hashes: the whole history is written in one sorted `git fast-import` stream with fixed dates.
- Before publication, the letters and digits of every file were compared with the source page's by a separate extractor; the history was checked for trailers that parse, no merges and no day after the build, and with global-law's `check_corpus.py`.
- History is append-only: corrections are added as new commits, and no published commit is rewritten.

## What it does not show

- **Earlier wording.** The site keeps no past versions (its historical view is empty for every law), so nothing before the current consolidation can be rebuilt from it.
- **The Constitution itself.** The Cook Islands Constitution Act 1964 is here, but its Schedule, the Constitution, reads only "Published separately in this consolidation", and that separate text is not in this record.
- **Laws as made** (the site's "Laws as published" PDFs), repealed laws the site no longer lists, and case law.
- **Images.** Forms, schedules and maps drawn as pictures are marked `[image]`.
- **Entries the site would not serve**: 75 rows in [`data/unreadable.csv`](data/unreadable.csv), 64 of them server errors, with the reason for each.

## Sources

| Source | Kind | Past versions | Notes |
| --- | --- | --- | --- |
| [cookislandslaws.gov.ck](https://cookislandslaws.gov.ck) (Cook Islands Legislative Service) | Consolidated legislation | no, the current text only | Each law's current text, Table of Amendments and history notes, read through the site's JSON API (see [`SOURCES.md`](SOURCES.md)) |

## Licence

See [`LICENSE`](LICENSE). Under the Copyright Act 2013 (Cook Islands), section 3, a "work" "does not include any work that is an official text, or a translation, of a legislative, administrative, or legal nature", so the texts are not protected by copyright; Lexifina's tools, file arrangement, commit messages and documentation are CC0 1.0.

## More

From [lexifina/global-law](https://github.com/lexifina/global-law):

- [FEATURES.md](https://github.com/lexifina/global-law/blob/main/FEATURES.md): every feature, and what every corpus must support (`git blame`, `law.py`, the MCP tools)
- [FAQ.md](https://github.com/lexifina/global-law/blob/main/FAQ.md): questions and answers · [CONTRIBUTING.md](https://github.com/lexifina/global-law/blob/main/CONTRIBUTING.md): proposing changes · [MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md): the MCP server · [REPRODUCE.md](https://github.com/lexifina/global-law/blob/main/REPRODUCE.md): how it was built · [CHANGELOG.md](https://github.com/lexifina/global-law/blob/main/CHANGELOG.md)
- [FRESHNESS.md](https://github.com/lexifina/global-law/blob/main/FRESHNESS.md): how current each corpus is · [Monitoring](https://github.com/lexifina/global-law/tree/main/monitoring): whether updates are running · [WATCHING.md](https://github.com/lexifina/global-law/blob/main/WATCHING.md): how each official source is watched for changes
- [performance/](https://github.com/lexifina/global-law/tree/main/performance): how fast the tools are, measured
- [visualisations/](https://github.com/lexifina/global-law/tree/main/visualisations): charts and bridges across the world's law
- [Vulnerabilities](https://github.com/lexifina/global-law/tree/main/vulnerabilities): mistakes in legislation as published
