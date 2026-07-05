#!/usr/bin/env python3
"""
Build local JSON catalogs for Messier, NGC and IC by scraping Wikipedia list pages.

Run this script from the repository root:

    python backend/scripts/build_catalogs.py

It writes files to `backend/data/`:
 - messier.json
 - ngc.json
 - ic.json

This is a helper to expand the local catalogs; it's tolerant to slight table variations.
"""
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUT_DIR = Path(__file__).resolve().parents[1] / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Use a session with a browser-like User-Agent to avoid 403 from Wikipedia
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
}
session = requests.Session()
session.headers.update(DEFAULT_HEADERS)


def parse_wikitable(table):
    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    rows = []
    for tr in table.find_all('tr'):
        cells = [td.get_text(strip=True) for td in tr.find_all(['td','th'])]
        if not cells:
            continue
        # If header row, skip
        if any(h.lower() in ' '.join(cells).lower() for h in ['messier','ngc','ic']):
            continue
        rows.append(cells)
    return headers, rows


def fetch_wiki_fields(href: str):
    """Fetch name/type/distance/constellation/description from a Wikipedia object page link (href starts with /wiki/)."""
    result = {}
    try:
        obj_url = 'https://en.wikipedia.org' + href
        robj = session.get(obj_url, timeout=20)
        robj.raise_for_status()
        soup_o = BeautifulSoup(robj.text, 'html.parser')
        
        # description: first meaningful paragraph
        desc = ''
        for p in soup_o.select('p'):
            # Use get_text(' ') to preserve spaces between elements
            t = p.get_text(' ', strip=True)
            if len(t) > 60:
                # Remove reference markers like [1], [2] more carefully
                # Replace them with space if adjacent to letters
                t = re.sub(r'\[\s*\d+\s*\]', ' ', t)
                # Remove remaining bracket references and clean up spaces
                t = re.sub(r'\s+', ' ', t).strip()
                desc = t
                break
        if desc:
            result['description'] = desc
        
        inf = soup_o.find('table', class_=re.compile('infobox'))
        if inf:
            for row in inf.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                if not th or not td:
                    continue
                key = th.get_text(' ', strip=True).lower()
                # Use get_text(' ') to preserve spaces between elements, then normalize
                val = td.get_text(' ', strip=True)
                # Clean up multiple spaces and reference markers
                val = re.sub(r'\[\s*\d+\s*\]', ' ', val)
                val = re.sub(r'\s+', ' ', val).strip()
                
                if 'type' in key and 'type' not in result:
                    result['type'] = val
                if 'constellation' in key and 'constellation' not in result:
                    result['constellation'] = val
                if 'distance' in key and 'distance' not in result:
                    result['distance'] = val
        
        # name from page title if available
        title = soup_o.find('h1', id='firstHeading')
        if title and title.get_text(strip=True):
            result['name'] = title.get_text(strip=True)
    except Exception:
        pass
    return result


