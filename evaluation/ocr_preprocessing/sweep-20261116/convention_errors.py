import csv,sys,re,collections
def lev(a,b):
    p=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        c=[i]
        for j,y in enumerate(b,1): c.append(min(p[j]+1,c[j-1]+1,p[j-1]+(x!=y)))
        p=c
    return p[-1]
recs=[r for r in csv.DictReader(open(sys.argv[1])) if r['scoring_eligible']=='True']
modes={'current':lambda s:s,'no_space':lambda s:re.sub(r'\s','',s),'alnum_only':lambda s:re.sub(r'[^0-9a-z]','',s)}
for iset in ['annotation','prediction']:
  print('==',iset)
  for m in ['easyocr','paddleocr','trocr']:
    rs=[r for r in recs if r['model']==m and r['input_set']==iset]
    out=[]
    for name,f in modes.items():
        e=sum(lev(f(r['normalised_scoring_hypothesis']),f(r['normalised_reference_text'])) for r in rs); n=sum(len(f(r['normalised_reference_text'])) for r in rs)
        ex=sum(f(r['normalised_scoring_hypothesis'])==f(r['normalised_reference_text']) for r in rs)
        out.append(f"{name}: CER {100*e/n:.1f} EM {100*ex/len(rs):.1f}")
    print(f"{m:10s} n={len(rs)} | "+' | '.join(out))
  for fld in ['front_eds_num','front_eds_destination','front_eds_route']:
    for m in ['easyocr','paddleocr','trocr']:
        rs=[r for r in recs if r['model']==m and r['input_set']==iset and r['field']==fld]
        f=modes['alnum_only']; ex=sum(f(r['normalised_scoring_hypothesis'])==f(r['normalised_reference_text']) for r in rs)
        print(f"   {fld:22s}{m:10s} alnum EM {ex}/{len(rs)}")
