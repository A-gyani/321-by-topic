import urllib.request, re, time, os, sys
os.makedirs('issues', exist_ok=True)
H={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36'}
if not os.path.exists('archive.html'):
    open('archive.html','wb').write(urllib.request.urlopen(urllib.request.Request('https://jamesclear.com/3-2-1',headers=H),timeout=30).read())
idx=open('archive.html',encoding='utf-8').read()
slugs=sorted(set(re.findall(r'href="https://jamesclear.com/3-2-1/([^"]+)"',idx)))
print(len(slugs),'slugs',flush=True)
ok=fail=0
for s in slugs:
    p=f'issues/{s}.html'
    if os.path.exists(p) and os.path.getsize(p)>20000: ok+=1; continue
    for attempt in range(3):
        try:
            d=urllib.request.urlopen(urllib.request.Request(f'https://jamesclear.com/3-2-1/{s}',headers=H),timeout=30).read()
            open(p,'wb').write(d); ok+=1; break
        except Exception as e:
            if attempt==2: fail+=1; print('FAIL',s,e,flush=True)
            time.sleep(2)
    time.sleep(0.4)
print('done ok',ok,'fail',fail,flush=True)
