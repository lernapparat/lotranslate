#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from itertools import repeat, count
import types
import time
import io
import re
import torch

import sys
import os

import spacy

#language_model_en = spacy.load("en")

base_dir = os.path.expanduser('~/python/pytorch/opennmt-py')
sys.path.append(os.path.join(base_dir, 'OpenNMT-py'))

import onmt
from onmt.utils.logging import init_logger
from onmt.utils.misc import split_corpus
from onmt.translate.translator import build_translator
import sentencepiece

opt = types.SimpleNamespace(
    alpha=0.0,
    attn_debug=False,
    avg_raw_probs=False,
    batch_size=30,
    beam_size=5,
    beta=-0.0,
    block_ngram_repeat=0,
    config=None,
    coverage_penalty='none',
    data_type='text',
    dump_beam='',
    dynamic_dict=False,
    fp32=True,
    gpu=-1,
    ignore_when_blocking=[],
    image_channel_size=3,
    length_penalty='none',
    log_file='',
    log_file_level='0',
    max_length=100,
    max_sent_length=None,
    min_length=0,
    models=[os.path.join(base_dir, 'available_models/model-ende/averaged-10-epoch.pt')],
    n_best=1,
    output='pred.txt',
    random_sampling_temp=1.0,
    random_sampling_topk=1,
    replace_unk=False,
    report_bleu=False,
    report_rouge=False,
    report_time=False,
    sample_rate=16000,
    save_config=None,
    seed=829,
    shard_size=10000,
    share_vocab=False,
    src='/tmp/x.txt',
    src_dir='',
    stepwise_penalty=False,
    tgt=None,
    verbose=False,
    window='hamming',
    window_size=0.02,
    window_stride=0.01,
    accum_count=4, adagrad_accumulator_init=0, adam_beta1=0.9, adam_beta2=0.998, audio_enc_pooling='1',
)

model_opt = types.SimpleNamespace(

    batch_size=5120, batch_type='tokens', bridge=False, brnn=False, brnn_merge='concat', cnn_kernel_width=3, context_gate=None, copy_attn=False, copy_attn_force=False, copy_attn_type=None, copy_loss_by_seqlength=False, coverage_attn=False, data='wmt14.en-de', dec_layers=6, dec_rnn_size=500, decay_method='noam', decoder_type='transformer', dropout=0.1, enc_layers=6, enc_rnn_size=500, encoder_type='transformer', epochs=20, exp='', exp_host='', feat_merge='concat', feat_vec_exponent=0.7, feat_vec_size=-1, fix_word_vecs_dec=False, fix_word_vecs_enc=False, generator_function='softmax', global_attention='general', global_attention_function='softmax', gpuid=[0], heads=8, input_feed=1, label_smoothing=0.1, lambda_coverage=1, layers=6, learning_rate=2.0, learning_rate_decay=0.5, loss_scale=0, max_generator_batches=4, max_grad_norm=0.0, max_relative_positions=0, model_dtype='fp32', model_type='text', normalization='tokens', optim='sparseadam', param_init=0.0, position_encoding=True, pre_word_vecs_dec=None, pre_word_vecs_enc=None, report_every=50, reuse_copy_attn=False, rnn_size=512, rnn_type='LSTM', sample_rate=16000, save_model='wmt14.en-de', seed=-1, self_attn_type='scaled-dot', share_decoder_embeddings=False, share_embeddings=False, src_word_vec_size=512, start_checkpoint_at=1, start_decay_at=8, start_epoch=1, tensorboard=True, tensorboard_log_dir='runs/wmt_ende2', tgt_word_vec_size=512, train_from='', transformer_ff=2048, truncated_decoder=0, valid_batch_size=32, warmup_steps=8000, window_size=0.02, word_vec_size=512)

