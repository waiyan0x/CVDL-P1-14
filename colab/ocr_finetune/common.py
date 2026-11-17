"""Train/valid-only bundle loading and the repository's normalised scoring."""
import argparse
import csv
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import random
import subprocess
import unicodedata

PADDLE_TAG='v3.3.2'
PADDLE_COMMIT='95dc316a8490a350c1d1fcf3bc80bf83d4e52450'
EASY_TAG='v1.7.2'
EASY_COMMIT='c4f3cd7225efd4f85451bd8b4a7646ae9a092420'
PADDLE_WEIGHTS_URL='https://paddle-model-ecology.bj.bcebos.com/paddlex/official_pretrained_model/en_PP-OCRv5_mobile_rec_pretrained.pdparams'


def normalise_text(text):
    # Copied from backend/app/evaluation/crop_scoring.py:normalise_text.
    folded = unicodedata.normalize("NFC", unicodedata.normalize("NFC", text).casefold())
    return " ".join(folded.split())


def distance(a,b):
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        current=[i]
        for j,y in enumerate(b,1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=current
    return previous[-1]


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def verify_initial(a,engine):
    lock=json.loads((a.data/'weights.lock.json').read_text())['models'][engine]
    root=a.pretrained if a.pretrained.is_dir() else a.pretrained.parent
    names=lock['files_sha256'] if engine=='trocr' else {'english_g2.pth':lock['files_sha256']['english_g2.pth']}
    actual={name:sha(root/name) for name in names}
    if actual!=names:raise ValueError('Initial checkpoint/config hashes differ from packaged '+engine)
    return actual


def pairs(path):
    result=[]
    for raw in Path(path).read_text().splitlines():
        name,sep,text=raw.partition('\t')
        if not sep or not text or '\t' in text:raise ValueError('Invalid line TSV')
        result.append(dict(image=name,text=text))
    return result


def load_data(root):
    root=Path(root).resolve()
    manifest=json.loads((root/'bundle_manifest.json').read_text())
    if manifest['counts']['test_files']!=0 or manifest['test_used'] is not False:
        raise ValueError('Bundle must explicitly contain no test data')
    for name,digest in manifest['payload_sha256'].items():
        p=(root/name).resolve()
        if not p.is_relative_to(root) or 'test' in Path(name).parts:
            raise ValueError('Unsafe or forbidden bundle member: '+name)
        if sha(p)!=digest:raise ValueError('Bundle hash mismatch: '+name)
    train=pairs(root/'train.tsv');labelled=pairs(root/'valid.tsv')
    truth={r['image']:r['text'] for r in labelled}
    refs=[];regions=[]
    for line in (root/'valid_crops.jsonl').read_text().splitlines():
        r=json.loads(line)
        refs.append(dict(review_id=r['review_id'],input_set=r['input_set'],field=r['field'],
                         text=r['reference'],line_count=len(r['lines'])))
        for i,p in enumerate(r['lines']):
            regions.append(dict(image=p,text=truth.get(p),review_id=r['review_id'],line_index=i))
    for split,rows in [('train',train),('valid',regions)]:
        for r in rows:
            if not r['image'].startswith('lines/'+split+'/'):
                raise ValueError('Line in wrong split: '+r['image'])
    if len(refs)!=len({r['review_id'] for r in refs}) or len(regions)!=len({r['image'] for r in regions}):
        raise ValueError('Duplicate validation identity')
    return train,regions,refs


def metrics(refs,regions,predictions):
    if len(regions)!=len(predictions):raise ValueError('Prediction count mismatch')
    by_crop={};line_errors=line_chars=0
    for row,pred in zip(regions,predictions):
        pred=pred if isinstance(pred,str) else ''
        group=by_crop.setdefault(row['review_id'],{})
        if row['line_index'] in group:raise ValueError('Duplicate line prediction')
        group[row['line_index']]=pred
        if row['text'] is not None:
            target=normalise_text(row['text']);hyp=normalise_text(pred)
            line_errors+=distance(target,hyp);line_chars+=len(target)
    errors=chars=exact=0
    for r in refs:
        target=normalise_text(r['text']);lines=by_crop.get(r['review_id'],{})
        hyp=normalise_text('\n'.join(lines.get(i,'') for i in range(r['line_count'])))
        errors+=distance(target,hyp);chars+=len(target);exact+=hyp==target
    return dict(cer=errors/chars,val_line_CER=line_errors/line_chars,
                val_crop_CER=errors/chars,val_crop_exact=exact/len(refs),
                crop_count=len(refs),line_pair_count=sum(r['text'] is not None for r in regions))


def check_charset(charset,characters,model):
    missing=sorted(set(charset)-set(characters))
    if missing:raise ValueError(model+' unsupported characters: '+repr(missing))
    return dict(model=model,missing=[],extended=[])


def seed_all(seed=0):
    import numpy as np
    random.seed(seed);np.random.seed(seed)
    os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
    os.environ['FLAGS_cudnn_deterministic']='1'


def args_for(description,extra=None):
    p=argparse.ArgumentParser(description=description)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--pretrained',type=Path,required=True)
    p.add_argument('--epochs',type=int,default=20);p.add_argument('--batch',type=int,default=8)
    p.add_argument('--lr',type=float,default=5e-5);p.add_argument('--seed',type=int,default=0)
    p.add_argument('--dry-run',action='store_true',help='CPU only, 8 training pairs, exactly 2 optimiser steps; no weights saved')
    if extra:extra(p)
    a=p.parse_args()
    if not 1<=a.epochs<=20:p.error('epochs must be 1–20')
    a.data=a.data.resolve();a.pretrained=a.pretrained.resolve();a.output=a.output.resolve()
    if not a.dry_run and not a.output.is_relative_to(Path('/content/drive')):
        p.error('Actual training outputs must be under the mounted /content/drive')
    return a


def record_config(a,extra=None):
    a.output.mkdir(parents=True,exist_ok=False)
    versions={}
    for name in ['torch','torchvision','transformers','accelerate','easyocr','paddlepaddle-gpu','numpy','Pillow']:
        try:versions[name]=metadata.version(name)
        except metadata.PackageNotFoundError:pass
    config=dict(arguments={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},
                versions=versions,dry_run=a.dry_run,test_used=False,
                normalisation='NFC -> Unicode casefold -> NFC -> collapse whitespace',
                augmentation='none, consistently for all three models',**(extra or {}))
    (a.output/'config.json').write_text(json.dumps(config,indent=2,ensure_ascii=False)+'\n')


def log_epoch(output,epoch,loss,result):
    p=output/'epoch_log.csv';new=not p.exists()
    with p.open('a',newline='') as f:
        w=csv.DictWriter(f,['epoch','train_loss','val_line_CER','val_crop_CER','val_crop_exact'],lineterminator='\n')
        if new:w.writeheader()
        w.writerow(dict(epoch=epoch,train_loss=loss,**{k:result.get(k) for k in ['val_line_CER','val_crop_CER','val_crop_exact']}))


def require_revision(repo,revision):
    actual=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if actual!=revision:raise ValueError('Unexpected upstream revision: '+actual)


def dry_pairs(train):
    if len(train)<8:raise ValueError('Dry run requires eight pairs')
    return train[:8]
