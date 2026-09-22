"""Parse James Clear 3-2-1 newsletter pages (saved HTML) into structured JSON."""
import re, html, json, glob, sys, os
from datetime import datetime

ROLES = set("""author writer astronaut poet novelist entrepreneur investor philosopher comedian actress actor musician
physicist scientist psychologist psychiatrist psychoanalyst economist artist designer chef coach painter photographer founder
journalist historian theologian monk naturalist architect composer director filmmaker pianist cartoonist programmer engineer
mathematician biologist surgeon doctor physician nurse pilot athlete runner boxer wrestler swimmer golfer rapper singer
songwriter playwright screenwriter essayist blogger podcaster professor teacher scholar statesman senator president general
admiral emperor stoic rabbi priest pastor bishop saint explorer adventurer mountaineer climber sailor inventor businessman
businesswoman billionaire executive ceo cofounder co-founder leader activist abolitionist chemist astronomer cosmologist
neuroscientist anthropologist sociologist linguist lawyer judge justice politician diplomat ambassador speaker consultant
marketer copywriter editor publisher illustrator animator sculptor potter woodworker craftsman carpenter farmer gardener
educator humorist critic broadcaster cellist violinist guitarist drummer conductor choreographer dancer ballerina
strategist analyst trader banker financier producer showrunner cyclist skier skater gymnast
philanthropist industrialist magnate tycoon chess grandmaster champion legend icon star mystic sage guru
bestselling award-winning pulitzer nobel prize-winning legendary famed renowned late former first the a an and
country music american british french german russian roman greek chinese japanese indian ancient buddhist zen taoist
sufi hindu christian jewish muslim catholic""".split())

def text_of(s):
    t = re.sub(r'<br\s*/?>', '\n', s)
    t = re.sub(r'<[^>]+>', '', t)
    return html.unescape(t).replace(' ', ' ').strip()

def clean(fragment):
    fragment = re.sub(r'<div id="block_[^"]*" class="twitter-share.*?</div>\s*</div>\s*</div>', '', fragment, flags=re.S)
    fragment = re.sub(r'<div[^>]*wp-block-spacer[^>]*></div>', '', fragment)
    fragment = re.sub(r'<hr[^>]*>', '', fragment)
    fragment = re.sub(r'<figure.*?</figure>', '', fragment, flags=re.S)
    return fragment

def blocks(fragment):
    out = []
    for m in re.finditer(r'<p[^>]*>(.*?)</p>|<(ol|ul)[^>]*>(.*?)</\2>|<blockquote[^>]*>(.*?)</blockquote>|<h[3-6][^>]*>(.*?)</h[3-6]>', fragment, flags=re.S):
        if m.group(1) is not None:
            t = text_of(m.group(1))
            if t and not re.match(r'^\(?\s*Share this on', t, re.I): out.append(t)
        elif m.group(2):
            items = [text_of(x) for x in re.findall(r'<li[^>]*>(.*?)</li>', m.group(3), flags=re.S)]
            for i, it in enumerate(items, 1):
                out.append((f'{i}. ' if m.group(2) == 'ol' else '• ') + it)
        elif m.group(4) is not None:
            t = text_of(m.group(4))
            if t: out.append(t)
        elif m.group(5) is not None:
            t = text_of(m.group(5))
            if t: out.append(t)
    return out

def strip_outer_quotes(lines):
    lines = [l.strip() for l in lines if l.strip()]
    if not lines: return lines
    lines[0] = re.sub(r'^((?:\d+\. |• )?)[“"]', r'\1', lines[0])
    for i in range(len(lines) - 1, -1, -1):
        if re.search(r'[”"]\*?\s*$', lines[i]):
            lines[i] = re.sub(r'[”"]\*?\s*$', '', lines[i]).rstrip()
            break
    return lines

AUTHOR_OVERRIDES = {('august-29-2019', 1): 'A friend’s grandmother', ('june-15-2023', 1): 'Anonymous',
                    ('april-23-2020', 0): 'A Native American proverb', ('november-21-2024', 1): 'J.R.R. Tolkien'}

MARK = r'<p[^>]*>(?:\s|<br\s*/?>|&nbsp;|<em>\s*</em>|<strong>\s*</strong>)*(?:I|II|III|IV|V)\.?(?:\s|&nbsp;|<em>\s*</em>)*</p>'

def author_from_intro(intro):
    m = re.match(r'^(?:The |An? |Olympic )?[^,]{3,80}, ([A-Z][^,]{2,50}),? (?:on|explains|shares|reminds|offers|describes|with|in|who)\b', intro)
    if m: return m.group(1).strip()
    s = re.sub(r'^(The (first|second|third) quote (today )?(is|comes) from )', '', intro, flags=re.I)
    s = re.sub(r'^(A quote from |Here is a quote from |Here’s a quote from |From )', '', s, flags=re.I)
    s = s.split(' on ')[0].split(',')[0].split(':')[0]
    s = re.sub(r'\s+(shares|reminds|explains|describes|writes|offers|says|talks|discusses|reflects|urges|encourages|argues|notes|asks|suggests|advises|recalls|points|gives|tells|warns|observes|with|in|about)\b.*$', '', s)
    words = s.split()
    run = []
    for w in reversed(words):
        core = w.strip('.,;()')
        if core[:1].isupper() or (core.lower() in ('de', 'van', 'von', 'der', 'da', 'la', 'le', 'du', 'bin', 'ibn', 'of', 'the') and run):
            run.insert(0, w.strip(',;()'))
        else:
            break
    while len(run) > 1 and run[0].lower().strip('.') in ROLES:
        run.pop(0)
    return ' '.join(run).strip() if run else s.strip()

