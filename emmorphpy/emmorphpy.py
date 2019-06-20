#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import jprops

import os
import sys

import functools
import subprocess
from collections import defaultdict, OrderedDict
from json import dumps as json_dumps

morph_flags = {'STEM': 0, 'PREFIX': 1, 'COMP_MEMBER': 2, 'COMP_MUST_HAVE': 3, 'COMP_BEFORE_HYPHEN': 4,
               'STEM_IF_COMP': 5, 'INT_PUNCT': 6}


class EmMorphPy:
    pass_header = True

    def _create_extra_lexicon(self):
        """
        lexicon must be defined:
        that is a dictionary, each key is the wordform,
        corresponding values are stored in a list of tuples.

        e.g: lexicon = { 'utána': [('utána', '[KOT]', 'DETAILED_ANALYSIS', 'HFST-OUTPUT')] }
        """
        self.lexicon = {'.': [('.', '[Punct]', '', '')],
                        ',': [(',', '[Punct]', '', '')],
                        ';': [(';', '[Punct]', '', '')],
                        ':': [(':', '[Punct]', '', '')],
                        '!': [('!', '[Punct]', '', '')],
                        '(': [('(', '[Punct]', '', '')],
                        ')': [(')', '[Punct]', '', '')],
                        '[': [('[', '[Punct]', '', '')],
                        ']': [(']', '[Punct]', '', '')],
                        '«': [('«', '[Punct]', '', '')],
                        '»': [('»', '[Punct]', '', '')],
                        '"': [('"', '[Punct]', '', '')],
                        '·': [('·', '[Punct]', '', '')],
                        '•': [('•', '[Punct]', '', '')],
                        '=': [('=', '[Punct]', '', '')],
                        '-': [('-', '[Punct]', '', '')],
                        '—': [('—', '[Punct]', '', '')],
                        '+': [('+', '[Punct]', '', '')],
                        '&': [('&', '[Punct]', '', '')],
                        '→': [('→', '[Punct]', '', '')],
                        '…': [('…', '[Punct]', '', '')],
                        '`': [('`', '[Punct]', '', '')],
                        '?': [('?', '[Punct]', '', '')],
                        '?!': [('?!', '[Punct]', '', '')],
                        '\'': [('\'', '[Punct]', '', '')],
                        '.........': [('.........', '[Punct]', '', '')],
                        '.......': [('.......', '[Punct]', '', '')],
                        '......': [('......', '[Punct]', '', '')],
                        '.....': [('.....', '[Punct]', '', '')],
                        '....': [('....', '[Punct]', '', '')],
                        '...': [('...', '[Punct]', '', '')],
                        '..': [('..', '[Punct]', '', '')]
                        }

    def _create_exceptions(self):
        """
        exceptions must be defined:
        that is a dictionary, each key is the wordform,
        corresponding HFST-outputs are stored in a set of tuples.

        e.g: exceptions = { 'hűha': {'HFST-OUTPUT'} }
        """
        self.exceptions = {'+': {'+:+ :[/N] :[Nom]'}
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

        # Here we must have rsplit because "_PerfPtcp_Subj=tA/Adj=/Adj" -> "_PerfPtcp_Subj=tA/Adj": "/Adj"
        tag_convert = dict(t.rsplit(value_sep, maxsplit=1)
                           for t in props.get('stemmer.convert', '').split(item_sep)
                           if len(t.rsplit(value_sep, maxsplit=1)) == 2)

        tag_replace = dict(t.split(value_sep, maxsplit=1)
                           for t in props.get('stemmer.replace', '').split(item_sep)
                           if len(t.split(value_sep, maxsplit=1)) == 2)

        # Precompute mappings into Look-up tables
        STEM = 0
        PREFIX = 1
        COMP_MEMBER = 2
        COMP_MUST_HAVE = 3

        tag_config_is_stem = {}
        tag_config_compound_member = {}
        tag_convert_is_derivative = {}
        tag_convert_config = {}
        tag_replace_config = {}
        tag_replace_config_is_prefix = {}
        tag_replace_config_must_have_compound = {}

        for category, flags in tag_config.items():
            tag_config_is_stem[category] = STEM in flags
            tag_config_compound_member[category] = COMP_MEMBER in flags

            tagc = tag_convert.get(category) is not None
            tag_convert_is_derivative[category] = tagc
            flags_conv = tag_config.get(tagc, set())  # None -> set(), None can be hashed also!
            tag_convert_config[category] = flags_conv

            category_replaced = tag_replace.get(category, category)
            flags_conv = tag_config.get(category_replaced, set())
            tag_replace_config[category] = flags_conv
            tag_replace_config_is_prefix[category] = PREFIX in flags_conv

            tag_replace_config_must_have_compound[category] = int(COMP_MUST_HAVE in flags or
                                                                  COMP_MUST_HAVE in flags_conv)

        for category, category_conv in tag_convert.items():
            tag_convert_is_derivative[category] = True
            flags_conv = tag_config.get(category_conv, set())  # None -> set(), None can be hashed also!
            tag_convert_config[category] = flags_conv

        for category, category_replaced in tag_replace.items():
            flags_conv = tag_config.get(category_replaced, set())
            tag_replace_config[category] = flags_conv
            tag_replace_config_is_prefix[category] = PREFIX in flags_conv
            tag_replace_config_must_have_compound[category] = int(COMP_MUST_HAVE in tag_config.get(category, set()) or
                                                                  COMP_MUST_HAVE in flags_conv)

        # Not used
        # unwanted_patterns = [re.compile(props.get('stemmer.exclude{0}'.format(n)))
        #                      for n in range(100) if props.get('stemmer.exclude{0}'.format(n)) is not None]

        copy2surface = set(props.get('stemmer.copy2surface', ''))

        hfst_params = props.get('analyzer.params', '').split()
        if len(hfst_params) > 0:
            hfst_params = hfst_params[:-1]  # Cut the FSA

        # Bind methods for faster access
        tag_config_is_stem = tag_config_is_stem.get
        tag_config_compound_member = tag_config_compound_member.get
        tag_convert_is_derivative = tag_convert_is_derivative.get
        tag_convert_config = tag_convert_config.get
        tag_replace = tag_replace.get
        tag_replace_config = tag_replace_config.get
        tag_replace_config_is_prefix = tag_replace_config_is_prefix.get
        tag_replace_config_must_have_compound = tag_replace_config_must_have_compound.get

        return tag_convert, tag_replace, tag_config_is_stem, tag_config_compound_member, tag_convert_is_derivative, \
            tag_convert_config, tag_replace_config, tag_replace_config_is_prefix, \
            tag_replace_config_must_have_compound, copy2surface, hfst_params

    @staticmethod
    def _stemmer_process(input_str, tag_convert, tag_replace_get, tag_config_is_stem_get,
                         tag_config_compound_member_get, tag_convert_is_derivative_get, tag_convert_config_get,
                         tag_replace_config_get, tag_replace_config_is_prefix_get,
                         tag_replace_config_must_have_compound_get, copy2surface):

        STEM = 0
        COMP_MEMBER = 2
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

        # bind methods for easier access
        tag_convert_get = tag_convert.get

        for lexical, category, surface in input_str:
            is_stem = tag_config_is_stem_get(category, False)
            compound_member = tag_config_compound_member_get(category, False)

            # conversion
            is_derivative = tag_convert_is_derivative_get(category, False)
            flags_conv = tag_convert_config_get(category, set())

            # tag replacement
            category = tag_replace_get(category, category)
            flags = tag_replace_config_get(category, set())  # Replace if found else keep

            is_prefix = tag_replace_config_is_prefix_get(category, False)
            must_have_compounds += tag_replace_config_must_have_compound_get(category, 0)

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
                            m['category'] = tag_convert_get(m['category'], m['category'])
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
                 lexicon=None, exceptions=None, source_fields=None, target_fields=None):
        self.loaded_conf = list(self._load_config(props))
        params = self.loaded_conf.pop()  # HFST params

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

        # Store frequent methods for easier access
        self.proc_wait = self.p.wait
        self.proc_stdin = self.p.stdin
        self.proc_stdout_readline = self.p.stdout.readline
        self.proc_stderr_read = self.p.stderr.read

        # Field names for e-magyar TSV
        if source_fields is None:
            source_fields = set()

        if target_fields is None:
            target_fields = []

        self.source_fields = source_fields
        self.target_fields = target_fields

        # Test HFST at init
        self._spec_query('test')

    @staticmethod
    def _create_readable_ana(danal):
        """
        input : ki[/Prev]=ki+fizet[/V]=fizet+és[_Ger/N]=és+e[Poss.3Sg]=é+t[Acc]=t
        immed.: ki[/Prev]   +fizet[/V]      +és[_Ger/N]   +e[Poss.3Sg]=é+t[Acc]
        output: ki[/Prev] + fizet[/V] + és[_Ger/N] + e[Poss.3Sg]=é + t[Acc]
        """
        out = []
        for deep, tag, surf in danal:
            eq = '='
            if deep == surf:
                eq = ''
                surf = ''
            out.append('{0}[{1}]{2}{3}'.format(deep, tag, eq, surf).replace(' ', '_'))
        return ' + '.join(out)

    @staticmethod
    def _format_danal(danal):
        return '+'.join(map(lambda x: '{0}[{1}]={2}'.format(*x), danal))

    @staticmethod  # TODO: Maybe its not a good idea to hand-wire here the name and order of the features
    def zip_w_keys(values, keys=('lemma', 'tag', 'morphana', 'readable', 'twolevel')):
        # TODO: From Python 3.7 no need for ordered dict to keep the insertion order
        # TODO: Its enough to write: {'lemma': lemma, 'tag': tag, 'morphana': danal, 'readable': readable}
        return OrderedDict(zip(keys, values))

    def process_sentence(self, sen, field_names):
        for tok in sen:
            output = self.dstem(tok[field_names[0]], out_mode=lambda x: [self.zip_w_keys(analysis) for analysis in x])
            output_json = json_dumps(output, ensure_ascii=False)
            tok.append(output_json)
        return sen

    @staticmethod
    def prepare_fields(field_names):
        return [field_names['form']]  # TODO: Maybe its not a good idea to hand-wire here the name of the features

    def close(self):
        self.p.wait()
        try:
            self.p.kill()
        except OSError:
            pass

    @functools.lru_cache(maxsize=20000)
    def _spec_query(self, inp):
        output = []
        proc_wait = self.proc_wait
        proc_stdin = self.proc_stdin
        proc_stdout_readline = self.proc_stdout_readline
        proc_stderr_read = self.proc_stderr_read

        parse_stem = self._parse_stem
        stemmer_process = self._stemmer_process
        tag_convert, tag_replace, tag_config_is_stem, tag_config_compound_member, tag_convert_is_derivative, \
            tag_convert_config, tag_replace_config, tag_replace_config_is_prefix, \
            tag_replace_config_must_have_compound, copy2surface = self.loaded_conf

        try:
            proc_stdin.write('{0}\n'.format(inp).encode('UTF-8'))
            proc_stdin.flush()
        except BrokenPipeError:
            print(proc_stderr_read().decode('UTF-8').rstrip(), file=sys.stderr)
            exit(proc_wait())

        while True:
            out = ''
            try:
                out = proc_stdout_readline()
            except BrokenPipeError:
                print(proc_stderr_read().decode('UTF-8').rstrip(), file=sys.stderr)
                exit(proc_wait())

            if len(out) <= 1:
                break
            ret = out.decode('UTF-8').strip().split('\t')
            if len(ret) == 3 and not ret[1].endswith('+?'):
                hfst_out = ret[1]

                # Omit exceptional anals before any processing (parse_stem, stemmer_process)
                if hfst_out not in self.exceptions.get(inp, {}):
                    danal = parse_stem(hfst_out)
                    stem = stemmer_process(danal, tag_convert, tag_replace, tag_config_is_stem,
                                           tag_config_compound_member, tag_convert_is_derivative, tag_convert_config,
                                           tag_replace_config, tag_replace_config_is_prefix,
                                           tag_replace_config_must_have_compound, copy2surface)
                    if len(stem) > 0:  # Suppress incorrect words
                        output.append((*stem, danal, hfst_out))  # lemma, tag, danal

        # Add extra anals without any processing (parse_stem, stemmer_process)
        output.extend(self.lexicon.get(inp, []))

        return output

    # Do allow space in stem or detailed analyzis! eg. "jóbarát" -> "jó*** barát"
    def stem(self, inp, out_mode=lambda x: sorted(set(x))):
        return out_mode((lemma, tag) for lemma, tag, _, _ in self._spec_query(inp))

    def analyze(self, inp, out_mode=lambda x: sorted(set(x))):
        return out_mode(self._format_danal(danal) for _, _, danal, _ in self._spec_query(inp))

    def dstem(self, inp, out_mode=lambda x: sorted(set(x))):
        return out_mode((lemma, tag, self._format_danal(danal), self._create_readable_ana(danal), hfst_out)
                        for lemma, tag, danal, hfst_out in self._spec_query(inp))

    def test(self):
        hfst_out_test = 'a:a l:l :o m:m :[/N] a:a :[Poss.3Sg] :[Nom]'
        danal_test = [('alom', '/N', 'alm'), ('a', 'Poss.3Sg', 'á'), ('val', 'Ins', 'val')]
        loaded_conf = self._load_config(props_path)[:-1]
        print('STEM', self._stemmer_process(danal_test, *loaded_conf))
        print('STEM2', self._stemmer_process(self._parse_stem(hfst_out_test), *loaded_conf))


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
    print(emmorph.process_sentence([['Az'], ['árvíztűrőtükörfúrógép'], ['"hasznos\''], ['.']], [0]))
