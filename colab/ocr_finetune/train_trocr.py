"""Packaged TrOCR -> HF best/, selected by normalised validation crop CER."""
import json
import time
from common import (args_for,load_data,metrics,seed_all,record_config,log_epoch,
                    verify_initial,dry_pairs)


def run(a):
    train,valid,refs=load_data(a.data)
    initial=verify_initial(a,'trocr')
    import torch
    from PIL import Image
    from transformers import (TrOCRProcessor,VisionEncoderDecoderModel,Seq2SeqTrainer,
                              Seq2SeqTrainingArguments,EarlyStoppingCallback)
    seed_all(a.seed);torch.manual_seed(a.seed)
    torch.use_deterministic_algorithms(True,warn_only=True);torch.backends.cudnn.benchmark=False
    if not a.dry_run and not torch.cuda.is_available():raise RuntimeError('CUDA GPU required for full training')
    processor=TrOCRProcessor.from_pretrained(a.pretrained,local_files_only=True,use_fast=False)
    failed=[]
    for text in sorted(set([r['text'] for r in train]+list((a.data/'charset.txt').read_text()))):
        ids=processor.tokenizer(text).input_ids
        restored=processor.tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        if restored!=text or processor.tokenizer.unk_token_id in ids:failed.append(dict(text=text,decoded=restored))
    if failed:raise ValueError('Tokenizer cannot preserve labels: '+json.dumps(failed,ensure_ascii=False))
    model=VisionEncoderDecoderModel.from_pretrained(a.pretrained,local_files_only=True)
    for obj in [model.config,model.generation_config]:
        obj.decoder_start_token_id=processor.tokenizer.cls_token_id
        obj.eos_token_id=processor.tokenizer.sep_token_id;obj.pad_token_id=processor.tokenizer.pad_token_id
    record_config(a,dict(initial_sha256=initial,charset=dict(missing=[],extended=[]),
                        effective_train_pairs=8 if a.dry_run else len(train),
                        validation_crops=len(refs),validation_regions=len(valid)))
    source=dry_pairs(train) if a.dry_run else train

    class Lines(torch.utils.data.Dataset):
        def __len__(self):return len(source)
        def __getitem__(self,i):
            r=source[i]
            with Image.open(a.data/r['image']) as im:
                pixels=processor(images=im.convert('RGB'),return_tensors='pt').pixel_values[0]
            ids=processor.tokenizer(r['text']).input_ids
            if len(ids)>64:raise ValueError('Label exceeds fixed 64-token limit: '+r['image'])
            return dict(pixel_values=pixels,labels=torch.tensor(ids+[-100]*(64-len(ids))))

    class Trainer(Seq2SeqTrainer):
        def evaluate(self,eval_dataset=None,ignore_keys=None,metric_key_prefix='eval'):
            previous=self.model.training;self.model.eval();predictions=[];errors=[];start=time.perf_counter()
            with torch.no_grad():
                for r in valid:
                    try:
                        with Image.open(a.data/r['image']) as im:
                            pixel=processor(images=im.convert('RGB'),return_tensors='pt').pixel_values.to(self.model.device)
                        output=self.model.generate(pixel,do_sample=False,num_beams=1,max_new_tokens=64,
                                                   forced_eos_token_id=None)[0]
                        eos=self.model.generation_config.eos_token_id;eos=set(eos if isinstance(eos,list) else [eos])
                        if not any(int(i) in eos for i in output[1:]):raise ValueError('No EOS before generation cap')
                        text=processor.tokenizer.decode(output,skip_special_tokens=True,clean_up_tokenization_spaces=False)
                    except Exception as exc:
                        text='';errors.append(dict(image=r['image'],error=str(exc)))
                    predictions.append(text)
            result=metrics(refs,valid,predictions)
            values={'eval_cer':result['cer'],**{'eval_'+k:v for k,v in result.items() if k!='cer'}}
            loss=next((v['loss'] for v in reversed(self.state.log_history) if 'loss' in v),None)
            log_epoch(a.output,self.state.epoch,loss,result)
            with (a.output/'validation_events.jsonl').open('a') as f:
                f.write(json.dumps(dict(epoch=self.state.epoch,seconds=time.perf_counter()-start,errors=errors))+'\n')
            self.log(values);self.control=self.callback_handler.on_evaluate(self.args,self.state,self.control,values)
            self.model.train(previous);return values

    # Per-epoch checkpoints (~1.3 GB each, model only) go to Colab's local disk,
    # not Drive: a free Drive (15 GB) cannot hold several. Only best/ is saved to
    # Drive. Resume is not implemented, so nothing recoverable is lost on disconnect.
    from pathlib import Path
    local_root=Path('/content/trocr-checkpoints')
    checkpoint_dir=(local_root/a.output.name) if local_root.parent.is_dir() else a.output/'checkpoints'
    params=Seq2SeqTrainingArguments(output_dir=str(checkpoint_dir),save_only_model=True,learning_rate=a.lr,
        per_device_train_batch_size=4 if a.dry_run else a.batch,per_device_eval_batch_size=a.batch,
        max_steps=2 if a.dry_run else -1,num_train_epochs=a.epochs,
        eval_strategy='no' if a.dry_run else 'epoch',save_strategy='no' if a.dry_run else 'epoch',
        logging_strategy='steps' if a.dry_run else 'epoch',logging_steps=1,
        metric_for_best_model='cer',greater_is_better=False,predict_with_generate=True,
        load_best_model_at_end=not a.dry_run,save_total_limit=2,report_to=[],seed=a.seed,data_seed=a.seed,
        use_cpu=a.dry_run,fp16=False,bf16=False,dataloader_num_workers=0)
    callbacks=[] if a.dry_run else [EarlyStoppingCallback(early_stopping_patience=3)]
    config=json.loads((a.output/'config.json').read_text())
    config.update(trainer_arguments=params.to_dict(),model_config=model.config.to_dict(),generation_config=model.generation_config.to_dict())
    (a.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    trainer=Trainer(model=model,args=params,train_dataset=Lines(),eval_dataset=Lines(),
                    processing_class=processor,callbacks=callbacks)
    start=time.perf_counter();trainer.train()
    if a.dry_run:
        loss=next((r['loss'] for r in reversed(trainer.state.log_history) if 'loss' in r),None)
        log_epoch(a.output,0,loss,{})
        (a.output/'dry_run.json').write_text(json.dumps(dict(steps=trainer.state.global_step,pairs=8,device='cpu',
                                  seconds=time.perf_counter()-start,weights_saved=False))+'\n');return
    trainer.save_model(str(a.output/'best'));processor.save_pretrained(a.output/'best')
    (a.output/'best/provenance.json').write_text(json.dumps(dict(repository='microsoft/trocr-base-printed',fine_tuned=True,initial_sha256=initial,selection_metric='minimum val_crop_CER'),indent=2)+'\n')
    (a.output/'selection.json').write_text(json.dumps(dict(val_crop_CER=trainer.state.best_metric,
                              source_checkpoint=trainer.state.best_model_checkpoint,seconds=time.perf_counter()-start),indent=2)+'\n')


if __name__=='__main__':run(args_for(__doc__))
