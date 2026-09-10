#!/usr/bin/env python3
"""Maintain canonical sitemaps and notify IndexNow after a successful Pages build.

Standard library only. Run `python scripts/seo.py --help` from the repository.
"""
import argparse
from datetime import date
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.canonical = ''
        self.title = ''
        self.description = ''
        self.noindex = False
        self.tokens = []
        self.in_title = False
        self.skip = None
        self.schema = False
        self.schema_text = ''
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'script':
            self.schema = a.get('type') == 'application/ld+json'
            self.schema_text = ''
            self.skip = 'script'
            return
        if tag == 'style':
            self.skip = 'style'
            return
        if self.skip:
            return
        if tag == 'title':
            self.in_title = True
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonical = a.get('href', '')
        if tag == 'meta':
            name = a.get('name', '').lower()
            if name == 'description':
                self.description = a.get('content', '')
            if name == 'robots':
                self.noindex = 'noindex' in a.get('content', '').lower()
            if name in {'description', 'robots'}:
                self.tokens.append((name, a.get('content', '')))
        if tag in {'a', 'img'}:
            self.tokens.append((tag, a.get('href', a.get('src', '')), a.get('alt', '')))

    def handle_endtag(self, tag):
        if tag == self.skip:
            if self.schema:
                self.tokens.append(('schema', json.dumps(json.loads(self.schema_text), sort_keys=True)))
            self.skip = None
            self.schema = False
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.schema:
            self.schema_text += data
        if self.skip:
            return
        value = ' '.join(data.split())
        if self.in_title:
            self.title += value
        if value:
            self.tokens.append(('text', value))

    def fingerprint(self):
        return sha256(json.dumps([self.canonical, self.tokens], ensure_ascii=False).encode()).hexdigest()


def host():
    value = (ROOT / 'CNAME').read_text().strip()
    if not re.fullmatch(r'[a-z0-9.-]+', value):
        raise ValueError('CNAME must contain one hostname.')
    return value


def validate_url(url):
    u = urlsplit(url)
    if u.scheme != 'https' or u.netloc != host() or u.query or u.fragment:
        raise ValueError(f'Expected a canonical HTTPS URL on {host()}: {url}')


def pages():
    result = {}
    for p in sorted(ROOT.rglob('*.html')):
        if any(part.startswith('.') or part in {'scripts', 'tests', 'docs'} for part in p.relative_to(ROOT).parts):
            continue
        page = Page(p.read_text())
        if page.noindex:
            continue
        if not page.canonical:
            raise ValueError(f'Missing canonical: {p.relative_to(ROOT)}')
        validate_url(page.canonical)
        if not page.title or not page.description:
            raise ValueError(f'Missing title or description: {p.relative_to(ROOT)}')
        relative = p.relative_to(ROOT).as_posix()
        route = '/' if relative == 'index.html' else '/' + relative.removesuffix('index.html')
        if urlsplit(page.canonical).path != route:
            raise ValueError(f'Canonical does not match file route: {relative}')
        if page.canonical in result:
            raise ValueError(f'Duplicate canonical: {page.canonical}')
        result[page.canonical] = (p, page)
    return result


def sitemap_entries():
    path = ROOT / 'sitemap.xml'
    if not path.exists():
        return {}
    result = {}
    for item in ET.parse(path).getroot().findall(f'{{{NS}}}url'):
        url = item.findtext(f'{{{NS}}}loc')
        if url in result:
            raise ValueError(f'Duplicate sitemap URL: {url}')
        result[url] = item.findtext(f'{{{NS}}}lastmod')
    return result


