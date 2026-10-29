"""Build the Cook Islands law repository from the cookislandslaws.gov.ck cache (fetch.py).

    python scripts/cook-islands-law/build.py ~/Documents/cook-islands-law --today YYYY-MM-DD [--limit N]

cookislandslaws.gov.ck (the Legislative Service's consolidated-law database) publishes the current consolidated
text of every Act and of the subsidiary legislation made under it, with a Table of Amendments per law (amending
law, date of assent or signature, date of commencement) and NZ-style history notes under each provision
("[Section 4(1) account: inserted, on 1 January 2022, by section 4 of the Banking Amendment Act 2019 (2019 No 10).]").
It keeps no earlier text (its "historical" view returns nothing for every law), so the record is current-only:

1. Every Act and every piece of subsidiary legislation is one law. Each node of its table of contents (section,
   regulation, clause, rule, schedule, form, schedule part) is one file, one paragraph per line; Part and Division
   headings from the table of contents go on top of the first file under them as `##` lines. The law's front page
   (name, Table of Amendments, long title, enacting words) is `title.md`.
2. Each law is one commit, `Kind: consolidated`, authored by the Legislative Service, dated noon Rarotonga time on
   the latest date on or before the retrieval day that the law's own record gives for a change taking effect: the
   commencement dates in its Table of Amendments and the "on <date>" of its history notes, else its own
   commencement, else the retrieval day. The `In-force:` trailer carries that day and `In-force-basis:` says which.
   Nobody is credited with single lines: the text before each amendment is not published. The notes stay in the
   files and are listed in data/amendments.csv.
3. The whole history is written in one git fast-import, so the same cache always gives the same hashes.
"""
import argparse
import csv
import io
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from fetch import CACHE, key, walk_ids  # noqa: E402

COMMITTER = 'Lexifina <cook-islands-law@lexifina.com>'
PUBLISHER = ('Cook Islands Legislative Service', 'legislative-service@cookislandslaws-gov-ck.invalid')
SITE = 'https://cookislandslaws.gov.ck'
MONTHS = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                      'september', 'october', 'november', 'december'], 1)}
DATE_RE = re.compile(r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|'
                     r'December)\s+(\d{4})\b')


def days_in(s: str) -> list[str]:
    out = []
    for d, m, y in DATE_RE.findall(s or ''):
        try:
            out.append(date(int(y), MONTHS[m.lower()], int(d)).isoformat())
        except ValueError:
            pass
    return out


# ---------------------------------------------------------------------------------------------------- html

BLOCK = {'p', 'div', 'li', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'table', 'tr', 'blockquote',
         'dl', 'thead', 'tbody', 'center', 'body', 'html'}
HEAD = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}


def norm(s: str) -> str:
    s = s.replace('\xa0', ' ').replace(' ', ' ').replace('​', '').replace('\xad', '').replace('﻿', '')
    return re.sub(r'\s+', ' ', s).strip()


