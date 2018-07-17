#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import jprops

import os
import re
import sys
import functools
import subprocess
from enum import Enum
from collections import defaultdict


class Flags(Enum):
    STEM = 0
    PREFIX = 1
    COMP_MEMBER = 2
    COMP_DELIM = 3
    COMP_MUST_HAVE = 4
    COMP_BEFORE_HYPHEN = 5
    STEM_IF_COMP = 6
    INT_PUNCT = 7


class MorphemeInfo:
    def __init__(self):
        self.lexical = ""
        self.surface = ""
        self.category = ""
        self.is_prefix = False  # Maybe redundant
        self.is_stem = False  # Maybe redundant
        self.is_derivative = False
        # self.is_compound_member = False     # Not used
        # self.is_compound_delimiter = False  # Not used
        self.flags = set()
        self.flags_conv = set()

    """
    def __str__(self):
        return "lexical: {0} |surface: {1} |category: {2} |is_prefix: {3} |is_stem: {4} |is_derivative: {5} " \
               "|is_compound_member: {6} |is_compound_delimiter: |flags: {7} |flags_conv: {8}".format(
                self.lexical, self.surface, self.category, self.is_prefix, self.is_stem, self.is_derivative,
                self.is_compound_member, self.is_compound_delimiter, self.flags, self.flags_conv)
    """


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
        for f in Flags:
            for t in props.get('stemmer.{0}'.format(str(f).split('.')[1]), '').split(item_sep):
                tag_config[t].add(f)

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
        item_sep, value_sep, tag_config, tag_convert, tag_replace, unwanted_patterns, copy2surface, _ = conf

        derivative = False
        must_have_compounds = 0  # how many morphemes with "compound must have" property
        last_stem_code = -1     # last stem position
        prev_last_stem_code = -1  # prev state of last_stem_code
        hyphen_pos = -1         # position of a hyphen
        look_for_compound = False

        sure_compound = False
        prev_compound = False

        # Stem
        morphs = []
        sz_stem = ''
        stem_code = -1
        compounds = 0

        for item_lexical, item_tag, item_surface in input_str:
            morph = MorphemeInfo()
            morph.lexical = item_lexical
            morph.surface = item_surface
            sz_cur_cod = item_tag

            # 6-3-as szabály miatt (2011.07.18. NA: "Azt kéne csinálni, hogy a morfológia által
            #  visszaadott cimkék elején lévő részt a `-ig ki kell törölni mielőtt bármi mást csinálnál")
            sz_cur_cod = sz_cur_cod[sz_cur_cod.find('`') + 1:]  # If not found -> -1 +1 = [0:] = the whole string
            morph.flags = tag_config[sz_cur_cod]

            morph.is_stem = Flags.STEM in morph.flags
            compound_member = Flags.COMP_MEMBER in morph.flags
            morph.is_compound_member = compound_member

            # conversion
            tagc = tag_convert.get(sz_cur_cod)
            morph.is_derivative = tagc is not None
            morph.flags_conv = tag_config.get(tagc, set())  # None -> set(), None can be hashed also!

            # tag replacement
            r = tag_replace.get(sz_cur_cod)
            if r is not None:
                sz_cur_cod = r
                morph.flags = tag_config.get(sz_cur_cod, morph.flags)  # Replace if found else keep

            morph.category = sz_cur_cod
            # morph.is_compound_delimiter = Flags.COMP_DELIM in morph.flags
            morph.is_prefix = Flags.PREFIX in morph.flags

            must_have_compounds += int(Flags.COMP_MUST_HAVE in morph.flags or
                                       Flags.COMP_MUST_HAVE in morph.flags_conv)

            # copy spec cars from lexical
            lex = morph.lexical
            if any(c in lex for c in copy2surface):  # else nothing to do :)
                surf = morph.surface
                for i, l_i in enumerate(lex):
                    if l_i in copy2surface:
                        surf = ''.join((surf[0:i], l_i, surf[i:]))

                morph.surface = surf

            # if (m_GetCaseFromInput)  // lexical gets case state from surface
            #   CaseConvert(surface, (curr_analysis.morp.end()-1)->lexical/*prev_lexical*/);
            # else
            if compounds > 1 and hyphen_pos != len(morphs) - 2:  # /*curr_analysis.compound_word*/
                # if it is in compound word: lowercase ("WolfGang"=>"Wolfgang")
                morph.lexical = morph.lexical.lower()

            # van-e 2 egymást követő compound member, (ha igen, tuti összetett)
            sure_compound |= prev_compound and compound_member
            prev_compound = compound_member

            # ha volt már tő és ez képző => a konvertáltjait megkeressük, ha compound member, akkor beállítjuk
            tmp_bool = look_for_compound and Flags.COMP_MEMBER in morph.flags_conv
            compound_member |= tmp_bool
            # morph.is_compound_member |= tmp_bool

            morphs.append(morph)

            if morph.is_stem:
                if morph.lexical == '-':
                    hyphen_pos = len(morphs) - 1

                if stem_code == -1:
                    stem_code = len(morphs) - 1  # save pos...

                last_stem_code = len(morphs) - 1
                if prev_last_stem_code != -1 and morph.lexical != '-':
                    convert = False
                    # Mutate list in loop!
                    for i in range(last_stem_code, prev_last_stem_code - 1, -1):
                        m = morphs[i]
                        convert |= m.is_stem
                        if convert and m.is_derivative:
                            # TODO: A None itt nincs kezelve
                            m.category = tag_convert.get(m.category)
                            m.flags = m.flags_conv
                            m.is_stem |= m.flags is not None and Flags.STEM in m.flags

                prev_last_stem_code = last_stem_code
                # első tőalkotó után bekapcsoljuk, ha ez True, akkor keresünk olyan képzőt,
                #  ami compound membert csinál belőle
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
        if sure_compound:  # curr_analysis.compounds > 1){
            # ez biztos összetett szó, mert 2 egymast követő compundmember van benne
            # ha nincs benne FN, de képzett főnév igen, azt megmenti
            # look for stem if compounds
            for n, m in enumerate(morphs):
                m = morphs[n]  # Mutate list in loop!
                if Flags.STEM_IF_COMP in m.flags:
                    m.is_stem = True
                    m.category = tag_convert[m.category]  # TODO: A None itt nincs kezelve
                    m.flags = m.flags_conv
                    stem_code = n
                    last_stem_code = max(n, last_stem_code)

        # TODO: Simplify bool expression...
        compound = compounds > 1 and hyphen_pos == -1 or must_have_compounds > 0
        if hyphen_pos > 0 and compound:
            # kötőjeles akkor lehet összetett szó, ha a kötőjel előtt [compound before hyphen] all
            # "aa[FN][NOM]-bb[FN][NOM]" vagy "aa[FN]-bb[FN]"
            # pl "Árpad-ház"

            m = morphs[hyphen_pos - 1]
            # ha a kotojel elotti ures es az azt megelozo toalkoto =>
            # ha a kotojel elott rag van, akkor ez nem osszetett szo
            if Flags.COMP_BEFORE_HYPHEN not in m.flags or (hyphen_pos > 1 and len(m.lexical) == 0 and
                                                           len(m.surface) == 0 and
                                                           not morphs[hyphen_pos - 2].is_stem):
                    compound = False

        # compound_word = compound

        internal_punct = False
        # most megmentjuk attol, hogy a PUNCT, PER vegu szavak to tipusa PUNCT legyen
        for n, m in enumerate(reversed(morphs), start=1):
            m = morphs[-1*n]  # Mutate list in loop!
            if Flags.INT_PUNCT not in m.flags:
                break
            internal_punct = True
            m.is_stem = False

        while last_stem_code > 0 and not morphs[last_stem_code].is_stem:
            last_stem_code -= 1

        if compound and not sure_compound:
            # összetett szavaknál a stemIfCompoundokat átalakítja
            for n, m in enumerate(morphs):
                m = morphs[n]  # Mutate list in loop!
                if Flags.STEM_IF_COMP in m.flags:
                    m.is_stem = True
                    m.category = tag_convert[m.category]  # TODO: A None itt nincs kezelve
                    m.flags = m.flags_conv
                    if n >= last_stem_code:
                        last_stem_code = n

        """
        # összetett szavaknál beteszi a + jelet...
        coffset = 0
        for m in morphs:
            if m.is_compound_member or m.is_compound_delimiter:
                if coffset != 0:
                    compound_delims.append(coffset)  # az utolsó nem kell: ott már vége a szónak
                coffset += len(m.surface)
        """

        # TODO: Simplify bool expression...
        internal_punct_and = True
        if internal_punct and hyphen_pos > 0:
            # végén van egy kötőjel, ha előtte ragozoztt szó áll, nem lehet szoösszetétel
            # pl. "magán-"
            m = morphs[hyphen_pos - 1]
            # ha a kötőjel előtti üres és az azt megelőző tőalkotó =>
            # hadd éljen, nem megy bele az ikerszó ágba
            # ez már ikerszó nem lehet
            if Flags.COMP_BEFORE_HYPHEN in m.flags and not (hyphen_pos > 1 and len(m.lexical) == 0
                                                            and len(m.surface) == 0
                                                            and not morphs[hyphen_pos - 2].is_stem):
                internal_punct_and = False

        # beleégetjük hogy a szóközi kötőjel stem
        for n, m in enumerate(morphs[1:-1], start=1):
            m = morphs[n]
            m.is_stem |= morphs[n - 1].is_stem and morphs[n + 1].is_stem and \
                (m.surface == '-' or m.lexical == '-')

        if internal_punct_and and hyphen_pos != -1 and not compound:
            # ikerszo

            half = False
            half_pos = stem_code  # hyphen_pos;//last_stem_code;//;
            for z in range(max(hyphen_pos - 1, 0), 0, -1):
                if morphs[z].is_stem:
                    half_pos = z
                    break

            tmp1 = ''
            tmp2 = ''
            for n, m in enumerate(morphs):
                if m.lexical == '-':
                    half = True
                    half_pos = last_stem_code

                if m.is_stem:
                    if n < half_pos and len(m.surface) != 0:
                            sz_stem += m.surface
                    else:
                        sz_stem += m.lexical
                else:
                    if not half:
                        tmp1 += m.category + ' '
                    else:
                        tmp2 += m.category + ' '

            if tmp1 != tmp2:
                # BAD input, stem is dropped
                # incorrect_word = True
                sz_stem += '<incorrect word>'
                # return 0;

        else:
            # simple case

            if len(morphs) >= last_stem_code:
                for n in range(last_stem_code+1):
                    if morphs[n].is_stem:
                        if n < last_stem_code:
                            sz_stem += morphs[n].surface
                        elif n == last_stem_code:  # /*curr_analysis.stem_code*/
                            sz_stem += morphs[n].lexical

        """
        //          if (m_regexp_stem_decision)
        //          {
        //              //call regular function
        //              SelectStem(curr_analysis);
        //          }
        """
        # print("STEM_OUTPUT:", stem)
        if sz_stem.endswith('<incorrect word>'):
            return ()
        else:
            tag = ''.join('[{0}]'.format(m.category) for n, m in enumerate(morphs)
                          if n >= last_stem_code or m.is_prefix)
            return sz_stem, tag

    @staticmethod
    def put_together(morph):
        item_lexical, item_tag, item_surface = morph
        item_surface = '=' + item_surface
        out = '{0}[{1}]{2}'.format(item_lexical, item_tag, item_surface)
        return out

    @staticmethod
    def _parse_stem(inp):
        item_surface = ''
        item_tag = ''
        item_lexical = ''
        items = []
        state = 0
        for ch in inp:
            if state in (0, 2):  # re.split('([^<>]*)', '<body><table><tr><td>')
                if ch == ':':  # switch sides
                    # else_str = re.match('[: ]*', substr).group()
                    # surf_len = len(else_str)
                    # if len(surf_len) > 0: item_surface = else_str
                    # curr += surf_len + 1                if ch == ':':  # switch sides
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
        return out_mode('+'.join(map(self.put_together, danal)).replace(' ', '_')
                        for _, _, danal in self._spec_query(inp))

    def dstem(self, inp, out_mode=lambda x: sorted(set(x))):
        return out_mode((lemma.replace(' ', '_'), tag.replace(' ', '_'),
                         '+'.join(map(self.put_together, danal)).replace(' ', '_'))
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
