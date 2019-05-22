#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from itertools import count
import types
import time
import io
import re
import torch

import sys
import os
import codecs
import copy

import simplejson

import onmt
import onmt.model_builder
import onmt.translate
import onmt.utils.parse

import sentencepiece

# import spacy

# language_model_en = spacy.load("en")

class SentencePieceTokenizer:
    def __init__(self, path):
        self.sp = sentencepiece.SentencePieceProcessor()
        self.sp.Load(path)

    def tokenize(self, s):
        return self.sp.EncodeAsPieces(s)


class TranslationModel:
    def __init__(self, model_path: str, model_opt: dict={}):
        self.output = io.StringIO()

        parser = onmt.utils.parse.ArgumentParser()
        onmt.opts.config_opts(parser)
        onmt.opts.translate_opts(parser)
        opt = {a.dest: a.default for a  in parser._actions}
        opt.update(model_opt)
        opt = types.SimpleNamespace(**opt)
        opt.models = [model_path]
        self.opt = opt
        fields, model, model_opt = onmt.model_builder.load_test_model(opt)

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

    def translate(self, text, tokenizer):
        self.output.seek(0)
        self.output.truncate()
        text_joined = ''.join(text)
        start_pos = [0]
        p = 0
        for t in text:
            p += len(t)
            start_pos.append(p)
        text_split = re.split(r'(\S+)', text_joined)
        tokens = [s for s in tokenizer.tokenize(' '.join(text_split[1::2]))]
        x = (''.join(tokens).split('\u2581'))
        assert x[0] == '' and x[1:] == text_split[1::2]

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
        src_dir = self.opt.src_dir
        attn_debug = True  # opt.attn_debug

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
                    batch_size=self.opt.batch_size,
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
                    attn_to_src_words = ([token_maps[i] for i in trans.attns[0][:-2, :-1].argmax(1).tolist()]
                                         + [token_maps[i] for i in trans.attns[0][-2:].argmax(1).tolist()])

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


def load_model_config(path: str):
    try:
        conf = simplejson.load(open(path))
        conf['base_path'] = path
    except Exception as e:  # noqa: F841
        conf = None
    return conf


translation_models = {}


def get_tokenizer(path, cfg):
    if cfg['type'] == 'sentencepiece':
        return SentencePieceTokenizer(path)
    else:
        raise Exception("unknown tokenizer type {}".format(cfg['type']))


def translate(cfg, words):
    # os.path.join(base_dir, './available_models/model-ende/sentencepiece.model')
    base_dir = os.path.dirname(cfg['base_path'])
    tokenizer_path = os.path.join(base_dir, cfg['tokenizer']['model'])
    tokenizer_key = 'tokenizer-' + cfg['tokenizer']['type']+': + tokenizer_path'
    tokenizer = translation_models.get(tokenizer_key)
    if tokenizer is None:
        tokenizer = get_tokenizer(tokenizer_path, cfg['tokenizer'])
        translation_models['tokenizer_key'] = tokenizer

    model_path = os.path.join(base_dir, cfg["model"])
    model_key = 'translationmodel:' + model_path
    model = translation_models.get(model_key)  # fix - use the model we want
    if model is None:
        model = TranslationModel(model_path, cfg.get("opt", {}))
        translation_models[model_key] = model
    return model.translate(words, tokenizer=tokenizer)


if __name__ == '__main__':
    text = ["The qui", "ck brown fox jumps", " over the lazy dog."]
    # text = 'We are happy to welcome you here!'
    tr = TranslationModel()
    print(tr.translate(text))