def build_messier():
    url = 'https://en.wikipedia.org/wiki/List_of_Messier_objects'
    print('Fetching Messier list...')
    r = session.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')

    # Find the table that contains M1 in its text
    table = None
    for t in soup.find_all('table', class_='wikitable'):
        if 'M1' in t.get_text():
            table = t
            break

    messier = {}
    if not table:
        print('Messier table not found; aborting messier build.')
        return messier

    # Map columns based on table headers to capture canonical name, type, distance, constellation
    headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
    # create mapping from header keywords to index
    header_map = {}
    for i, h in enumerate(headers):
        if 'messier' in h or h.strip().startswith('m'):
            header_map['designation'] = i
        if 'other' in h or 'ngc' in h or 'other designation' in h:
            header_map['other'] = i
        if 'common name' in h or 'name' in h:
            header_map['name'] = i
        if 'type' in h:
            header_map['type'] = i
        if 'distance' in h:
            header_map['distance'] = i
        if 'constellation' in h:
            header_map['constellation'] = i
        if 'right ascension' in h or h == 'ra':
            header_map['ra'] = i
        if 'declination' in h or h == 'dec':
            header_map['dec'] = i

    # (fetch_wiki_fields moved to module level)

    for tr in table.find_all('tr'):
        tds = tr.find_all(['td','th'])
        if not tds:
            continue
        cols = [td.get_text(strip=True) for td in tds]
        # Find Messier designation from available columns
        designation = None
        if 'designation' in header_map and header_map['designation'] < len(cols):
            m = re.search(r'\bM\s*(\d{1,3})\b', cols[header_map['designation']])
            if m:
                designation = f"M{int(m.group(1))}"
        if not designation:
            # fallback: search any cell for M###
            for c in cols:
                m = re.search(r'\bM\s*(\d{1,3})\b', c)
                if m:
                    designation = f"M{int(m.group(1))}"
                    break
        if not designation:
            continue

        obj = {'designation': designation}
        # name
        if 'name' in header_map and header_map['name'] < len(cols):
            name = cols[header_map['name']]
            if name and name not in ['—', '']:
                obj['name'] = name
        # other designation (NGC/IC)
        if 'other' in header_map and header_map['other'] < len(cols):
            other = cols[header_map['other']]
            if other and other not in ['—', '']:
                obj['other'] = other
        # type, distance, constellation
        if 'type' in header_map and header_map['type'] < len(cols):
            obj['type'] = cols[header_map['type']]
        if 'distance' in header_map and header_map['distance'] < len(cols):
            obj['distance'] = cols[header_map['distance']]
        if 'constellation' in header_map and header_map['constellation'] < len(cols):
            obj['constellation'] = cols[header_map['constellation']]
        if 'ra' in header_map and header_map['ra'] < len(cols):
            obj['ra'] = cols[header_map['ra']]
        if 'dec' in header_map and header_map['dec'] < len(cols):
            obj['dec'] = cols[header_map['dec']]

        # Ensure we have at least a name
        if 'name' not in obj:
            obj['name'] = designation
        # if row contains a link to the object page, follow it to enrich fields
        a = tr.find('a', href=re.compile(r'^/wiki/'))
        if a and a.get('href'):
            extra = fetch_wiki_fields(a['href'])
            # merge extras without overwriting existing simple values unless missing
            for k, v in extra.items():
                if k not in obj or not obj.get(k):
                    obj[k] = v

        messier[designation] = obj

    # write file
    out = OUT_DIR / 'messier.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(messier, f, indent=2, ensure_ascii=False)
    print('Wrote', out)
    return messier


def build_ngc():
    base = 'https://en.wikipedia.org/wiki/'
    ranges = ['List_of_NGC_objects_(1%E2%80%931000)',
              'List_of_NGC_objects_(1001%E2%80%932000)',
              'List_of_NGC_objects_(2001%E2%80%933000)',
              'List_of_NGC_objects_(3001%E2%80%934000)',
              'List_of_NGC_objects_(4001%E2%80%935000)',
              'List_of_NGC_objects_(5001%E2%80%936000)',
              'List_of_NGC_objects_(6001%E2%80%937000)',
              'List_of_NGC_objects_(7001%E2%80%937840)']

    ngc = {}
    for r in ranges:
        url = base + r
        print('Fetching', url)
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print('Failed to fetch', url, e)
            continue
        soup = BeautifulSoup(resp.text, 'html.parser')
        # find the first wikitable
        for table in soup.find_all('table', class_='wikitable'):
            headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
            if not headers:
                continue
            # try parse rows using headers
            for tr in table.find_all('tr'):
                tds = tr.find_all('td')
                if not tds:
                    continue
                cols = [td.get_text(strip=True) for td in tds]
                # find NGC designation in first column
                ngc_match = re.search(r'NGC\s*(\d+)', cols[0])
                if not ngc_match:
                    # sometimes the number is just digits
                    digits = re.search(r'\d+', cols[0])
                    if digits:
                        designation = f"NGC{digits.group(0)}"
                    else:
                        continue
                else:
                    designation = f"NGC{ngc_match.group(1)}"

                entry = {'designation': designation}
                # map known header names to columns heuristically
                hdr_to_idx = {h: i for i, h in enumerate(headers)}
                # attempt to extract common fields
                try:
                    if 'common name' in hdr_to_idx:
                        entry['name'] = cols[hdr_to_idx['common name']]
                    elif len(cols) > 1:
                        entry['name'] = cols[1]
                    if 'type' in hdr_to_idx:
                        entry['type'] = cols[hdr_to_idx['type']]
                    if 'constellation' in hdr_to_idx:
                        entry['constellation'] = cols[hdr_to_idx['constellation']]
                    if 'right ascension' in hdr_to_idx:
                        entry['ra'] = cols[hdr_to_idx['right ascension']]
                    if 'declination' in hdr_to_idx:
                        entry['dec'] = cols[hdr_to_idx['declination']]
                except Exception:
                    pass
                # follow link for richer data when available
                a = tr.find('a', href=re.compile(r'^/wiki/'))
                if a and a.get('href'):
                    extra = fetch_wiki_fields(a['href'])
                    for k, v in extra.items():
                        if k not in entry or not entry.get(k):
                            entry[k] = v

                ngc[designation] = entry
            # assume first wikitable is the desired list
            break

    out = OUT_DIR / 'ngc.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(ngc, f, indent=2, ensure_ascii=False)
    print('Wrote', out)
    return ngc


