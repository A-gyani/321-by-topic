"""Merge issues.json + tags/*.json into data.js and index.html at the repo root. Run from the repo root."""
import json, glob, os, sys, re, shutil
issues = json.load(open('issues.json', encoding='utf-8'))
tags = {}
for f in glob.glob('tags/*.json'):
    tags.update(json.load(open(f, encoding='utf-8')))
tax = [l.split('. ',1)[1].split(' — ')[0].strip() for l in open('TAXONOMY.md',encoding='utf-8') if re.match(r'^\d+\. ', l)]
items, missing, badtopic = [], [], set()
def norm_author(a):
    a = re.sub(r'([A-Z])\.\s+(?=[A-Z]\.)', r'.', a)   # "C. S. Lewis" -> "C.S. Lewis"
    return {'Laozi': 'Lao Tzu', 'Lao-Tzu': 'Lao Tzu'}.get(a, a)
def norm(ts):
    out = []
    for t in (ts or []):
        if t in tax: out.append(t)
        else: badtopic.add(t)
    return out or ['Uncategorised']
for iss in issues:
    t = tags.get(iss['slug'])
    meta = {'date': iss['date'], 'iso': iss['iso'], 'url': iss['url'], 'issue': iss['title']}
    for k, idea in enumerate(iss['ideas']):
        tp = norm(t['ideas'][k] if t and k < len(t.get('ideas', [])) else None)
        if tp == ['Uncategorised']: missing.append((iss['slug'], 'idea', k))
        items.append({'kind': 'idea', 'text': idea['text'], 'topics': tp, **meta})
    for k, q in enumerate(iss['quotes']):
        tp = norm(t['quotes'][k] if t and k < len(t.get('quotes', [])) else None)
        if tp == ['Uncategorised']: missing.append((iss['slug'], 'quote', k))
        items.append({'kind': 'quote', 'text': q['text'], 'author': norm_author(q['author']), 'lead': q['lead'], 'source': q['source'], 'topics': tp, **meta})
    if iss['question']:
        tp = norm(t['question'] if t else None)
        if tp == ['Uncategorised']: missing.append((iss['slug'], 'question', 0))
        items.append({'kind': 'question', 'text': iss['question'], 'topics': tp, **meta})
open('data.js', 'w', encoding='utf-8').write('window.DATA=' + json.dumps(items, ensure_ascii=False, separators=(',', ':')) + ';\n')
html = open('scripts/site_template.html', encoding='utf-8').read()
open('index.html', 'w', encoding='utf-8').write(html)
print(len(issues), 'issues ->', len(items), 'items;', len(missing), 'untagged;', 'unknown topics:', sorted(badtopic))
if missing[:10]: print(missing[:10])
