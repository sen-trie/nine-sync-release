import json,sys
d=json.load(open(sys.argv[1]))
for r in d['records']:
    print(r['label'][:50].ljust(50), str(r.get('ok','-')).ljust(5), str(r['mode']).ljust(8), 'ops',r['ops'],'props',r['props'],'reg',r['bundled_registered'],'lp',r['load_post'],'menu',r['menu_import'],'t',r['ticks'], (r.get('error') or '')[:100])
print(d['summary'])
