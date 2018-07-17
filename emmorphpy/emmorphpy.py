#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import jprops

import os
import re
import sys
import functools
import subprocess
from collections import defaultdict


morph_flags = {'STEM': 0, 'PREFIX': 1, 'COMP_MEMBER': 2, 'COMP_MUST_HAVE': 3, 'COMP_BEFORE_HYPHEN': 4,
               'STEM_IF_COMP': 5, 'INT_PUNCT': 6}


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
        for f, v in morph_flags.items():
            for t in props.get('stemmer.{0}'.format(f), '').split(item_sep):
                tag_config[t].add(v)

        tag_convert = dict(t.split(value_sep, maxsplit=1)
                           for t in props.get('stemmer.convert', '').split(item_sep)
                           if len(t.split(value_sep, maxsplit=1)) == 2)

        tag_replace = dict(t.split(value_sep, maxsplit=1)
                           for t in props.get('stemmer.replace', '').split(item_sep)
                           if len(t.split(value_sep, maxsplit=1)) == 2)

        unwanted_patterns = [re.compile(props.get('stemmer.exclude{0}'.format(n)))
                             for n in range(100) if props.get('stemmer.exclude{0}'.format(n)) is not None]

        copy2surface = set(props.get('stemmer.copy2surface', ''))

        hfst_params = props.get('analyzer.params', '').split()
        if len(hfst_params) > 0:
            hfst_params = hfst_params[:-1]  # Cut the FSA

        return item_sep, value_sep, tag_config, tag_convert, tag_replace, unwanted_patterns, copy2surface,\
            hfst_params

    @staticmethod
    def _stemmer_process(input_str, conf):
        _, _, tag_config, tag_convert, tag_replace, _, copy2surface, _ = conf

        STEM = 0
        PREFIX = 1
        COMP_MEMBER = 2
        COMP_MUST_HAVE = 3
        COMP_BEFORE_HYPHEN = 4
        STEM_IF_COMP = 5
        INT_PUNCT = 6

        derivative = False
        must_have_compounds = 0   # how many morphemes with "compound must have" property
        last_stem_code = -1       # last stem position
        prev_last_stem_code = -1  # prev state of last_stem_code
        hyphen_pos = -1           # position of a hyphen
        look_for_compound = False

        sure_compound = False
        prev_compound = False

        # Stem
        morphs = []
        len_morphs = 0
        sz_stem = ''
        stem_code = -1
        compounds = 0

        for lexical, category, surface in input_str:
            # 6-3-as szabály miatt (2011.07.18. NA: "Azt kéne csinálni, hogy a morfológia által
            #  visszaadott cimkék elején lévő részt a `-ig ki kell törölni mielőtt bármi mást csinálnál")
            category = category[category.find('`') + 1:]  # If not found -> -1 +1 = [0:] = the whole string
            flags = tag_config[category]

            is_stem = STEM in flags
            compound_member = COMP_MEMBER in flags

            # conversion
            tagc = tag_convert.get(category)
            is_derivative = tagc is not None
            flags_conv = tag_config.get(tagc, set())  # None -> set(), None can be hashed also!

            # tag replacement
            r = tag_replace.get(category)
            if r is not None:
                category = r
                flags = tag_config.get(category, flags)  # Replace if found else keep

            is_prefix = PREFIX in flags
            must_have_compounds += int(COMP_MUST_HAVE in flags or
                                       COMP_MUST_HAVE in flags_conv)

            # copy spec cars from lexical
            lex = lexical
            if any(c in lex for c in copy2surface):  # else nothing to do :)
                surf = surface
                for i, l_i in enumerate(lex):
                    if l_i in copy2surface:
                        surf = ''.join((surf[0:i], l_i, surf[i:]))

                surface = surf

            if compounds > 1 and hyphen_pos != len_morphs - 2:
                # if it is in compound word: lowercase ("WolfGang"=>"Wolfgang")
                lexical = lexical.lower()

            # van-e 2 egymást követő compound member, (ha igen, tuti összetett)
            sure_compound |= prev_compound and compound_member
            prev_compound = compound_member

            # ha volt már tő és ez képző => a konvertáltjait megkeressük, ha compound member, akkor beállítjuk
            compound_member |= look_for_compound and COMP_MEMBER in flags_conv

            morph = {'lexical': lexical,
                     'surface': surface,
                     'category': category,
                     'is_prefix': is_prefix,
                     'is_stem': is_stem,
                     'is_derivative': is_derivative,
                     'flags': flags,
                     'flags_conv': flags_conv}
            morphs.append(morph)
            len_morphs = len(morphs)

            if is_stem:
                if lexical == '-':
                    hyphen_pos = len_morphs - 1

                if stem_code == -1:
                    stem_code = len_morphs - 1  # save pos...

                last_stem_code = len_morphs - 1
                if prev_last_stem_code != -1 and lexical != '-':
                    convert = False
                    # Mutate list in loop!
                    for i in range(last_stem_code, prev_last_stem_code - 1, -1):
                        m = morphs[i]
                        convert |= m['is_stem']
                        if convert and m['is_derivative']:
                            m['category'] = tag_convert.get(m['category'])  # TODO: A None itt nincs kezelve
                            fc = m['flags_conv']
                            m['flags'] = fc
                            m['is_stem'] |= STEM in fc

                prev_last_stem_code = last_stem_code
                # első tőalkotó után bekapcsoljuk, ha ez True, akkor keresünk olyan képzőt,
                # ami compound membert csinál belőle
                look_for_compound |= not derivative

            # ha cmember => növelem
            # ha tő ÉS jön egy compoundMember kepző => növelem
            if compound_member:
                compounds += 1
                look_for_compound = False

        """
        // === creating stem ===
        // is it compound?
        /*
            -ha 2 tove van
            -ha 1 tove + (conv->FN OR stem if compound)


        teszt-esetek:
            nagybefekteto
            husdarabolo
            husdarabologep
            darabolo-evo
            daraboloevo
            darabologep
            Lajos-
            piros-
         */
        //TODO: es ha tobb kotojel van?
        //"tájlátogató-felvilágosító"
        """
        if sure_compound:
            # ez biztos összetett szó, mert 2 egymast követő compundmember van benne
            # ha nincs benne FN, de képzett főnév igen, azt megmenti
            # look for stem if compounds
            for n in range(len_morphs):
                m = morphs[n]  # Mutate list in loop!
                if STEM_IF_COMP in m['flags']:
                    m['is_stem'] = True
                    m['category'] = tag_convert[m['category']]  # TODO: A None itt nincs kezelve
                    m['flags'] = m['flags_conv']
                    stem_code = n
                    last_stem_code = max(n, last_stem_code)

        # kötőjeles akkor lehet összetett szó, ha a kötőjel előtt [compound before hyphen] all
        # "aa[FN][NOM]-bb[FN][NOM]" vagy "aa[FN]-bb[FN]"
        # pl "Árpad-ház"

        # ha a kotojel elotti ures es az azt megelozo toalkoto =>
        # ha a kotojel elott rag van, akkor ez nem osszetett szo
        # TODO: Simplify bool expression...
        compound = compounds > 1 and hyphen_pos == -1 or must_have_compounds > 0
        if hyphen_pos > 0 and compound:
            m = morphs[hyphen_pos - 1]
            if COMP_BEFORE_HYPHEN not in m['flags'] or (hyphen_pos > 1 and len(m['lexical']) == 0 and
                                                        len(m['surface']) == 0 and
                                                        not morphs[hyphen_pos - 2]['is_stem']):
                    compound = False

        internal_punct = False
        # most megmentjuk attol, hogy a PUNCT, PER vegu szavak to tipusa PUNCT legyen
        for n in range(len_morphs-1, -1, -1):
            m = morphs[n]  # Mutate list in loop!
            if INT_PUNCT not in m['flags']:
                break
            internal_punct = True
            m['is_stem'] = False

        while last_stem_code > 0 and not morphs[last_stem_code]['is_stem']:
            last_stem_code -= 1

        if compound and not sure_compound:  # összetett szavaknál a stemIfCompoundokat átalakítja
            for n in range(len_morphs):
                m = morphs[n]  # Mutate list in loop!
                if STEM_IF_COMP in m['flags']:
                    m['is_stem'] = True
                    m['category'] = tag_convert[m['category']]  # TODO: A None itt nincs kezelve
                    m['flags'] = m['flags_conv']
                    if n >= last_stem_code:
                        last_stem_code = n

        # végén van egy kötőjel, ha előtte ragozoztt szó áll, nem lehet szoösszetétel
        # pl. "magán-"
        # ha a kötőjel előtti üres és az azt megelőző tőalkotó => hadd éljen, nem megy bele az ikerszó ágba
        # ez már ikerszó nem lehet
        # TODO: Simplify bool expression...
        internal_punct_and = True
        if internal_punct and hyphen_pos > 0:
            m = morphs[hyphen_pos - 1]
            if COMP_BEFORE_HYPHEN in m['flags'] and not (hyphen_pos > 1 and len(m['lexical']) == 0
                                                         and len(m['surface']) == 0
                                                         and not morphs[hyphen_pos - 2]['is_stem']):
                internal_punct_and = False

        # beleégetjük hogy a szóközi kötőjel stem
        for n in range(1, len_morphs-2):
            m = morphs[n]  # Mutate list in loop!
            m['is_stem'] |= morphs[n - 1]['is_stem'] and morphs[n + 1]['is_stem'] and \
                (m['surface'] == '-' or m['lexical'] == '-')

        if internal_punct_and and hyphen_pos != -1 and not compound:  # ikerszo

            half = False
            half_pos = next((z for z in range(max(hyphen_pos - 1, 0), 0, -1) if morphs[z]['is_stem']), stem_code)

            tmp1 = ''
            tmp2 = ''
            for n, m in enumerate(morphs):
                if m['lexical'] == '-':
                    half = True
                    half_pos = last_stem_code

                if m['is_stem']:
                    if n < half_pos and len(m['surface']) != 0:
                        sz_stem += m['surface']
                    else:
                        sz_stem += m['lexical']
                else:
                    if not half:
                        tmp1 += m['category'] + ' '
                    else:
                        tmp2 += m['category'] + ' '

            if tmp1 != tmp2:  # BAD input, stem is dropped
                sz_stem += '<incorrect word>'

        else:  # simple case
            if len_morphs >= last_stem_code:
                for n, m in enumerate(morphs[:last_stem_code+1]):
                    if m['is_stem']:
                        if n < last_stem_code:
                            sz_stem += m['surface']
                        else:
                            sz_stem += m['lexical']

        if sz_stem.endswith('<incorrect word>'):
            return ()
        else:
            tag = '[{0}]'.format(']['.join(m['category'] for n, m in enumerate(morphs)
                                 if n >= last_stem_code or m['is_prefix']))
            return sz_stem, tag

    @staticmethod
    def _parse_stem(inp):
        item_surface = ''
        item_tag = ''
        item_lexical = ''
        items = []
        state = 0
        for ch in inp:
            if state in (0, 2):
                if ch == ':':
                    state += 1
                elif ch == ' ':
                    item_surface += ch
                else:
                    if len(item_tag) > 0:
                        items.append((item_lexical, item_tag, item_surface))
                        item_lexical, item_tag, item_surface, = '', '', ''

                    item_surface += ch
            elif state == 1:
                if ch == '[':  # tag opening
                    state = 3
                    if len(item_tag) > 0:
                        items.append((item_lexical, item_tag, item_surface))
                        item_lexical, item_tag, item_surface, = '', '', ''
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
            items.append((item_lexical, item_tag, item_surface))

        return items  # Ez megy a stemmerbe... '+'.join(...)

    def __init__(self, props=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hfst-wrapper.props'),
                 fsa=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hu.hfstol'), hfst_lookup='hfst-lookup',
                 lexicon=None, exceptions=None):
        self.loaded_conf = self._load_config(props)
        params = self.loaded_conf[-1]  # HFST params

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

    @functools.lru_cache(maxsize=20000)
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
                stem = self._stemmer_process(danal, self.loaded_conf)
                if len(stem) > 0:  # Suppress incorrect words
                    output.append((*stem, danal))  # lemma, tag, danal

        # Add extra anals
        output.extend(self.lexicon.get(inp, []))

        # Remove exceptional anals
        to_delete = self.exceptions.get(inp)
        if to_delete is not None:
            output = [anal for anal in output if anal not in to_delete]

        return output

    # Do not allow space in stem or detailed analyzis! eg. "jóbarát" -> "jó*** barát"
    def stem(self, inp, out_mode=lambda x: sorted(set(x))):
        return out_mode((lemma.replace(' ', '_'), tag.replace(' ', '_'))
                        for lemma, tag, _ in self._spec_query(inp))

    def analyze(self, inp, out_mode=lambda x: sorted(set(x))):
        return out_mode('+'.join(map(lambda x: '{0}[{1}]={2}'.format(*x), danal)).replace(' ', '_')
                        for _, _, danal in self._spec_query(inp))

    def dstem(self, inp, out_mode=lambda x: sorted(set(x))):
        return out_mode((lemma.replace(' ', '_'), tag.replace(' ', '_'),
                         '+'.join(map(lambda x: '{0}[{1}]={2}'.format(*x), danal)).replace(' ', '_'))
                        for lemma, tag, danal in self._spec_query(inp))

    def test(self):
        hfst_out_test = 'a:a l:l :o m:m :[/N] a:a :[Poss.3Sg] :[Nom]'
        danal_test = [('alom', '/N', 'alm'), ('a', 'Poss.3Sg', 'á'), ('val', 'Ins', 'val')]
        loaded_conf = self._load_config(props_path)
        print('STEM', self._stemmer_process(danal_test, loaded_conf))
        print('STEM2', self._stemmer_process(self._parse_stem(hfst_out_test), loaded_conf))


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