def build_ic():
    url = 'https://en.wikipedia.org/wiki/List_of_IC_objects'
    print('Fetching IC list...')
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print('Failed to fetch IC list:', e)
        return {}
    soup = BeautifulSoup(r.text, 'html.parser')
    ic = {}
    # find all wikitable tables and parse rows containing IC numbers
    for table in soup.find_all('table', class_='wikitable'):
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if not tds:
                continue
            cols = [td.get_text(strip=True) for td in tds]
            ic_match = re.search(r'IC\s*(\d+)', cols[0])
            if not ic_match:
                digits = re.search(r'\d+', cols[0])
                if digits:
                    designation = f"IC{digits.group(0)}"
                else:
                    continue
            else:
                designation = f"IC{ic_match.group(1)}"
            entry = {'designation': designation}
            if len(cols) > 1:
                entry['name'] = cols[1]
            if len(cols) > 2:
                entry['type'] = cols[2]

            # follow link for richer info
            a = tr.find('a', href=re.compile(r'^/wiki/'))
            if a and a.get('href'):
                extra = fetch_wiki_fields(a['href'])
                for k, v in extra.items():
                    if k not in entry or not entry.get(k):
                        entry[k] = v

            ic[designation] = entry

    out = OUT_DIR / 'ic.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(ic, f, indent=2, ensure_ascii=False)
    print('Wrote', out)
    return ic


def build_caldwell():
    # Caldwell catalogue page
    urls = ['https://en.wikipedia.org/wiki/Caldwell_catalog', 'https://en.wikipedia.org/wiki/Caldwell_catalogue']
    cald = {}
    table = None
    for url in urls:
        try:
            r = session.get(url, timeout=20)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            # find table with Caldwell entries
            for t in soup.find_all('table', class_='wikitable'):
                if 'C1' in t.get_text() or 'Caldwell' in t.get_text():
                    table = t
                    break
            if table:
                break
        except Exception:
            continue

    if not table:
        print('Caldwell table not found; skipping caldwell build.')
        return cald

    for tr in table.find_all('tr'):
        tds = tr.find_all('td')
        if not tds:
            continue
        cols = [td.get_text(strip=True) for td in tds]
        # designation in form C### or just number
        des = None
        m = re.search(r'\bC\s*(\d{1,3})\b', cols[0])
        if m:
            des = f"C{int(m.group(1))}"
        else:
            digits = re.search(r'\d+', cols[0])
            if digits:
                des = f"C{int(digits.group(0))}"
        if not des:
            continue
        entry = {'designation': des}
        if len(cols) > 1:
            entry['name'] = cols[1]

        # follow link for richer info
        a = tr.find('a', href=re.compile(r'^/wiki/'))
        if a and a.get('href'):
            extra = fetch_wiki_fields(a['href'])
            for k, v in extra.items():
                if k not in entry or not entry.get(k):
                    entry[k] = v

        cald[des] = entry

    out = OUT_DIR / 'caldwell.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(cald, f, indent=2, ensure_ascii=False)
    print('Wrote', out)
    return cald


def main():
    build_messier()
    build_ngc()
    build_ic()
    build_caldwell()


if __name__ == '__main__':
    main()

