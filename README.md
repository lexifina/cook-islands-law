# The laws of the Cook Islands, as a git repository

The consolidated legislation of the Cook Islands as a git repository: 272 Acts (including the Constitution of the Cook Islands) and 390 pieces of subsidiary legislation made under them. The source is [cookislandslaws.gov.ck](https://cookislandslaws.gov.ck), the consolidated-law database of the Legislative Service (Legislative Service Act 1968-69). There is one file per section, regulation, clause, rule, schedule or form (20669 files), with one paragraph per line, so `git blame` and `git diff` work line by line.

**What this repository is not, yet: a history.** cookislandslaws.gov.ck publishes only the current consolidated text of each law and keeps no earlier versions (its "historical" view is empty for every law). So each law is a single commit holding its whole current text. Nothing before that text can be rebuilt from this source. New consolidations will be added from now on as later commits, so the history grows forward from here. The amendment history the site prints is kept: each law's Table of Amendments (amending law, date of assent or signature, date of commencement) and the history note under each provision (`[Section 4(1) account: inserted, on 1 January 2022, by section 4 of the Banking Amendment Act 2019 (2019 No 10).]`) are in the files and in [`data/amendments.csv`](data/amendments.csv).

The record holds 658 laws, dated between 1908-08-04 and 2026-10-29, in 659 commits.

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What does section 4 of the Banking Act 2011 say? | `python tools/in_force_on.py 2026-10-29 acts/banking-act-2011 s4` |
| The whole of a law, in order | `python tools/in_force_on.py 2026-10-29 acts/banking-act-2011` |
| Which laws amended an Act, and when they commenced | `cat acts/banking-act-2011/title.md` (its Table of Amendments) |
| What a section's history notes say | `grep -h '^\[' acts/banking-act-2011/s4.md` |
| Every provision an amending Act touched, by its notes | `grep -i 'Banking Amendment Act 2019' data/amendments.csv` |
| What changed in a law since this build (after later builds) | `git log -p -- acts/banking-act-2011` |
| The list of laws, with their dates | [`laws.csv`](laws.csv) |

Each file starts with any Part or Division headings above it (`## Part 1 Preliminary`), then its own heading as the site prints it (`# 4 Interpretation`), then its paragraphs, one per line, and last the history notes, copied as they are. Each law's `title.md` holds its name, Table of Amendments, long title and enacting words; its `index.txt` lists its files in the order of the law. Subsidiary legislation is under `subsidiary/`, and its commit names its parent Act (`Parent-act:`).

## The dates, and which one we use

Each commit is dated, at noon Rarotonga time, by **the latest day on or before the retrieval day (2026-10-29) on which the law's own record says a change took effect**: the commencement dates in its Table of Amendments and the "on <date>" of its history notes; for a law never amended, its own commencement ("commenced on ..."); failing that, its assent or signature. That day is in the `In-force:` trailer, and `In-force-basis:` says which kind of evidence gave it. It is the earliest day from which the text here can be the text in force, assuming the consolidation is complete. For 24 laws the record gives no date at all; they are dated by the retrieval day (`In-force-basis: retrieved`). 0 laws name a date after the retrieval day in their record; they are listed in [`data/unreadable.csv`](data/unreadable.csv) and their text is as published.

Rarotonga time is hard-coded (tz Pacific/Rarotonga): UTC-10:30 until 12 November 1978, then UTC-10 with a half-hour summer time until 3 March 1991, and UTC-10 all year since. Commits before 1970 are dated 1970-01-01 (git cannot hold earlier dates); the real day is in the trailer. `tools/in_force_on.py` reads the trailers, not the commit dates.

## What "author" means

Every law-text commit has the same author: `Cook Islands Legislative Service <legislative-service@cookislandslaws-gov-ck.invalid>`, with `Kind: consolidated`. The address cannot exist. The author is the publisher of the consolidation, not a lawmaker. No line is credited to an amending law, because without the earlier text nobody can tell which words an amendment wrote. In the shared design for these repositories, a change is credited to an amending law only when the source shows the text before and after it. When later consolidations are added, a change will be credited to an amending law only where a new history note names it; otherwise it is labelled `Kind: unexplained` and authored by the publisher.

There are 658 consolidated commits, 0 amendment commits and 0 unexplained ones. The Tables of Amendments hold 967 rows naming 701 distinct amending laws, and the provisions carry 4575 history notes.

## What it does not show

- Any text before the current consolidation. The site has none.
- Laws as made: the site's "Laws as published" PDFs are not included.
- Repealed laws that the database no longer lists.
- Pictures (marked `[image]`).
- Table-of-contents entries the site would not serve (79 rows, with the reason, in [`data/unreadable.csv`](data/unreadable.csv)).

This is a research aid. The site's disclaimer excludes liability and says it is no substitute for legal advice; the same is true of this repository. It is not an official version.

## How it is checked

`tools/build/` holds the build as it was run. [`data/source-sha256.tsv`](data/source-sha256.tsv) has the sha256 of every cached answer the build read. The build is deterministic: from the same answers it gives the same commit hashes (see [`REPRODUCE.md`](REPRODUCE.md)). Before this build was called clean it was checked for: every file's letters and digits equal to the source page's, by a separate extractor; `tools/in_force_on.py` output for sample provisions; trailers that parse; no merges, no dates that go backwards, no dates after the build date, no carriage returns; two builds giving the same HEAD; `check_corpus.py` from global-law.

## How it is built

`fetch.py` reads the site's own JSON API (read from the site's JavaScript): the list of Acts (`retrieve_all_act`), each Act's table of contents (`retrieve_toc/<Act>`, which also lists its subsidiary legislation), each law's front page and every entry (`display_pages/<id>`). `build.py` turns each entry into lines, puts Part headings on the first file below them, and writes one commit per law with `git fast-import`. No AI model writes or changes any law text.

## Licence

Source: cookislandslaws.gov.ck, Cook Islands Legislative Service. The Copyright Act 2013 (Cook Islands), section 3, defines "work" so that it "does not include any work that is an official text, or a translation, of a legislative, administrative, or legal nature", so the texts carry no copyright. The site states no licence and no terms of use. The wording was not changed; it was only split into files and lines. Lexifina's own contributions (tools, arrangement, commit messages, documentation) are CC0. See [`LICENSE`](LICENSE) and [`SOURCES.md`](SOURCES.md). This repository is private.
