"""Pinned official English v5 training, crop-CER selection, native inference export."""
import json
import logging
import os
from pathlib import Path
import re
import runpy
import sys
import time
from common import (args_for,load_data,metrics,seed_all,record_config,log_epoch,sha,
                    check_charset,dry_pairs,require_revision,PADDLE_COMMIT,PADDLE_WEIGHTS_URL)


def run(a):
    train,valid,refs=load_data(a.data)
    require_revision(a.repo,PADDLE_COMMIT)
    seed_all(a.seed)
    import paddle
    import yaml
    paddle.seed(a.seed)
    if not a.dry_run and not paddle.is_compiled_with_cuda():raise RuntimeError('CUDA Paddle required')
    checkpoint=a.pretrained.with_suffix('') if a.pretrained.suffix=='.pdparams' else a.pretrained
    weights=checkpoint.with_suffix('.pdparams')
    if not weights.is_file():raise ValueError('Training .pdparams required; inference.pdiparams is not interchangeable')
    origin_file=weights.with_suffix('.origin.json')
    if not origin_file.is_file():raise ValueError('Training checkpoint needs its Colab download .origin.json')
    origin=json.loads(origin_file.read_text())
    if origin.get('url')!=PADDLE_WEIGHTS_URL or origin.get('sha256')!=sha(weights):
        raise ValueError('Training checkpoint URL/hash provenance mismatch')
    repo=a.repo.resolve();config_path=repo/'configs/rec/PP-OCRv5/multi_language/en_PP-OCRv5_mobile_rec.yaml'
    config=yaml.safe_load(config_path.read_text())
    if config['Global']['model_name']!='en_PP-OCRv5_mobile_rec':raise ValueError('Wrong starting architecture')
    dictionary=repo/config['Global']['character_dict_path']
    characters=dictionary.read_text().splitlines()+[' ']
    # All current characters are already covered. If future labels require a
    # changed head, fail explicitly rather than silently dropping or reindexing.
    coverage=check_charset((a.data/'charset.txt').read_text(),characters,'English Paddle v5')
    for r in train:check_charset(r['text'],characters,'English Paddle v5')
    # 5 training lines (up to 39 chars) exceed the config's 25. Raise the limit to the
    # CTC output length rather than drop labels. At 48x320 input the CTC branch emits
    # 40 timesteps; a label needs len + adjacent repeats <= 40. The limit only sets
    # label padding and the auxiliary NRTR decode length (no learned weights).
    ctc_steps=40
    def ctc_need(t):return len(t)+sum(x==y for x,y in zip(t,t[1:]))
    longest=max(ctc_need(r['text']) for r in train)
    if longest>ctc_steps:
        raise ValueError(f'A training label needs {longest} CTC steps > {ctc_steps}; no silent filtering')
    original_max=config['Global']['max_text_length']
    if max(len(r['text']) for r in train)>original_max:
        config['Global']['max_text_length']=ctc_steps
        for head in config['Architecture']['Head']['head_list']:
            if 'NRTRHead' in head:head['NRTRHead']['max_text_length']=ctc_steps
    max_text_length_change=dict(original=original_max,used=config['Global']['max_text_length'],
        longest_train_label=max(len(r['text']) for r in train),
        labels_over_original=sum(len(r['text'])>original_max for r in train))
    record_config(a,dict(initial_checkpoint_url=PADDLE_WEIGHTS_URL,initial_checkpoint_sha256=sha(weights),
                        upstream_tag='v3.3.2',upstream_commit=PADDLE_COMMIT,charset=coverage,
                        dictionary_sha256=sha(dictionary),base_config_sha256=sha(config_path),
                        max_text_length=max_text_length_change,
                        selection='max 1/(1+val_crop_CER), exactly equivalent to minimum CER'))
    run_dictionary=a.output/'dictionary.txt';run_dictionary.write_bytes(dictionary.read_bytes())
    (a.output/'dictionary_check.json').write_text(json.dumps(coverage,indent=2)+'\n')
    source=dry_pairs(train) if a.dry_run else train
    train_file=a.output/'train.tsv';train_file.write_text(''.join(r['image']+'\t'+r['text']+'\n' for r in source))
    # Upstream label transforms require a valid encoded label even for eval.
    # Use a placeholder only in this clearly separate I/O file; real crop/line
    # metrics always use bundle references, never decoded placeholder labels.
    eval_file=a.output/'eval_io_not_ground_truth.tsv'
    eval_file.write_text(''.join(r['image']+'\t?\n' for r in valid))
    g=config['Global'];g.update(use_gpu=not a.dry_run,distributed=False,seed=a.seed,
        epoch_num=1 if a.dry_run else a.epochs,save_model_dir=str(a.output/'checkpoints'),
        pretrained_model=str(checkpoint),checkpoints=None,save_epoch_step=1,
        eval_batch_step=[0,1],eval_batch_epoch=1,cal_metric_during_train=False,
        log_smooth_window=1,print_batch_step=1,character_dict_path=str(run_dictionary))
    config['Optimizer']['lr']['learning_rate']=a.lr;config['Optimizer']['lr']['warmup_epoch']=0
    transforms=[{'DecodeImage':{'img_mode':'BGR','channel_first':False}},
                {'MultiLabelEncode':{'gtc_encode':'NRTRLabelEncode'}},
                {'RecResizeImg':{'image_shape':[3,48,320]}},
                {'KeepKeys':{'keep_keys':['image','label_ctc','label_gtc','length','valid_ratio']}}]
    for split,file in [('Train',train_file),('Eval',eval_file)]:
        config[split]=dict(dataset=dict(name='SimpleDataSet',data_dir=str(a.data),
            label_file_list=[str(file)],transforms=transforms),
            loader=dict(shuffle=split=='Train',drop_last=False,batch_size_per_card=4 if a.dry_run else a.batch,num_workers=0))
    if a.dry_run:
        # No eval in the 2-step smoke test. PaddleOCR v3.3.2 calls len(valid_dataloader)
        # whenever eval_batch_step is a list, so use a plain, never-reached step instead.
        config['Eval']=None;g['eval_batch_step']=10**9;g['eval_batch_epoch']=None
    config['Metric']=dict(name='RecMetric',main_indicator='cer_score')
    saved=json.loads((a.output/'config.json').read_text());saved['effective_paddle_config']=config
    (a.output/'config.json').write_text(json.dumps(saved,indent=2)+'\n')
    effective=a.output/'paddle_config.yaml';effective.write_text(yaml.safe_dump(config,sort_keys=False))
    sys.path.insert(0,str(repo))
    import ppocr.metrics
    from ppocr.postprocess import build_post_process
    from ppocr.modeling.architectures import build_model
    # Fail on partial pretrained loading, which the upstream loader otherwise
    # may merely log. Current dictionary is unchanged, so all shapes must agree.
    ctc_classes=len(build_post_process(config['PostProcess'],g).character)
    arch=config['Architecture'];arch['Head']['out_channels_list']={'CTCLabelDecode':ctc_classes,'NRTRLabelDecode':ctc_classes+3}
    expected=build_model(arch).state_dict();stored=paddle.load(str(weights))
    mismatch=[k for k,v in expected.items() if k not in stored or list(v.shape)!=list(stored[k].shape)]
    if mismatch:raise ValueError('Pretrained training-head mismatch (not silently reinitialised): '+repr(mismatch))
    del expected,stored
    epoch_losses={};epoch_number=[0];step_count=[0]

    class LossRecorder(logging.Handler):
        def emit(self,record):
            text=record.getMessage();epoch=re.search(r'epoch:\s*\[(\d+)/',text)
            loss=re.search(r'(?<![\w])loss:\s*([0-9.eE+-]+)',text)
            if epoch:epoch_number[0]=int(epoch.group(1))
            if epoch and loss:
                epoch_losses.setdefault(epoch_number[0],[]).append(float(loss.group(1)));step_count[0]+=1

    class CropMetric:
        main_indicator='cer_score'
        def __init__(self,**kwargs):self.reset();self.epoch=0
        def reset(self):self.output=[]
        def __call__(self,pred_label,batch=None,**kwargs):
            predictions,_=pred_label;self.output.extend(r[0] for r in predictions)
        def get_metric(self):
            result=metrics(refs,valid,self.output);self.epoch+=1
            losses=epoch_losses.get(self.epoch,[])
            log_epoch(a.output,self.epoch,sum(losses)/len(losses) if losses else None,result)
            self.reset()
            return dict(cer_score=1/(1+result['cer']),val_crop_CER=result['cer'],
                        val_line_CER=result['val_line_CER'],val_crop_exact=result['val_crop_exact'])

    ppocr.metrics.RecMetric=CropMetric
    from ppocr.utils.logging import get_logger
    get_logger().addHandler(LossRecorder())
    import tools.program as program
    if a.dry_run:
        # No checkpoints anywhere in CPU smoke mode.
        program.save_model=lambda *args,**kwargs:None
    previous_argv=sys.argv[:];previous_dir=Path.cwd();start=time.perf_counter()
    sys.argv=['tools/train.py','-c',str(effective)]
    try:
        os.chdir(repo);runpy.run_path(str(repo/'tools/train.py'),run_name='__main__')
    finally:
        sys.argv=previous_argv;os.chdir(previous_dir)
    if a.dry_run:
        if step_count[0]!=2:raise RuntimeError('Expected two logged optimiser steps, observed '+str(step_count[0]))
        losses=epoch_losses[1];log_epoch(a.output,0,sum(losses)/len(losses),{})
        (a.output/'dry_run.json').write_text(json.dumps(dict(steps=2,pairs=8,device='cpu',
                                seconds=time.perf_counter()-start,weights_saved=False))+'\n');return
    selected=a.output/'checkpoints/best_accuracy'
    if not selected.with_suffix('.pdparams').exists():raise RuntimeError('No CER-selected checkpoint was produced')
    # The filename is upstream's name; its selection metric above is crop CER.
    best=a.output/'best';best.mkdir()
    import subprocess
    subprocess.run([sys.executable,str(repo/'tools/export_model.py'),'-c',str(effective),'-o',
                    'Global.pretrained_model='+str(selected),'Global.save_inference_dir='+str(best)],cwd=repo,check=True)
    for name in ['inference.json','inference.pdiparams','inference.yml']:
        if not (best/name).is_file():raise RuntimeError('Export did not produce '+name+'; do not claim runner compatibility')
    # The runner verifies these exported files, not the original training weights.
    provenance=dict(repository='PaddlePaddle/en_PP-OCRv5_mobile_rec',fine_tuned=True,
                    upstream_tag='v3.3.2',initial_checkpoint_url=PADDLE_WEIGHTS_URL,
                    initial_checkpoint_sha256=sha(weights),files_sha256={p.name:sha(p) for p in best.iterdir() if p.is_file()})
    (best/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    (a.output/'selection.json').write_text(json.dumps(dict(metric='minimum val_crop_CER',
                    upstream_selected_prefix=str(selected),seconds=time.perf_counter()-start),indent=2)+'\n')


if __name__=='__main__':
    run(args_for(__doc__,lambda p:p.add_argument('--repo',type=Path,required=True)))
