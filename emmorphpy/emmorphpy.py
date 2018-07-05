#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import jprops

import os
import re
import sys
import functools
import subprocess
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from stemmer import FlagsPy as Flags
from stemmer import stemmer_process


class EmMorphPy:

    def _create_extra_lexicon(self):
        """
        lexicon must be defined:
        that is a dictionary, each key is the wordform,
        corresponding values are stored in a list of tuples.

        e.g: lexicon = { 'utána': [('utána', '[KOT]', 'DETAILED_ANALYSIS')] }
        """
        self.lexicon = {'.': [('.', '[Punct]', '')],
                        ',': [(',', '[Punct]', '')],
                        ';': [(';', '[Punct]', '')],
                        ':': [(':', '[Punct]', '')],
                        '!': [('!', '[Punct]', '')],
                        '(': [('(', '[Punct]', '')],
                        ')': [(')', '[Punct]', '')],
                        '[': [('[', '[Punct]', '')],
                        ']': [(']', '[Punct]', '')],
                        '«': [('«', '[Punct]', '')],
                        '»': [('»', '[Punct]', '')],
                        '"': [('"', '[Punct]', '')],
                        '·': [('·', '[Punct]', '')],
                        '•': [('•', '[Punct]', '')],
                        '=': [('=', '[Punct]', '')],
                        '-': [('-', '[Punct]', '')],
                        '—': [('—', '[Punct]', '')],
                        '+': [('+', '[Punct]', '')],
                        '&': [('&', '[Punct]', '')],
                        '→': [('→', '[Punct]', '')],
                        '…': [('…', '[Punct]', '')],
                        '`': [('`', '[Punct]', '')],
                        '?': [('?', '[Punct]', '')],
                        '?!': [('?!', '[Punct]', '')],
                        '\'': [('\'', '[Punct]', '')],
                        '.........': [('.........', '[Punct]', '')],
                        '.......': [('.......', '[Punct]', '')],
                        '......': [('......', '[Punct]', '')],
                        '.....': [('.....', '[Punct]', '')],
                        '....': [('....', '[Punct]', '')],
                        '...': [('...', '[Punct]', '')],
                        '..': [('..', '[Punct]', '')]
                        }

    def _create_exceptions(self):
        """
        exceptions must be defined:
        that is a dictionary, each key is the wordform,
        corresponding values are stored in a set of tuples.

        e.g: exceptions = { 'hűha': {('hűha', '[ISZ]', 'DETAILED_ANALYSIS')} }
        """
        self.exceptions = {'+': {('', '[/N][Nom]', '+[/N]=++[Nom]')}
                           }

    @staticmethod
    def _load_config(java_props_file):
        with open(java_props_file) as fp:
            props = jprops.load_properties(fp)

        item_sep = props.get('stemmer.item_sep', ';')
        value_sep = props.get('stemmer.value_sep', '=')

        tag_config = defaultdict(set)
        for f_str, f in Flags.items():
            for t in props.get('stemmer.{0}'.format(f_str), '').split(item_sep):
                tag_config[t.encode('UTF-8')].add(f)
        tag_config = dict(tag_config)

        tag_convert = dict()
        for t in props.get('stemmer.convert', '').split(item_sep):
            k, v = t.split(value_sep, maxsplit=1)
            tag_convert[k.encode('UTF-8')] = v.encode('UTF-8')

        tag_replace = dict()
        for t in props.get('stemmer.replace', '').split(item_sep):
            k, v = t.split(value_sep, maxsplit=1)
            tag_replace[k.encode('UTF-8')] = v.encode('UTF-8')

        unwanted_patterns = [re.compile(props.get('stemmer.exclude{0}'.format(n)))
                             for n in range(100) if props.get('stemmer.exclude{0}'.format(n)) is not None]

        copy2surface_str = props.get('stemmer.copy2surface', '').encode('UTF-8')

        hfst_params = props.get('analyzer.params', '').split()
        if len(hfst_params) > 0:
            hfst_params = hfst_params[:-1]  # Cut the FSA

        return item_sep, value_sep, tag_config, tag_convert, tag_replace, unwanted_patterns, copy2surface_str,\
            hfst_params

    @staticmethod
    def _parse_stem(inp):
        item_surface = ''
        item_tag = ''
        item_lexical = ''
        items = []
        state = 0
        for ch in inp:
            if state in (0, 2):
                if ch == ':':  # switch sides
                    state += 1
                elif ch == ' ':
                    item_surface += ch
                else:
                    if len(item_tag) > 0:
                        if len(item_surface) > 0:
                            item_surface = '=' + item_surface
                        out = item_lexical + "[" + item_tag + "]" + item_surface
                        items.append(out)
                        item_surface = ''
                        item_tag = ''
                        item_lexical = ''
                    item_surface += ch
            elif state == 1:
                if ch == '[':  # tag opening
                    state = 3
                    if len(item_tag) > 0:
                        if len(item_surface) > 0:
                            item_surface = '=' + item_surface
                        out = item_lexical + "[" + item_tag + "]" + item_surface
                        items.append(out)
                        item_surface = ''
                        item_tag = ''
                        item_lexical = ''
                elif ch == ' ':  # beginning of next pair
                    state = 0
                else:
                    item_lexical += ch
            elif state == 3:
                if ch == ']':  # tag closing
                    state = 1
                elif ch == ' ':  # beginning of next pair (remember we are inside a tag)
                    state = 2
                else:
                    item_tag += ch
        if len(item_tag) > 0 or len(item_lexical) > 0 or len(item_surface) > 0:
            if len(item_surface) > 0:
                item_surface = '=' + item_surface
            out = item_lexical + "[" + item_tag + "]" + item_surface
            items.append(out)

        return '+'.join(items)  # Ez megy a stemmerbe...

    def __init__(self, props=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hfst-wrapper.props'),
                 fsa=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hu.hfstol'), hfst_lookup='hfst-lookup',
                 lexicon=None, exceptions=None):
        self.loaded_conf = self._load_config(props)
        params = self.loaded_conf[-1]  # HFST params
        self.conf_to_stemmer = *self.loaded_conf[2:5], self.loaded_conf[6]

        # Init extra anals
        if lexicon is None:
            self._create_extra_lexicon()
        else:
            self.lexicon = lexicon

        # Init exceptional anals
        if lexicon is None:
            self._create_exceptions()
        else:
            self.exceptions = exceptions

        try:
            self.p = subprocess.Popen([hfst_lookup, *params, fsa], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        except FileNotFoundError:
            print('ERROR: hfst-lookup not found at: {0} !'.format(hfst_lookup), file=sys.stderr)
            exit(1)

        self._spec_query('test')

    def close(self):
        self.p.wait()
        try:
            self.p.kill()
        except OSError:
            pass

    @functools.lru_cache(maxsize=2000)
    def _spec_query(self, inp):
        output = []
        try:
            self.p.stdin.write('{0}\n'.format(inp).encode('UTF-8'))
            self.p.stdin.flush()
        except BrokenPipeError:
            print(self.p.stderr.read().decode('UTF-8').rstrip(), file=sys.stderr)
            exit(self.p.wait())

        while True:
            out = ''
            try:
                out = self.p.stdout.readline()
            except BrokenPipeError:
                print(self.p.stderr.read().decode('UTF-8').rstrip(), file=sys.stderr)
                exit(self.p.wait())

            if len(out) <= 1:
                break
            ret = out.decode('UTF-8').strip().split('\t')
            if len(ret) == 3 and not ret[1].endswith('+?'):
                danal = self._parse_stem(ret[1])
                stem = stemmer_process(danal.encode('UTF-8'), *self.conf_to_stemmer)
                if len(stem) > 0:  # Suppress incorrect words
                    # Do not allow space in stem or detailed analyzis! eg. "jóbarát" -> "jó*** barát"
                    lemma, tag = stem
                    lemma = lemma.decode('UTF-8').replace(' ', '_')
                    tag = tag.decode('UTF-8').replace(' ', '_')
                    danal = danal.replace(' ', '_')
                    output.append((lemma, tag, danal))

        # Add extra anals
        output.extend(self.lexicon.get(inp, []))

        # Remove exceptional anals
        to_delete = self.exceptions.get(inp)
        if to_delete is not None:
            output = [anal for anal in output if anal not in to_delete]

        return output

    def stem(self, inp, out_mode=lambda x: sorted(set(x))):
        return out_mode((lemma, tag) for lemma, tag, _ in self._spec_query(inp))

    def analyze(self, inp, out_mode=lambda x: sorted(set(x))):
        return out_mode(danal for _, _, danal in self._spec_query(inp))

    def dstem(self, inp, out_mode=lambda x: sorted(set(x))):
        return out_mode((lemma, tag, danal) for lemma, tag, danal in self._spec_query(inp))

    def test(self):
        hfst_out_test = 'a:a l:l :o m:m :[/N] á:a :[Poss.3Sg] v:v a:a l:l :[Ins]'
        danal_test = 'alom[/N]=alm+a[Poss.3Sg]=á+val[Ins]=val'
        print('STEM', stemmer_process(danal_test.encode('UTF-8'), *self.conf_to_stemmer))
        print('STEM2', stemmer_process(self._parse_stem(hfst_out_test).encode('UTF-8'), *self.conf_to_stemmer))


if __name__ == '__main__':
    props_path = 'hfst-wrapper.props'
    morph_fst_path = 'hu.hfstol'
    emmorph = EmMorphPy(props_path, morph_fst_path)
    emmorph.test()
    print('almával', emmorph.stem('almával'))
    print('almával', emmorph.analyze('almával'))
    print('almával', emmorph.dstem('almával'))
    print('körtével', emmorph.stem('körtével'))
    print('körtével', emmorph.analyze('körtével'))
    print('körtével', emmorph.dstem('körtével'))
