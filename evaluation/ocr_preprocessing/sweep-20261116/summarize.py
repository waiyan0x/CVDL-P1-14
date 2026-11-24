import csv,sys,collections,re
def lev(a,b):
    p=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        c=[i]
        for j,y in enumerate(b,1): c.append(min(p[j]+1,c[j-1]+1,p[j-1]+(x!=y)))
        p=c
    return p[-1]
for f in sys.argv[1:]:
    rs=list(csv.DictReader(open(f)))
    agg=collections.defaultdict(lambda:[0,0,0,0])
    for r in rs:
        for key in [(r['variant'],r['input_set'],'all'),(r['variant'],r['input_set'],r['field'][10:])]:
            a=agg[key]; a[0]+=lev(r['hyp'],r['ref']); a[1]+=len(r['ref']); a[2]+=r['hyp']==r['ref']; a[3]+=1
    print('==',rs[0]['engine'])
    vs=list(dict.fromkeys(r['variant'] for r in rs))
    print(f"{'variant':12s}"+''.join(f"{k:>22s}" for k in ['anno all CER/EM','anno num EM','anno dest EM','anno route EM','pred all CER/EM']))
    for v in vs:
        line=f"{v:12s}"
        for iset,fld in [('annotation','all'),('annotation','num'),('annotation','destination'),('annotation','route'),('prediction','all')]:
            a=agg[(v,iset,fld)]
            line+=f"{100*a[0]/a[1]:9.1f}/{100*a[2]/a[3]:5.1f} n{a[3]:<3d}  " if fld=='all' else f"{a[2]:>14d}/{a[3]:<3d}    "
        print(line)