class ToLines(HTMLParser):
    """HTML -> one line per paragraph; headings get '#'; table cells joined with ' | '; hidden markers skipped."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self.cur: list[str] = []
        self.stack: list[tuple[str, bool]] = []
        self.skip = 0
        self.cell = 0
        self.cells_in_row = 0
        self.head = 0

    def flush(self):
        t = norm(''.join(self.cur))
        if t:
            self.lines.append(('# ' if self.head else '') + t)
        self.cur = []

    def handle_starttag(self, tag, attrs):
        if tag in ('col', 'colgroup', 'img', 'br', 'hr', 'input', 'meta', 'link'):
            if self.skip:
                return
            if tag == 'img':
                self.cur.append(' [image] ')
            elif tag == 'br':
                if self.cell:
                    self.cur.append(' ')
                else:
                    self.flush()
            return
        cls = (dict(attrs).get('class') or '').split()
        skip = tag in ('style', 'script') or 'hidden' in cls or 'hiddendiv' in cls
        self.stack.append((tag, skip))
        if skip:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in ('td', 'th'):
            if self.cells_in_row:
                self.cur.append(' | ')
            self.cells_in_row += 1
            self.cell += 1
            return
        if tag == 'tr':
            self.flush()
            self.cells_in_row = 0
            return
        if tag in BLOCK:
            if self.cell:
                self.cur.append(' ')
            else:
                self.flush()
                if tag in HEAD:
                    self.head += 1

    def handle_endtag(self, tag):
        idx = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), None)
        if idx is None:
            return
        popped = self.stack[idx:]
        del self.stack[idx:]
        was_skip = any(sk for _, sk in popped)
        for _, sk in popped:
            if sk:
                self.skip -= 1
        if was_skip or self.skip:
            return
        heads_closed = sum(1 for t, _ in popped if t in HEAD)
        if tag in ('td', 'th'):
            self.cell = max(0, self.cell - 1)
            return
        if tag == 'tr':
            self.flush()
            self.cells_in_row = 0
            return
        if tag in BLOCK:
            if self.cell:
                self.cur.append(' ')
            else:
                self.flush()
        self.head = max(0, self.head - heads_closed)

    def handle_data(self, data):
        if not self.skip:
            self.cur.append(data)

    def close(self):
        super().close()
        self.flush()


def html_lines(h: str) -> list[str]:
    p = ToLines()
    p.feed(h or '')
    p.close()
    return p.lines


def page_body(h: str) -> str:
    """A node page repeats the law name and the Part heading above the node; the node starts at the first hidden
    marker (`<div class="hiddendiv" data-value=...>`)."""
    i = h.find('<div class="hiddendiv"')
    return h[i:] if i >= 0 else h


# ---------------------------------------------------------------------------------------------------- tree

def slug(t: str) -> str:
    t = t.lower().replace('&', ' and ').replace('’', '').replace("'", '')
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    return t[:90].rstrip('-') or 'law'


def law_code(parent_id: str) -> str:
    return '.'.join(parent_id.split('.')[:3])


def unit_id(node_id: str, code: str) -> str:
    s = re.sub(r'_htm$', '', node_id)
    flat = code.replace('.', '_').replace('-', '_')
    s2 = s.replace('-', '_')
    i = s2.find(flat + '_')
    u = s[i + len(flat) + 1:] if i >= 0 else s.split('_', 1)[-1]
    return re.sub(r'[^0-9A-Za-z._-]', '-', u).lower() or 'unit'


def flatten(entries, heads: list[str], out: list):
    """TOC list -> [(node, [headings above it])] in order; dict keys that are not nodes are headings."""
    for e in entries:
        if not isinstance(e, dict):
            continue
        if 'id' in e and 'name' in e:
            out.append((e, list(heads)))
            continue
        for k, v in e.items():
            flatten(v if isinstance(v, list) else [v], heads + [norm(k)], out)


def load_laws(limit: int | None) -> list[dict]:
    acts = json.loads((CACHE / 'acts.json').read_text('utf-8'))
    laws: list[dict] = []
    for a in sorted(acts, key=lambda a: (a['ActName'], a['LegalId'])):
        toc = json.loads((CACHE / 'toc' / f"{key(a['ActName'])}.json").read_text('utf-8'))
        for top, blocks in toc.items():
            for blk in blocks if isinstance(blocks, list) else []:
                if not isinstance(blk, dict):
                    continue
                for name, entries in blk.items():
                    nodes: list = []
                    flatten(entries if isinstance(entries, list) else [entries], [], nodes)
                    if not nodes:
                        continue
                    code = law_code(nodes[0][0].get('parent_id') or '')
                    is_act = norm(name).lower() == norm(a['ActName']).lower()
                    laws.append({'act': a['ActName'], 'act_legal_id': a['LegalId'], 'name': norm(name),
                                 'kind': 'act' if is_act else 'subsidiary', 'code': code, 'nodes': nodes,
                                 'year': a.get('Year', '')})
    # folders: acts/<slug>, subsidiary/<slug>; deterministic tie-break by code
    used: dict[str, str] = {}
    for law in sorted(laws, key=lambda l: (l['kind'], l['name'], l['code'])):
        base = f"{'acts' if law['kind'] == 'act' else 'subsidiary'}/{slug(law['name'])}"
        d, k = base, 2
        while d in used and used[d] != law['code']:
            d = f'{base}-{k}'
            k += 1
        used[d] = law['code']
        law['dir'] = d
    seen = set()
    laws = [l for l in sorted(laws, key=lambda l: l['dir']) if not (l['dir'] in seen or seen.add(l['dir']))]
    return laws[:limit] if limit else laws


NOTE_RE = re.compile(r'^\[[^\[\]]*\b(?:inserted|amended|replaced|repealed|substituted|revoked|renumbered|added|'
                     r'omitted|expired|corrected)\b[^\[\]]*\]$', re.I)


def build_law(law: dict, today: str) -> dict:
    files: dict[str, str] = {}
    order: list[str] = []
    amend: list[list[str]] = []
    issues: list[dict] = []
    evidence: list[tuple[str, str]] = []  # (day, basis)
    front = CACHE / 'front' / f"{key(law['name'])}.html"
    if front.exists():
        lines = html_lines(front.read_text('utf-8'))
        files[f"{law['dir']}/title.md"] = '\n'.join(lines) + '\n'
        order.append('title.md')
        for l in lines:
            cells = [c.strip() for c in l.split(' | ')]
            if len(cells) == 3 and cells[0] not in ('Amending Legislation',):
                ds = days_in(cells[2])
                amend.append([law['dir'], 'title', 'table of amendments', cells[0], '; '.join(ds), l])
                evidence += [(d, 'commencement in the Table of Amendments') for d in ds]
            m = re.search(r'\b(?:commenced|came into force) on (\d{1,2} \w+ \d{4})', l)
            if m and not l.startswith('#'):
                evidence += [(d, "the law's own commencement") for d in days_in(m.group(1))]
            m = re.search(r'\b(?:assented to|signed|made) on (\d{1,2} \w+ \d{4})', l)
            if m and not l.startswith('#'):
                evidence += [(d, "the law's assent or signature") for d in days_in(m.group(1))]
    else:
        issues.append({'law': law['name'], 'node': 'front page', 'issue': 'not fetched'})
    pending: list[str] = []
    last_heads: list[str] = []
    seen_ids: dict[str, int] = {}
    for node, heads in law['nodes']:
        # headings that changed since the previous node go on top of this node's file
        common = 0
        while common < min(len(heads), len(last_heads)) and heads[common] == last_heads[common]:
            common += 1
        pending += ['#' * min(2 + i, 6) + ' ' + h for i, h in enumerate(heads) if i >= common and h]
        last_heads = heads
        p = CACHE / 'pages' / f"{key(node['id'])}.html"
        if not p.exists():
            issues.append({'law': law['name'], 'node': node['id'],
                           'issue': 'no page (server error)' if p.with_suffix('.html.err').exists() else 'not fetched'})
            continue
        lines = html_lines(page_body(p.read_text('utf-8')))
        if not lines:
            issues.append({'law': law['name'], 'node': node['id'], 'issue': 'empty page'})
            continue
        uid = unit_id(node['id'], law['code'])
        if uid in seen_ids:
            seen_ids[uid] += 1
            uid = f'{uid}~{seen_ids[uid]}'
        else:
            seen_ids[uid] = 1
        files[f"{law['dir']}/{uid}.md"] = '\n'.join([*pending, *lines]) + '\n'
        pending = []
        order.append(f'{uid}.md')
        for l in lines:
            if NOTE_RE.match(l):
                ds = days_in(l)
                m = re.search(r'\bby (.*?)\s*\.?\]$', l)
                amend.append([law['dir'], uid, 'note', m.group(1) if m else '', '; '.join(ds), l])
                evidence += [(d, 'history notes') for d in ds]
    if pending:
        files[f"{law['dir']}/headings.md"] = '\n'.join(pending) + '\n'
        order.append('headings.md')
    if files:
        files[f"{law['dir']}/index.txt"] = '\n'.join(order) + '\n'
    past = [e for e in evidence if e[0] <= today]
    future = sorted({e[0] for e in evidence if e[0] > today})
    # the latest change date; the basis names every kind of evidence for that day
    day = max((e[0] for e in past), default=None)
    basis = sorted({b for d, b in past if d == day})
    if future:
        issues.append({'law': law['name'], 'node': 'dates', 'issue': f'dates after {today} in its record: '
                       + ', '.join(future) + ' (text as published; dated by the latest past date)'})
    return {'files': files, 'amend': amend, 'issues': issues, 'day': day, 'basis': basis, 'future': future}


# ---------------------------------------------------------------------------------------------------- time

def first_sunday(y: int, m: int) -> date:
    d = date(y, m, 1)
    return d + timedelta(days=(6 - d.weekday()) % 7)


def last_sunday(y: int, m: int) -> date:
    d = date(y, m + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def offset(day: date) -> int:
    """Minutes east of UTC at noon in Rarotonga (tz Pacific/Rarotonga): -10:30 until 1978-11-12; then -10:00 with
    a half-hour summer time from 1978-11-12, and from the last Sunday of October 1979-1990, to the first Sunday of
    March 1979-1991; -10:00 all year since 1991-03-03."""
    if day < date(1978, 11, 12):
        return -630
    y = day.year
    if y <= 1991 and day < first_sunday(y, 3):
        return -570
    if 1979 <= y <= 1990 and day >= last_sunday(y, 10):
        return -570
    if y == 1978:
        return -570
    return -600


def git_date(day: str, seq: int) -> str:
    d = date.fromisoformat(day)
    off = offset(d)
    sign = '-' if off < 0 else '+'
    tz = f'{sign}{abs(off) // 60:02d}{abs(off) % 60:02d}'
    if d.year < 1970:  # clamped: noon local time on 1970-01-01, plus seq seconds to keep the order
        return f'{12 * 3600 - off * 60 + seq} {tz}'
    ts = int(datetime(d.year, d.month, d.day, 12, tzinfo=timezone(timedelta(minutes=off))).timestamp())
    return f'{ts} {tz}'


# ---------------------------------------------------------------------------------------------------- write

def message(law: dict, day: str, built: dict, src: str) -> str:
    n_notes = sum(1 for r in built['amend'] if r[2] == 'note')
    n_table = sum(1 for r in built['amend'] if r[2] == 'table of amendments')
    label = law['name'] if law['kind'] == 'act' else f"{law['name']} (under the {law['act'].title()})"
    if src == 'retrieved':
        first = (f'The text of the {label} as cookislandslaws.gov.ck publishes it. Its record gives no date for a '
                 f'change taking effect, so it is dated by the day it was retrieved, {day}.')
    else:
        first = (f'The text of the {label} as cookislandslaws.gov.ck publishes it, dated by the latest day its own '
                 f"record gives for a change taking effect: {day} ({', '.join(built['basis'])}).")
    body = [first, '',
            'The site keeps no earlier versions, so this commit holds the whole text and nobody is credited with',
            'single lines. The amendment history the site prints stays in the files: the Table of Amendments in',
            f'title.md ({n_table} rows) and the history notes under provisions ({n_notes} notes).']
    if built['future']:
        body += ['', 'Its record also names later dates (' + ', '.join(built['future']) + '); the text is as',
                 'published on the retrieval day.']
    trailers = ['Kind: consolidated', f'In-force: {day}', f'Consolidated: {day}',
                f"In-force-basis: {'retrieved' if src == 'retrieved' else '; '.join(built['basis'])}",
                f"Law: {law['name']}", f"Law-kind: {law['kind']}"]
    if law['kind'] == 'subsidiary':
        trailers.append(f"Parent-act: {law['act'].title()}")
    trailers.append(f"Source: {SITE}/#/ (law code {law['code']})")
    subject = f"{law['name']}: as consolidated on cookislandslaws.gov.ck, in force from {day}"
    if src == 'retrieved':
        subject = f"{law['name']}: as consolidated on cookislandslaws.gov.ck, retrieved {day}"
    return '\n'.join([subject, '', *body, '', *trailers]) + '\n'


def fast_import(repo: Path, commits: list[tuple], docs: dict[str, bytes], today: str) -> None:
    buf = io.BytesIO()
    w = buf.write
    seq = 0
    name, email = PUBLISHER
    for day, law, built, src in commits:
        seq += 1
        when = git_date(day, seq)
        w(b'commit refs/heads/main\n')
        w(f'author {name} <{email}> {when}\ncommitter {COMMITTER} {when}\n'.encode())
        m = message(law, day, built, src).encode('utf-8')
        w(f'data {len(m)}\n'.encode() + m + b'\n')
        for path, text in sorted(built['files'].items()):
            t = text.encode('utf-8')
            w(f'M 100644 inline {path}\ndata {len(t)}\n'.encode() + t + b'\n')
        w(b'\n')
    when = git_date(today, seq + 1)
    msg = (f'Documentation: README, REPRODUCE, SOURCES, tools, laws.csv and data\n\n'
           f'Built from the cookislandslaws.gov.ck cache on {today}.\n\nKind: documentation\n').encode()
    w(b'commit refs/heads/main\n')
    w(f'author {COMMITTER} {when}\ncommitter {COMMITTER} {when}\n'.encode())
    w(f'data {len(msg)}\n'.encode() + msg + b'\n')
    for path, data in sorted(docs.items()):
        w(f'M 100644 inline {path}\ndata {len(data)}\n'.encode() + data + b'\n')
    w(b'\n')
    r = subprocess.run(['git', '-C', str(repo), 'fast-import', '--quiet', '--force'], input=buf.getvalue(),
                       capture_output=True)
    if r.returncode:
        sys.exit(r.stderr.decode('utf-8', 'replace')[-3000:])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', type=Path)
    ap.add_argument('--today', required=True)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--stats', action='store_true', help='parse and report only; write nothing')
    args = ap.parse_args()
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', args.today):
        sys.exit('--today must be YYYY-MM-DD')
    fo = CACHE / 'fetched_on.txt'
    fetched_on = fo.read_text('utf-8').strip() if fo.exists() else args.today
    if fetched_on > args.today:
        sys.exit(f'retrieval date {fetched_on} is after --today')

    laws = load_laws(args.limit)
    commits, issues, amend = [], [], []
    for law in laws:
        built = build_law(law, fetched_on)
        issues += built['issues']
        amend += built['amend']
        law['units'] = sum(1 for p in built['files'] if not p.endswith(('/title.md', '/index.txt', '/headings.md')))
        law['amendments_listed'] = sum(1 for r in built['amend'] if r[2] == 'table of amendments')
        law['notes'] = sum(1 for r in built['amend'] if r[2] == 'note')
        if not built['files']:
            law['consolidated'] = ''
            issues.append({'law': law['name'], 'node': law['code'], 'issue': 'no text'})
            continue
        src = 'record'
        day = built['day']
        if not day:
            day, src = fetched_on, 'retrieved'
        law['consolidated'] = day
        law['date_source'] = src
        commits.append((day, law, built, src))
    commits.sort(key=lambda c: (c[0], c[1]['dir']))
    print(f'{len(laws)} laws, {len(commits)} commits, {len(issues)} issues, {len(amend)} amendment rows, '
          f"{sum(l['units'] for l in laws)} units", flush=True)
    if args.stats:
        from collections import Counter
        print(Counter(i['issue'].split(' (')[0][:40] for i in issues).most_common(10))
        return

    import docs as docmod
    docs = docmod.render(laws, commits, issues, amend, args.today, fetched_on)

    repo = args.repo
    repo.mkdir(parents=True, exist_ok=True)
    remote = None
    if (repo / '.git').exists():
        r = subprocess.run(['git', '-C', str(repo), 'remote', 'get-url', 'origin'], capture_output=True, text=True)
        remote = r.stdout.strip() or None
        import os
        import shutil
        import stat

        def onerr(func, path, _):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(repo / '.git', onerror=onerr)
        for child in repo.iterdir():
            shutil.rmtree(child, onerror=onerr) if child.is_dir() else child.unlink()
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'core.autocrlf', 'false'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'core.longpaths', 'true'], check=True)
    if remote:
        subprocess.run(['git', '-C', str(repo), 'remote', 'add', 'origin', remote], check=True)
    fast_import(repo, commits, docs, args.today)
    subprocess.run(['git', '-C', str(repo), 'checkout', '-q', '-f', 'main'], check=True)
    head = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    count = subprocess.run(['git', '-C', str(repo), 'rev-list', '--count', 'HEAD'], capture_output=True, text=True).stdout.strip()
    print(f'built {repo}: {count} commits, head {head}', flush=True)


if __name__ == '__main__':
    main()
