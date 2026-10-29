"""README, REPRODUCE.md, SOURCES.md, LICENSE, corpus.json, laws.csv, data/ and tools for the Cook Islands law
repository (called by build.py)."""
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
REPO_FILES = HERE / 'repo'
CACHE = HERE / '.cache'
BUILD_FILES = ('fetch.py', 'build.py', 'docs.py')


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _csv(rows: list[list]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out, lineterminator='\n')
    for r in rows:
        w.writerow(r)
    return out.getvalue().encode('utf-8')


def source_sums() -> str:
    paths = [CACHE / 'acts.json'] + [p for sub in ('toc', 'front', 'pages') for p in sorted((CACHE / sub).glob('*'))
                                     if not p.name.endswith('.tmp')]
    return ''.join(f'{p.relative_to(CACHE).as_posix()}\t{_sha(p)}\n' for p in paths)


def render(laws: list[dict], commits: list[tuple], issues: list[dict], amend: list[list[str]], today: str,
           fetched_on: str) -> dict[str, bytes]:
    acts = [l for l in laws if l['kind'] == 'act']
    subs = [l for l in laws if l['kind'] == 'subsidiary']
    built = [l for l in laws if l.get('consolidated')]
    units = sum(l.get('units', 0) for l in laws)
    days = sorted(l['consolidated'] for l in built)
    table_rows = [r for r in amend if r[2] == 'table of amendments']
    note_rows = [r for r in amend if r[2] == 'note']
    amending = {r[3] for r in table_rows if r[3]}
    act_list = len(json.loads((CACHE / 'acts.json').read_text('utf-8')))

    laws_csv = _csv([['name', 'kind', 'parent_act', 'code', 'in_force', 'date_source', 'units', 'amendments_listed',
                      'history_notes', 'path']] +
                    [[l['name'], l['kind'], l['act'] if l['kind'] == 'subsidiary' else '', l['code'],
                      l.get('consolidated', ''), l.get('date_source', ''), l.get('units', 0),
                      l.get('amendments_listed', 0), l.get('notes', 0), l['dir'] + '/'] for l in laws])
    amend_csv = _csv([['law', 'unit', 'source', 'amending_law', 'dates', 'text']] + sorted(amend))
    issues_csv = _csv([['law', 'node', 'issue']] + [[i['law'], i['node'], i['issue']] for i in issues])

    stats = {
        'today': today, 'fetched_on': fetched_on, 'laws': len(laws), 'acts': len(acts), 'subsidiary': len(subs),
        'laws_with_text': len(built), 'units': units, 'commits': len(commits) + 1, 'consolidated': len(commits),
        'amendment': 0, 'unexplained': 0, 'first': days[0] if days else '', 'last': days[-1] if days else '',
        'amending_laws_listed': len(amending), 'table_of_amendment_rows': len(table_rows),
        'history_notes': len(note_rows), 'unreadable': len(issues), 'act_list': act_list,
        'retrieved_dated': sum(1 for l in built if l.get('date_source') == 'retrieved'),
        'future': sum(1 for i in issues if i['node'] == 'dates'),
        'in_force_by_decade': dict(sorted(Counter(d[:3] + '0s' for d in days).items())),
    }

    def fill(text: str) -> str:
        for k, v in stats.items():
            if isinstance(v, (str, int)):
                text = text.replace('{{' + k.upper() + '}}', str(v))
        for name in BUILD_FILES:
            text = text.replace('{{SHA_' + name.upper().replace('.', '_') + '}}', _sha(HERE / name))
        return text

    corpus = {
        'corpus': 'ck/national/acts',
        'name': 'Laws of the Cook Islands (consolidated Acts and subsidiary legislation)',
        'label': 'Cook Islands',
        'language': 'en',
        'history': 'current-only',
        'history_from': days[0] if days else '',
        'record_to': fetched_on,
        'checked_on': fetched_on,
        'record_note': ('cookislandslaws.gov.ck publishes only the current consolidation, so each law has one version '
                        'here: the text as retrieved on ' + fetched_on + ', dated by the latest day its own record '
                        '(Table of Amendments, history notes, commencement) gives for a change taking effect. '
                        'Earlier text is not available; the notes and tables are kept as text and in '
                        'data/amendments.csv.'),
        'built': today,
        'in_force_trailer': 'In-force',
        'baseline_trailer': 'Consolidated',
        'has_future_branch': False,
        'laws': {'acts': len(acts), 'subsidiary': len(subs)},
        'dates': {'commit': 'latest past commencement or history-note date of each law (In-force-basis trailer), '
                            'else its own commencement or assent, else the retrieval day',
                  'baseline_trailer': 'Consolidated', 'other_trailers': ['In-force-basis', 'Parent-act'],
                  'time': '12:00 Pacific/Rarotonga (UTC-10:30 until 1978-11-12; UTC-10 with half-hour summer time '
                          'until 1991-03-03; UTC-10 since)',
                  'before_1970': 'clamped to 1970-01-01; the real day is in the trailer'},
        'author': {'consolidated': 'Cook Islands Legislative Service', 'amendment': 'none yet',
                   'unexplained': 'Cook Islands Legislative Service'},
        'scope': {
            'trailer': 'Applies',
            'groups': 'any one line',
            'conditions': 'all of a line',
            'when_absent': 'not extracted for the Cook Islands; savings and transitional rules are in the amending laws',
            'default_reach': {
                'rule': 'presumption against retroactivity',
                'meaning': 'an enactment is presumed not to affect rights acquired, or proceedings begun, before it '
                           'took effect unless it says so',
                'authority': 'common-law presumption; the Acts Interpretation Act 1924 as in force in the Cook Islands '
                             '(in this repository) governs the effect of repeals',
                'decided_here': False,
            },
        },
        'tool': 'tools/in_force_on.py',
        'citation': {'file': '(acts/[^/]+)/s([0-9]+[a-z]*)\\.md',
                     'cites': '([Ss]ection|s\\.?) ?{n}([^0-9a-zA-Z]|$)'},
    }

    files = {
        'corpus.json': (json.dumps(corpus, indent=2, ensure_ascii=False) + '\n').encode('utf-8'),
        'README.md': fill((REPO_FILES / 'README.md').read_text('utf-8')).encode('utf-8'),
        'REPRODUCE.md': fill((REPO_FILES / 'REPRODUCE.md').read_text('utf-8')).encode('utf-8'),
        'SOURCES.md': fill((REPO_FILES / 'SOURCES.md').read_text('utf-8')).encode('utf-8'),
        'LICENSE': (REPO_FILES / 'LICENSE').read_bytes(),
        'laws.csv': laws_csv,
        'data/amendments.csv': amend_csv,
        'data/unreadable.csv': issues_csv,
        'data/stats.json': (json.dumps(stats, indent=1, sort_keys=True) + '\n').encode('utf-8'),
        'data/source-sha256.tsv': source_sums().encode('utf-8'),
        'tools/in_force_on.py': (REPO_FILES / 'tools' / 'in_force_on.py').read_bytes(),
    }
    for name in BUILD_FILES:
        files[f'tools/build/{name}'] = (HERE / name).read_bytes()
    for name in ('README.md', 'REPRODUCE.md', 'SOURCES.md', 'LICENSE'):
        files[f'tools/build/repo/{name}'] = (REPO_FILES / name).read_bytes()
    files['tools/build/repo/tools/in_force_on.py'] = (REPO_FILES / 'tools' / 'in_force_on.py').read_bytes()
    for k, v in files.items():
        if b'\r' in v:
            raise SystemExit(f'CR in {k}')
    return files
