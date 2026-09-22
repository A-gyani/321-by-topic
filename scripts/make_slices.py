"""Split issues.json into N compact slices for parallel tagging."""
import json, os, sys
N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
issues = json.load(open('issues.json', encoding='utf-8'))
os.makedirs('slices', exist_ok=True); os.makedirs('tags', exist_ok=True)
per = -(-len(issues) // N)
for i in range(N):
    chunk = issues[i*per:(i+1)*per]
    out = []
    for iss in chunk:
        out.append({'slug': iss['slug'], 'title': iss['title'],
                    'ideas': [x['text'] for x in iss['ideas']],
                    'quotes': [{'lead': q['lead'], 'text': q['text']} for q in iss['quotes']],
                    'question': iss['question']})
    json.dump(out, open(f'slices/slice_{i+1}.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f'slice_{i+1}: {len(chunk)} issues, {sum(len(x["ideas"])+len(x["quotes"])+1 for x in out)} items')