def at_ref(ref, path):
    r = subprocess.run(['git', 'show', f'{ref}:{path}'], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def significant_paths(base, head):
    names = git('diff', '--name-only', '--no-renames', base, head, '--', '*.html').splitlines()
    changed = []
    for name in names:
        before, after = at_ref(base, name), at_ref(head, name)
        old = Page(before) if before is not None else None
        new = Page(after) if after is not None else None
        if old and new and old.fingerprint() == new.fingerprint():
            continue
        changed.append((name, old, new))
    return changed


def update_sitemap(as_of):
    today = date.fromisoformat(as_of) if as_of else date.today()
    old = sitemap_entries()
    ET.register_namespace('', NS)
    root = ET.Element(f'{{{NS}}}urlset')
    for url, (path, page) in pages().items():
        relative = path.relative_to(ROOT).as_posix()
        original = at_ref('HEAD', relative)
        modified = original is None or Page(original).fingerprint() != page.fingerprint()
        lastmod = today.isoformat() if modified or not old.get(url) else old[url]
        node = ET.SubElement(root, f'{{{NS}}}url')
        ET.SubElement(node, f'{{{NS}}}loc').text = url
        ET.SubElement(node, f'{{{NS}}}lastmod').text = lastmod
    ET.indent(root, space='  ')
    (ROOT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode') + '\n')
    print(f'Sitemap updated: {len(root)} canonical pages; unchanged dates preserved.')


def check():
    current, entries = pages(), sitemap_entries()
    if set(current) != set(entries):
        raise ValueError(f'Sitemap mismatch. Missing: {set(current)-set(entries)}; extra: {set(entries)-set(current)}')
    for url, lastmod in entries.items():
        if not lastmod or date.fromisoformat(lastmod) > date.today():
            raise ValueError(f'Invalid/future lastmod for {url}: {lastmod}')
    config = json.loads((ROOT / 'indexnow.json').read_text())
    key = config['key']
    if not re.fullmatch(r'[a-zA-Z0-9-]{8,128}', key):
        raise ValueError('Invalid IndexNow verification key.')
    if (ROOT / f'{key}.txt').read_text().strip() != key:
        raise ValueError('IndexNow verification file does not match configuration.')
    if f'Sitemap: https://{host()}/sitemap.xml' not in (ROOT / 'robots.txt').read_text():
        raise ValueError('robots.txt does not reference the canonical sitemap.')
    print(f'Validated {len(current)} pages, canonical URLs, sitemap dates and IndexNow verification file.')


def request(url, data=None, headers=None):
    req = Request(url, data=data, headers={'User-Agent': 'SetuCrest-Publishing/1.0', **(headers or {})})
    for attempt in range(3):
        try:
            with urlopen(req, timeout=25) as response:
                return response.status, response.read().decode('utf-8')
        except HTTPError as e:
            if (e.code == 429 or e.code >= 500) and attempt < 2:
                time.sleep(min(10, int(e.headers.get('Retry-After', '5')) if e.headers.get('Retry-After', '5').isdigit() else 5))
                continue
            raise
        except URLError:
            if attempt == 2:
                raise
            time.sleep(5)


def deployment_base(event, head):
    run = event.get('workflow_run')
    if not run:
        raise ValueError('Use --base for a manual dry run; automatic submission requires a completed Pages workflow event.')
    if run.get('conclusion') != 'success' or run.get('head_branch') != 'main' or run.get('name') != 'pages build and deployment':
        raise ValueError('Submission requires a successful main-branch Pages build.')
    if run['head_sha'] != head:
        raise ValueError('Checkout does not match the deployed commit.')
    repo = os.environ['GITHUB_REPOSITORY']
    if run.get('head_repository', {}).get('full_name') != repo:
        raise ValueError('Deployment must originate from this repository.')
    headers = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'}
    candidates = []
    for page in range(1, 6):
        url = f'https://api.github.com/repos/{repo}/actions/workflows/{run["workflow_id"]}/runs?branch=main&status=success&per_page=100&page={page}'
        _, text = request(url, headers=headers)
        data = json.loads(text)['workflow_runs']
        candidates.extend(x for x in data if x['id'] != run['id'] and x['run_number'] < run['run_number'])
        if candidates or len(data) < 100:
            break
    if not candidates:
        raise ValueError('No earlier successful deployment found; refusing to guess the submission range.')
    previous = max(candidates, key=lambda x: x['run_number'])
    return previous['head_sha']


def notify(base=None, dry_run=False):
    check()
    head = git('rev-parse', 'HEAD')
    if not base:
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
        base = deployment_base(event, head)
    if subprocess.run(['git', 'merge-base', '--is-ancestor', base, head], cwd=ROOT).returncode:
        raise ValueError('Earlier deployment is not an ancestor; review the range before submitting.')
    changes = significant_paths(base, head)
    urls = set()
    for _, old, new in changes:
        if old and old.canonical and not old.noindex:
            urls.add(old.canonical)
        if new and new.canonical and not new.noindex:
            urls.add(new.canonical)
    for url in urls:
        validate_url(url)
    config = json.loads((ROOT / 'indexnow.json').read_text())
    key = config['key']
    payload = {'host': host(), 'key': key, 'keyLocation': f'https://{host()}/{key}.txt', 'urlList': sorted(urls)}
    if dry_run:
        print(json.dumps({'base': base, 'head': head, 'urlList': payload['urlList']}, indent=2))
        return
    if not urls:
        print('No meaningful HTML changes since the previous successful deployment; no submission.')
        return
    status, public_key = request(payload['keyLocation'])
    if status != 200 or public_key.strip() != key:
        raise ValueError('Public key file is not ready; no URLs submitted.')
    current = pages()
    for url in sorted(urls):
        try:
            status, content = request(url)
        except HTTPError as e:
            if url not in current and e.code in {404, 410}:
                continue
            raise
        if url in current:
            if status != 200 or Page(content).fingerprint() != current[url][1].fingerprint():
                raise ValueError(f'Live content does not yet match the deployed source: {url}')
        elif status == 200:
            if Page(content).canonical == url:
                raise ValueError(f'Removed URL is still serving its original page: {url}')
    for start in range(0, len(payload['urlList']), 10000):
        batch = {**payload, 'urlList': payload['urlList'][start:start + 10000]}
        status, _ = request('https://api.indexnow.org/indexnow', json.dumps(batch).encode(), {'Content-Type': 'application/json; charset=utf-8'})
        if status not in {200, 202}:
            raise ValueError(f'IndexNow returned unexpected status {status}.')
        print(f'IndexNow received {len(batch["urlList"])} URLs (HTTP {status}); indexing is not guaranteed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    sm = subs.add_parser('sitemap', help='Update sitemap before committing edited pages.')
    sm.add_argument('--date', help='Editorial date (YYYY-MM-DD); defaults to today.')
    subs.add_parser('check', help='Check page metadata, sitemap and verification configuration.')
    ix = subs.add_parser('indexnow', help='Notify participating engines after a successful Pages deployment.')
    ix.add_argument('--base', help='Explicit earlier commit for an offline dry run only.')
    ix.add_argument('--dry-run', action='store_true', help='List changed URLs without network submission.')
    args = parser.parse_args()
    if args.command == 'sitemap':
        update_sitemap(args.date)
    elif args.command == 'check':
        check()
    else:
        if args.base and not args.dry_run:
            parser.error('--base requires --dry-run; real submissions must follow a successful Pages event.')
        notify(args.base, args.dry_run)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f'Publishing check failed: {error}', file=sys.stderr)
        sys.exit(1)