def parse(doc, slug):
    doc = doc.replace('​', '').replace('﻿', '').replace('\xa0', ' ')
    title = text_of(re.search(r'<h1>(.*?)</h1>', doc, re.S).group(1))
    date = re.search(r'post-info-cat">\s*(.*?)\s*<', doc, re.S).group(1).strip()
    start = re.search(r'<h2[^>]*>\s*\d+\s*IDEAS', doc, re.I)
    if not start: raise ValueError('no ideas heading')
    body = doc[start.start():]
    end = body.find('<div class="post__next">')
    body = body[:end] if end > 0 else body
    sections = re.split(r'<h2[^>]*>(.*?)</h2>', body)
    secs = {}
    for i in range(1, len(sections), 2):
        secs[re.sub(r'\s+', ' ', text_of(sections[i]).upper())] = clean(sections[i + 1])
    ideas, quotes, warnings = [], [], []
    ideas_html = next((v for k, v in secs.items() if 'IDEAS' in k), '')
    iparts = re.split(MARK, ideas_html)
    lead0 = blocks(iparts[0])
    if not lead0 or (len(lead0) == 1 and re.search(r'(…|\.\.\.|:)\s*$', lead0[0])): iparts = iparts[1:]
    for part in iparts:
        lines = strip_outer_quotes(blocks(part))
        if lines: ideas.append({'text': '\n'.join(lines)})
    quotes_html = next((v for k, v in secs.items() if 'QUOTE' in k), '')
    qparts = re.split(MARK, quotes_html)
    if len(blocks(qparts[0])) < 2: qparts = qparts[1:]
    for part in qparts:
        lines = blocks(part)
        if not lines: continue
        intro_html = re.search(r'<p[^>]*>(.*?)</p>', part, re.S)
        strong = re.search(r'<strong>(.*?)</strong>', intro_html.group(1), re.S) if intro_html else None
        m1 = re.match(r'^(.*?:)\s*([“"].*)$', lines[0], re.S)
        if m1 and len(lines[0]) > 60 and (len(lines) == 1 or re.match(r'^source:', lines[1], re.I)):
            lines = [m1.group(1), m1.group(2)] + lines[1:]
        intro = lines[0]
        source = ''
        if re.match(r'^source:', lines[-1], re.I):
            source = re.sub(r'^source:\s*', '', lines[-1], flags=re.I).strip(); lines = lines[:-1]
        body_lines = strip_outer_quotes(lines[1:])
        if strong:
            author = text_of(strong.group(1)).strip(' ,:')
        else:
            author = author_from_intro(intro); warnings.append(f'author-fallback: {author!r} <- {intro[:80]!r}')
        author = AUTHOR_OVERRIDES.get((slug, len(quotes)), author)
        quotes.append({'author': author, 'lead': intro.rstrip(':'), 'text': '\n'.join(body_lines), 'source': source})
    q_html = next((v for k, v in secs.items() if 'QUESTION' in k), '')
    qlines = []
    for l in blocks(q_html):
        if re.match(r'^\(|^Until next|^James Clear|^p\.s\.|^P\.S\.|^Thanks for reading', l): break
        qlines.append(l)
    if len(qlines) > 1 and qlines[0].rstrip().endswith(':') and re.search(r'(question|consider|think about|ask yourself)', qlines[0], re.I):
        qlines = qlines[1:]
    question = '\n'.join(qlines).strip()
    if len(ideas) != 3: warnings.append(f'{len(ideas)} ideas')
    if len(quotes) != 2: warnings.append(f'{len(quotes)} quotes')
    if not question: warnings.append('no question')
    return {'slug': slug, 'url': f'https://jamesclear.com/3-2-1/{slug}', 'title': re.sub(r'^3-2-1:\s*', '', title),
            'date': date, 'iso': datetime.strptime(date, '%B %d, %Y').strftime('%Y-%m-%d'),
            'ideas': ideas, 'quotes': quotes, 'question': question, 'warnings': warnings}

if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else 'issues'
    out, bad = [], []
    for f in sorted(glob.glob(os.path.join(src, '*.html'))):
        slug = os.path.basename(f)[:-5]
        try:
            out.append(parse(open(f, encoding='utf-8').read(), slug))
        except Exception as e:
            bad.append((slug, str(e)))
    out.sort(key=lambda o: o['iso'])
    json.dump(out, open('issues.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(len(out), 'issues parsed;', len(bad), 'failed')
    for b in bad: print('  FAILED', b)
    for o in out:
        for w in o['warnings']: print(o['slug'], '|', w)
