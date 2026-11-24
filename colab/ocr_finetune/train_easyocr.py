"""EasyOCR trainer Model, English g2 start, crop-CER checkpoint and custom export."""
import json
import math
import sys
import time
from types import SimpleNamespace
from common import (args_for,load_data,metrics,seed_all,record_config,log_epoch,
                    verify_initial,dry_pairs,check_charset,require_revision,EASY_COMMIT)


def run(a):
    train,valid,refs=load_data(a.data);initial=verify_initial(a,'easyocr')
    require_revision(a.repo,EASY_COMMIT)
    import torch
    import numpy as np
    from PIL import Image
    import yaml
    from easyocr.config import recognition_models
    seed_all(a.seed);torch.manual_seed(a.seed);torch.use_deterministic_algorithms(True,warn_only=True)
    torch.backends.cudnn.benchmark=False
    device='cpu' if a.dry_run else 'cuda'
    if device=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA GPU required')
    sys.path.insert(0,str(a.repo.resolve()/'trainer'))
    from model import Model
    chars=recognition_models['gen2']['english_g2']['characters']
    coverage=check_charset((a.data/'charset.txt').read_text(),chars,'english_g2')
    for row in train:check_charset(row['text'],chars,'english_g2')
    config=dict(Transformation='None',FeatureExtraction='VGG',SequenceModeling='BiLSTM',Prediction='CTC',
                num_fiducial=20,input_channel=1,output_channel=256,hidden_size=256,num_class=len(chars)+1,
                imgH=64,imgW=600,batch_max_length=128)
    model=Model(SimpleNamespace(**config)).to(device)
    state=torch.load(a.pretrained,map_location='cpu',weights_only=True)
    model.load_state_dict({k.removeprefix('module.'):v for k,v in state.items()},strict=True)
    record_config(a,dict(initial_sha256=initial,architecture=config,character_list=chars,
                        charset=coverage,trainer_commit=EASY_COMMIT,
                        early_stopping=dict(monitor='val_crop_CER',mode='min',patience=3,min_delta=0)))
    ids={c:i+1 for i,c in enumerate(chars)}

    def images(rows):
        tensors=[]
        for r in rows:
            with Image.open(a.data/r['image']) as im:
                im=im.convert('L');width=min(600,max(1,math.ceil(64*im.width/im.height)))
                im=im.resize((width,64),Image.Resampling.BICUBIC)
                array=np.asarray(im,dtype=np.float32)/127.5-1
                array=np.pad(array,((0,0),(0,600-width)),mode='edge')
                tensors.append(torch.from_numpy(array[None].copy()))
        return torch.stack(tensors).to(device)

    optimizer=torch.optim.Adam(model.parameters(),lr=a.lr)
    saved=json.loads((a.output/'config.json').read_text());saved['optimizer_defaults']=optimizer.defaults
    (a.output/'config.json').write_text(json.dumps(saved,indent=2)+'\n')
    criterion=torch.nn.CTCLoss(blank=0,zero_infinity=False)
    source=dry_pairs(train) if a.dry_run else train
    best=float('inf');stale=0;steps=0;start=time.perf_counter()
    for epoch in range(1,2 if a.dry_run else a.epochs+1):
        model.train();losses=[]
        order=list(range(8)) if a.dry_run else torch.randperm(len(source)).tolist()
        batch=4 if a.dry_run else a.batch
        for offset in range(0,len(order),batch):
            rows=[source[i] for i in order[offset:offset+batch]]
            output=model(images(rows),None).log_softmax(2)
            target=torch.tensor([ids[c] for r in rows for c in r['text']],dtype=torch.long,device=device)
            lengths=torch.tensor([len(r['text']) for r in rows],dtype=torch.long)
            pred_lengths=torch.full((len(rows),),output.shape[1],dtype=torch.long)
            loss=criterion(output.permute(1,0,2),target,pred_lengths,lengths)
            if not torch.isfinite(loss):raise ValueError('Nonfinite CTC loss; no silent zeroing')
            optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step()
            losses.append(float(loss.detach().cpu()));steps+=1
        if a.dry_run:
            assert steps==2
            log_epoch(a.output,0,sum(losses)/len(losses),{})
            (a.output/'dry_run.json').write_text(json.dumps(dict(steps=steps,pairs=8,device=device,
                                seconds=time.perf_counter()-start,weights_saved=False))+'\n');return
        model.eval();predictions=[];errors=[]
        with torch.no_grad():
            for row in valid:
                try:
                    tokens=model(images([row]),None).argmax(2)[0].cpu().tolist()
                    text=[];previous=None
                    for token in tokens:
                        if token and token!=previous:text.append(chars[token-1])
                        previous=token
                    predictions.append(''.join(text))
                except Exception as exc:
                    predictions.append('');errors.append(dict(image=row['image'],error=str(exc)))
        result=metrics(refs,valid,predictions);log_epoch(a.output,epoch,sum(losses)/len(losses),result)
        with (a.output/'validation_events.jsonl').open('a') as f:f.write(json.dumps(dict(epoch=epoch,errors=errors))+'\n')
        if result['cer']<best:
            best=result['cer'];stale=0;dest=a.output/'best';dest.mkdir(exist_ok=True)
            torch.save({'module.'+k:v.detach().cpu() for k,v in model.state_dict().items()},dest/'eds_english_g2.pth')
            custom=dict(imgH=64,lang_list=['en'],character_list=chars,
                        network_params=dict(input_channel=1,output_channel=256,hidden_size=256))
            (dest/'eds_english_g2.yaml').write_text(yaml.safe_dump(custom,allow_unicode=True))
            (dest/'eds_english_g2.py').write_text('from easyocr.model.vgg_model import Model\n')
            (dest/'README.txt').write_text('Load all three files from this directory:\nimport easyocr\nreader = easyocr.Reader(["en"], detector=False, recog_network="eds_english_g2", model_storage_directory=BEST_DIR, user_network_directory=BEST_DIR, download_enabled=False, quantize=False)\n')
            (a.output/'selection.json').write_text(json.dumps(dict(epoch=epoch,val_crop_CER=best,seed=a.seed))+'\n')
        else:stale+=1
        if stale>=3:break


if __name__=='__main__':
    from pathlib import Path
    run(args_for(__doc__,lambda p:p.add_argument('--repo',type=Path,required=True)))