class TranslationModel:
    def __init__(self):
        self.sp = sentencepiece.SentencePieceProcessor()
        self.sp.Load(os.path.join(base_dir, './available_models/model-ende/sentencepiece.model'))
        self.output = io.StringIO()

        #fields, model, model_opt = onmt.model_builder.load_test_model(opt)

        model_path = opt.models[0]
        checkpoint = torch.load(model_path,
                            map_location=lambda storage, loc: storage)

        from onmt.utils.parse import ArgumentParser
        #model_opt = ArgumentParser.ckpt_model_opts(checkpoint['opt'])
        #print (model_opt)
        ArgumentParser.update_model_opts(model_opt)
        ArgumentParser.validate_model_opts(model_opt)
        print(model_opt)
        vocab = checkpoint['vocab']
        if onmt.inputters.old_style_vocab(vocab):
            fields = onmt.inputters.load_old_vocab(
                vocab, opt.data_type, dynamic_dict=model_opt.copy_attn
            )
        else:
            fields = vocab

        model = onmt.model_builder.build_base_model(model_opt, fields, onmt.utils.misc.use_gpu(opt), checkpoint,
                             opt.gpu)
        if opt.fp32:
            model.float()
        model.eval()
        model.generator.eval()

        scorer = onmt.translate.GNMTGlobalScorer.from_opt(opt)

        self.translator = onmt.translate.translator.Translator.from_opt(
            model,
            fields,
            opt,
            model_opt,
            global_scorer=scorer,
            out_file=self.output,
            report_score=True,
        )
        
    def translate(self, text):
        self.output.seek(0)
        self.output.truncate()
        text_joined = ''.join(text)
        start_pos = [0]
        p = 0
        for t in text:
            p += len(t)
            start_pos.append(p)
        text_split = re.split('(\S+)', text_joined)
        tokens = [s for s in self.sp.EncodeAsPieces(' '.join(text_split[1::2]))]
        x = (''.join(tokens).split('\u2581'))
        assert x[0] == '' and x[1:] == text_split[1::2]
        print (tokens)
        token_maps = []
        pos = 0
        numwhitespace = 0
        input_piece = 0
        for t in tokens:
            thislen = len(t)
            if t.startswith('\u2581'):
                pos += len(text_split[2*numwhitespace])
                numwhitespace += 1
                thislen -= 1
            if pos >= start_pos[input_piece+1]:
                # could move if most of the characters lie in next input piece
                # instead "all of them"
                input_piece += 1
            token_maps.append(input_piece)
            pos += thislen

        src = [tokens]
        src_dir=opt.src_dir
        attn_debug=True # opt.attn_debug

        data = onmt.inputters.Dataset(
                    self.translator.fields,
                    readers=[self.translator.src_reader],
                    data=[("src", src)],
                    dirs=[src_dir],
                    sort_key=onmt.inputters.str2sortkey[self.translator.data_type],
                    filter_pred=self.translator._filter_pred
                )

        data_iter = onmt.inputters.OrderedIterator(
                    dataset=data,
                    device=self.translator._dev,
                    batch_size=opt.batch_size,
                    train=False,
                    sort=False,
                    sort_within_batch=True,
                    shuffle=False
                )

        xlation_builder = onmt.translate.TranslationBuilder(
                    data, self.translator.fields, self.translator.n_best, self.translator.replace_unk, None
                )

        # Statistics
        counter = count(1)
        pred_score_total, pred_words_total = 0, 0
        gold_score_total, gold_words_total = 0, 0

        all_scores = []
        all_predictions = []

        start_time = time.time()

        for batch in data_iter:
            batch_data = self.translator.translate_batch(
                batch, data.src_vocabs, attn_debug
            )
            translations = xlation_builder.from_batch(batch_data)

            for trans in translations:
                all_scores += [trans.pred_scores[:self.translator.n_best]]
                pred_score_total += trans.pred_scores[0]
                pred_words_total += len(trans.pred_sents[0])

                n_best_preds = [" ".join(pred)
                                for pred in trans.pred_sents[:self.translator.n_best]]
                all_predictions += [n_best_preds]
                self.translator.out_file.write('\n'.join(n_best_preds) + '\n')
                self.translator.out_file.flush()

                if self.translator.verbose:
                    sent_number = next(counter)
                    output = trans.log(sent_number)

                if attn_debug:
                    preds = trans.pred_sents[0]
                    preds.append('</s>')

                    # FIXME: an alternative here would be map first and then take the argmax. it'll be more precise
                    attn_to_src_words = [token_maps[i] for i in trans.attns[0][:-2,:-1].argmax(1).tolist()]+[token_maps[i] for i in trans.attns[0][-2:].argmax(1).tolist()]
                    
                    attns = trans.attns[0].tolist()
                    if self.translator.data_type == 'text':
                        srcs = trans.src_raw
                    else:
                        srcs = [str(item) for item in range(len(attns[0]))]
                    header_format = "{:>10.10} " + "{:>10.7} " * len(srcs)
                    row_format = "{:>10.10} " + "{:>10.7f} " * len(srcs)
                    output = header_format.format("", *srcs) + '\n'
                    for word, row in zip(preds, attns):
                        max_index = row.index(max(row))
                        row_format = row_format.replace(
                            "{:>10.7f} ", "{:*>10.7f} ", max_index + 1)
                        row_format = row_format.replace(
                            "{:*>10.7f} ", "{:>10.7f} ", max_index)
                        output += row_format.format(word, *row) + '\n'
                        row_format = "{:>10.10} " + "{:>10.7f} " * len(srcs)
                    print(output)

        end_time = time.time()

        if self.translator.report_score:
            msg = self.translator._report_score('PRED', pred_score_total,
                                     pred_words_total)
            self.translator._log(msg)

        if self.translator.report_time:
            total_time = end_time - start_time
            self.translator._log("Total translation time (s): %f" % total_time)
            self.translator._log("Average translation time (s): %f" % (
                total_time / len(all_predictions)))
            self.translator._log("Tokens per second: %f" % (
                pred_words_total / total_time))

        if self.translator.dump_beam:
            import json
            json.dump(self.translator.translator.beam_accum,
                      codecs.open(self.translator.dump_beam, 'w', 'utf-8'))

        #return all_scores, all_predictions


        res = self.output.getvalue().split(' ')
        if res:
            res[0] = res[0].lstrip('\u2581')
        cur_attn = 0
        cur_w = ''
        res_words = []
        for attn, w in zip(attn_to_src_words, res):
            if attn != cur_attn:
                if cur_w:
                    res_words.append((cur_w, cur_attn))
                    cur_w = ''
                cur_attn = attn
            cur_w += w.replace('\u2581', ' ')
        if cur_w:
            res_words.append((cur_w.rstrip(), cur_attn))
        return res_words

if __name__ == '__main__':
    text = ["The qui", "ck brown fox jumps", " over the lazy dog."]
    #text = 'We are happy to welcome you here!'
    tr = TranslationModel()
    print(tr.translate(text))

