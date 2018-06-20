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
        self.is_prefix = False
        self.is_stem = False
        self.is_derivative = False
        self.is_compound_member = False
        self.is_compound_delimiter = False
        self.flags = set()
        self.flags_conv = set()

    def __str__(self):
        return "lexical: {0} |surface: {1} |category: {2} |is_prefix: {3} |is_stem: {4} |is_derivative: {5} " \
               "|is_compound_member: {6} |is_compound_delimiter: |flags: {7} |flags_conv: {8}".format(
                self.lexical, self.surface, self.category, self.is_prefix, self.is_stem, self.is_derivative,
                self.is_compound_member, self.is_compound_delimiter, self.flags, self.flags_conv)


class Stem:

    def __init__(self):
        self.morphs = []
        self.sz_accented_form = ''
        self.sz_stem = ''
        self.stem_code = -1
        self.compounds = 0
        self.compound_word = False
        self.incorrect_word = False
        self.compound_delims = []

    def __str__(self):
        return "morphs: {0} \n |sz_accented_form: {1} |sz_stem: {2} |stem_code: {3} |compounds: {4} " \
               "|compound_word: {5} |incorrect_word: {6} |compound_delims: {7}".format(
                str([str(m) for m in self.morphs]), self.sz_accented_form, self.sz_stem, self.stem_code, self.compounds,
                self.compound_word, self.incorrect_word, self.compound_delims)

    def get_tags(self, all_tags):
        return ''.join('[{0}]'.format(m.category) for n, m in enumerate(self.morphs)
                       if all_tags or n >= self.stem_code or m.is_prefix)


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
        self.exceptions = {}

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

        copy2surface_str = props.get('stemmer.copy2surface', '')

        hfst_params = props.get('analyzer.params', '').split()
        if len(hfst_params) > 0:
            hfst_params = hfst_params[:-1]  # Cut the FSA

        return item_sep, value_sep, tag_config, tag_convert, tag_replace, unwanted_patterns, copy2surface_str,\
            hfst_params

    @staticmethod
    def _copy2surface(copy2surface_str, in_str, out):
        if len(copy2surface_str) > 0:  # else nothing to do :)
            i = 0
            while i < len(out):  # Mutate out in the loop!
                if i >= len(in_str):
                    break
                if copy2surface_str.find(in_str[i]) != -1:
                    out = out[0:i] + in_str[i] + out[i:]
                elif in_str[i] != out[i]:
                    break
                i += 1

        return out

    def _convert_case(self, copy2surface_str, hyphen_pos, stem, surface):
        if len(stem.morphs) > 0:
            last = stem.morphs[-1]
            surface = self._copy2surface(copy2surface_str, last.lexical, surface)  # copy spec cars from lexical

            # if (m_GetCaseFromInput)  // lexical gets case state from surface
            #   CaseConvert(surface, (curr_analysis.morp.end()-1)->lexical/*prev_lexical*/);
            # else
            if stem.compounds > 1 and hyphen_pos != len(stem.morphs) - 2:  # /*curr_analysis.compound_word*/
                # if it is in compound word: lowercase ("WolfGang"=>"Wolfgang")
                last.lexical = last.lexical.lower()

            last.surface = surface

    def _stemmer_process(self, input_str, conf):
        item_sep, value_sep, tag_config, tag_convert, tag_replace, unwanted_patterns, copy2surface_str, _ = conf

        state = 0

        derivative = False
        must_have_compounds = 0  # how many morphemes with "compound must have" property
        last_stem_code = -1     # last stem position
        prev_last_stem_code = -1  # prev state of last_stem_code
        hyphen_pos = -1         # position of a hyphen
        look_for_compound = False

        surf_lex_diff = False
        sure_compound = False
        prev_compound = False

        sz_cur_cod = ''
        surface = ''  # lexical prev_lexical, prev_surface;

        morph = MorphemeInfo()
        stem = Stem()

        for c in input_str:
            if state == 0:
                if c == '[':
                    state = 1
                elif c == '=':
                    state = 2
                    surf_lex_diff = True
                elif c == '+':
                    surf_lex_diff = False
                # ignoring '+' in lexical form
                else:
                    stem.sz_accented_form += c
                    morph.lexical += c
            elif state == 1:
                if c == ']':
                    morph.flags = tag_config[sz_cur_cod]

                    morph.is_stem = Flags.STEM in morph.flags
                    it_is_stem = morph.is_stem
                    morph.is_compound_member = Flags.COMP_MEMBER in morph.flags
                    compound_member = morph.is_compound_member

                    # conversion
                    tagc = tag_convert.get(sz_cur_cod)
                    morph.is_derivative = tagc is not None
                    if morph.is_derivative:
                        morph.flags_conv = tag_config[tagc]
                    else:
                        morph.flags_conv = set()

                    # tag replacement
                    r = tag_replace.get(sz_cur_cod)
                    if r is not None:
                        sz_cur_cod = r
                        morph.flags = tag_config.get(sz_cur_cod, morph.flags)  # Replace if found else keep

                    morph.category = sz_cur_cod
                    morph.is_compound_delimiter = Flags.COMP_DELIM in morph.flags
                    morph.is_prefix = Flags.PREFIX in morph.flags

                    if surf_lex_diff:
                        morph.surface = surface
                    else:
                        morph.surface = morph.lexical

                    must_have_compounds += int(Flags.COMP_MUST_HAVE in morph.flags or
                                               (morph.flags_conv is not None and
                                                Flags.COMP_MUST_HAVE in morph.flags_conv))

                    stem.morphs.append(morph)

                    # van-e 2 egymást követő compound member, (ha igen, tuti összetett)
                    sure_compound |= prev_compound and compound_member
                    prev_compound = compound_member

                    # ha volt már tő és ez képző => a konvertáltjait megkeressük, ha compound member, akkor beállítjuk
                    tmp_bool = look_for_compound and morph.flags_conv is not None and \
                        Flags.COMP_MEMBER in morph.flags_conv
                    compound_member |= tmp_bool
                    morph.is_compound_member |= tmp_bool

                    if it_is_stem:
                        if morph.lexical == '-':
                            hyphen_pos = len(stem.morphs) - 1

                        if stem.stem_code == -1:
                            stem.stem_code = len(stem.morphs) - 1  # save pos...

                        last_stem_code = len(stem.morphs) - 1
                        if prev_last_stem_code != -1 and morph.lexical != '-':
                            convert = False
                            # Mutate list in loop!
                            for i in range(last_stem_code, prev_last_stem_code - 1, -1):
                                m = stem.morphs[i]
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
                        stem.compounds += 1
                        look_for_compound = False

                    morph = MorphemeInfo()
                    sz_cur_cod = ''
                    state = 2
                elif c == '`':
                    # 6-3-as szabály miatt (2011.07.18. NA: "Azt kéne csinálni, hogy a morfológia által
                    #  visszaadott cimkék elején lévő részt a `-ig ki kell törölni mielőtt bármi mást csinálnál")
                    sz_cur_cod = ''
                else:
                    sz_cur_cod += c

            elif state == 2:
                if c == '+':
                    state = 0
                # iLastPlusPos = curr_analysis.sz_accented_form.length();
                elif c == '=':
                    state = 3

            elif state == 3:
                # surface form is arriving, it may replace stem
                if c == '+':
                    state = 0
                    self._convert_case(copy2surface_str, hyphen_pos, stem, surface)
                    surface = ''
                else:
                    surface += c

            elif state == 5:
                break

        if len(surface) > 0:  # surface form és nincs utána semmi
            self._convert_case(copy2surface_str, hyphen_pos, stem, surface)

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
            for n, m in enumerate(stem.morphs):
                m = stem.morphs[n]  # Mutate list in loop!
                if Flags.STEM_IF_COMP in m.flags:
                    m.is_stem = True
                    m.category = tag_convert[m.category]  # TODO: A None itt nincs kezelve
                    m.flags = m.flags_conv
                    stem.stem_code = n
                    if n >= last_stem_code:
                        last_stem_code = n

        compound = stem.compounds > 1 and hyphen_pos == -1 or must_have_compounds > 0
        if hyphen_pos > 0 and compound:
            # kötőjeles akkor lehet összetett szó, ha a kötőjel előtt [compound before hyphen] all
            # "aa[FN][NOM]-bb[FN][NOM]" vagy "aa[FN]-bb[FN]"
            # pl "Árpad-ház"

            m = stem.morphs[hyphen_pos - 1]
            # ha a kotojel elotti ures es az azt megelozo toalkoto =>
            # ha a kotojel elott rag van, akkor ez nem osszetett szo

            # TODO: Simplify bool expression...
            if Flags.COMP_BEFORE_HYPHEN not in m.flags or (hyphen_pos > 1 and len(m.lexical) == 0 and
                                                           len(m.surface) == 0 and
                                                           not stem.morphs[hyphen_pos - 2].is_stem):
                    compound = False

        stem.compound_word = compound

        internal_punct = False
        # most megmentjuk attol, hogy a PUNCT, PER vegu szavak to tipusa PUNCT legyen
        for n, m in enumerate(reversed(stem.morphs), start=1):
            m = stem.morphs[-1*n]  # Mutate list in loop!
            if Flags.INT_PUNCT not in m.flags:
                break
            internal_punct = True
            m.is_stem = False

        while last_stem_code > 0 and not stem.morphs[last_stem_code].is_stem:
            last_stem_code -= 1

        if compound and not sure_compound:
            # összetett szavaknál a stemIfCompoundokat átalakítja
            for n, m in enumerate(stem.morphs):
                m = stem.morphs[n]  # Mutate list in loop!
                if Flags.STEM_IF_COMP in m.flags:
                    m.is_stem = True
                    m.category = tag_convert[m.category]  # TODO: A None itt nincs kezelve
                    m.flags = m.flags_conv
                    if n >= last_stem_code:
                        last_stem_code = n

        # összetett szavaknál beteszi a + jelet...
        coffset = 0
        for m in stem.morphs:
            if m.is_compound_member or m.is_compound_delimiter:
                if coffset != 0:
                    stem.compound_delims.append(coffset)  # az utolsó nem kell: ott már vége a szónak
                coffset += len(m.surface)

        internal_punct_and = True
        if internal_punct and hyphen_pos > 0:
            # végén van egy kötőjel, ha előtte ragozoztt szó áll, nem lehet szoösszetétel
            # pl. "magán-"
            m = stem.morphs[hyphen_pos - 1]
            # ha a kötőjel előtti üres és az azt megelőző tőalkotó =>
            # hadd éljen, nem megy bele az ikerszó ágba
            # ez már ikerszó nem lehet
            # TODO: Simplify bool expression...
            if Flags.COMP_BEFORE_HYPHEN in m.flags and not (hyphen_pos > 1 and len(m.lexical) == 0
                                                            and len(m.surface) == 0
                                                            and not stem.morphs[hyphen_pos - 2].is_stem):
                internal_punct_and = False

        # beleégetjük hogy a szóközi kötőjel stem
        for n, m in enumerate(stem.morphs[1:-1], start=1):
            m = stem.morphs[n]
            m.is_stem |= stem.morphs[n - 1].is_stem and stem.morphs[n + 1].is_stem and \
                (m.surface == '-' or m.lexical == '-')

        if internal_punct_and and hyphen_pos != -1 and not compound:
            # ikerszo

            half = False
            half_pos = stem.stem_code  # hyphen_pos;//last_stem_code;//;
            for z in range(max(hyphen_pos - 1, 0), 0, -1):
                if stem.morphs[z].is_stem:
                    half_pos = z
                    break

            tmp1 = ''
            tmp2 = ''
            for n, m in enumerate(stem.morphs):
                if m.lexical == '-':
                    half = True
                    half_pos = last_stem_code

                if m.is_stem:
                    if n < half_pos and len(m.surface) != 0:
                            stem.sz_stem += m.surface
                    else:
                        stem.sz_stem += m.lexical
                else:
                    if not half:
                        tmp1 += m.category + ' '
                    else:
                        tmp2 += m.category + ' '

            if tmp1 != tmp2:
                # BAD input, stem is dropped
                stem.incorrect_word = True
                stem.sz_stem += '<incorrect word>'
                # return 0;

        else:
            # simple case

            if len(stem.morphs) >= last_stem_code:
                for n in range(last_stem_code+1):
                    if stem.morphs[n].is_stem:
                        if n < last_stem_code:
                            stem.sz_stem += stem.morphs[n].surface
                        elif n == last_stem_code:  # /*curr_analysis.stem_code*/
                            stem.sz_stem += stem.morphs[n].lexical

        stem.stem_code = last_stem_code

        """
        //          if (m_regexp_stem_decision)
        //          {
        //              //call regular function
        //              SelectStem(curr_analysis);
        //          }
        """
        # print("STEM_OUTPUT:", stem)
        if stem.incorrect_word:
            return ()
        else:
            return stem.sz_stem, stem.get_tags(False)

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
                stem = self._stemmer_process(danal, self.loaded_conf)
                if len(stem) > 0:  # Suppress incorrect words
                    output.append((inp, danal, stem))

        # Add extra anals
        output.extend(self.lexicon.get(inp, []))

        # Remove exceptional anals
        to_delete = self.exceptions.get(inp)
        if to_delete is not None:
            output = [anal for anal in output if anal not in to_delete]

        return output

    def stem(self, inp, out_mode=sorted):
        return out_mode(list(elem[2]) for elem in self._spec_query(inp))

    def analyze(self, inp, out_mode=sorted):
        return out_mode(elem[1] for elem in self._spec_query(inp))

    def dstem(self, inp, out_mode=sorted):
        return out_mode(list(elem[2]) + [elem[1]] for elem in self._spec_query(inp))

    def test(self):
        hfst_out_test = 'a:a l:l :o m:m :[/N] á:a :[Poss.3Sg] v:v a:a l:l :[Ins]'
        danal_test = 'alom[/N]=alm+a[Poss.3Sg]=á+val[Ins]=val'
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
