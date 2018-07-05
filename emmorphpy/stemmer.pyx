#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-
# cython: language_level=3
# distutils: language = c++

from cython.operator cimport dereference as deref
from libcpp.string cimport string as cpp_string

from libcpp cimport bool as cpp_bool
from libcpp.set cimport set as cpp_set
from libcpp.vector cimport vector as cpp_vector
from libcpp.map cimport map as cpp_map

cdef enum Flags:
    STEM = 0
    PREFIX = 1
    COMP_MEMBER = 2
    COMP_DELIM = 3
    COMP_MUST_HAVE = 4
    COMP_BEFORE_HYPHEN = 5
    STEM_IF_COMP = 6
    INT_PUNCT = 7

FlagsPy = {'STEM': STEM,
           'PREFIX': PREFIX,
           'COMP_MEMBER': COMP_MEMBER,
           'COMP_DELIM': COMP_DELIM,
           'COMP_MUST_HAVE': COMP_MUST_HAVE,
           'COMP_BEFORE_HYPHEN': COMP_BEFORE_HYPHEN,
           'STEM_IF_COMP': STEM_IF_COMP,
           'INT_PUNCT': INT_PUNCT}

ctypedef cpp_set[Flags] flags_set

cdef struct MorphemeInfo:
    cpp_string lexical
    cpp_string surface
    cpp_string category
    cpp_bool is_prefix
    cpp_bool is_stem
    cpp_bool is_derivative
    cpp_bool is_compound_member
    cpp_bool is_compound_delimiter
    flags_set flags
    flags_set flags_conv

cdef MorphemeInfo make_morpheme_info():
    cdef MorphemeInfo morph
    morph.lexical = b''
    morph.surface = b''
    morph.category = b''
    morph.is_prefix = False
    morph.is_stem = False
    morph.is_derivative = False
    morph.is_compound_member = False
    morph.is_compound_delimiter = False
    morph.flags = flags_set()
    morph.flags_conv = flags_set()
    return morph

ctypedef cpp_vector[MorphemeInfo] morpheme_info_list

cdef struct Stem:
    morpheme_info_list morphs
    cpp_string sz_accented_form
    cpp_string sz_stem
    int stem_code
    int compounds
    cpp_bool compound_word
    cpp_bool incorrect_word
    cpp_vector[int] compound_delims


cdef Stem make_stem():
    cdef Stem stem
    stem.morphs = morpheme_info_list()
    stem.sz_accented_form = b''
    stem.sz_stem = b''
    stem.stem_code = -1
    stem.compounds = 0
    stem.compound_word = False
    stem.incorrect_word = False
    stem.compound_delims = cpp_vector[int]()
    return stem

cdef cpp_string get_tags(morpheme_info_list morphs, int stem_code, cpp_bool all_tags):
    cdef cpp_string str_morphs = b''
    cdef MorphemeInfo *m
    for n in range(morphs.size()):
        m = &morphs[n]
        if all_tags or <int>n >= stem_code or m.is_prefix:
            str_morphs.append(b'[')
            str_morphs.append(m.category)
            str_morphs.append(b']')

    return str_morphs


cdef cpp_string copy2surface(cpp_string copy2surface_str, cpp_string in_str, cpp_string out):
    cdef size_t i = 0
    if copy2surface_str.length() > 0:  # else nothing to do :)
        while i < out.length():  # Mutate out in the loop!
            if i >= in_str.length():
                break
            if copy2surface_str.find(in_str.substr(i, 1)) != <size_t>-1:
                out = out.substr(0,i) + in_str.substr(i, 1) + out.substr(i)
            elif in_str[i] != out[i]:
                break
            i += 1

    return out

cdef void convert_case(cpp_string copy2surface_str, size_t hyphen_pos, Stem *stem, cpp_string surface):
    cdef size_t stem_end
    cdef MorphemeInfo *last
    if stem.morphs.size() > 0:
        last = &stem.morphs.back()
        surface = copy2surface(copy2surface_str, last.lexical, surface)  # copy spec cars from lexical

        # if (m_GetCaseFromInput)  // lexical gets case state from surface
        #   CaseConvert(surface, (curr_analysis.morp.end()-1)->lexical/*prev_lexical*/);
        # else
        if stem.compounds > 1 and hyphen_pos != stem.morphs.size() - 2:  # /*curr_analysis.compound_word*/
            # if it is in compound word: lowercase ("WolfGang"=>"Wolfgang")
            last.lexical = last.lexical.lower()  # TODO: NO UTF-8-aware lowercasing using STDLIB exists!

        last.surface = surface

cpdef cpp_vector[cpp_string] stemmer_process(cpp_string cpp_input_str,
                                             cpp_map[cpp_string, flags_set] cpp_tag_config,
                                             cpp_map[cpp_string, cpp_string] cpp_tag_convert,
                                             cpp_map[cpp_string, cpp_string] cpp_tag_replace,
                                             cpp_string cpp_copy2surface_str):

    cdef cpp_map[cpp_string, flags_set].iterator tc
    cdef cpp_map[cpp_string, cpp_string].iterator r

    cdef size_t state = 0

    cdef cpp_bool derivative = False
    cdef int must_have_compounds = 0  # how many morphemes with "compound must have" property
    cdef int last_stem_code = -1  # last stem position
    cdef int prev_last_stem_code = -1  # prev state of last_stem_code
    cdef int hyphen_pos = -1  # position of a hyphen
    cdef cpp_bool look_for_compound = False

    cdef cpp_bool surf_lex_diff = False
    cdef cpp_bool sure_compound = False
    cdef cpp_bool prev_compound = False
    cdef char c_str
    cdef cpp_bool compound_member = False
    cdef cpp_bool convert, tmp_bool, compound
    cdef MorphemeInfo *m

    cdef cpp_string sz_cur_cod = b''
    cdef cpp_string surface = b''  # lexical prev_lexical, prev_surface;

    cdef MorphemeInfo morph = make_morpheme_info()
    cdef Stem stem = make_stem()

    for s in range(cpp_input_str.length()):
        c_str = cpp_input_str[s]  # TODO: This copies every char...
        if state == 0:
            if c_str == b'[':
                state = 1
            elif c_str == b'=':
                state = 2
                surf_lex_diff = True
            elif c_str == b'+':
                surf_lex_diff = False
            # ignoring '+' in lexical form
            else:
                stem.sz_accented_form.push_back(c_str)
                morph.lexical.push_back(c_str)
        elif state == 1:
            compound_member = False
            if c_str == b']':
                morph.flags = cpp_tag_config[sz_cur_cod]

                morph.is_stem = morph.flags.find(STEM) != morph.flags.end()
                it_is_stem = morph.is_stem
                morph.is_compound_member = morph.flags.find(COMP_MEMBER) != morph.flags.end()
                compound_member = morph.is_compound_member

                # conversion
                r = cpp_tag_convert.find(sz_cur_cod)
                morph.is_derivative = r != cpp_tag_convert.end()
                if morph.is_derivative:
                    morph.flags_conv = cpp_tag_config[deref(r).second]
                else:
                    morph.flags_conv = flags_set()

                # tag replacement
                r = cpp_tag_replace.find(sz_cur_cod)
                if r != cpp_tag_replace.end():
                    sz_cur_cod = deref(r).second
                    tc = cpp_tag_config.find(sz_cur_cod)
                    if tc != cpp_tag_config.end():
                        morph.flags = deref(tc).second  # Replace if found else keep

                morph.category = sz_cur_cod
                morph.is_compound_delimiter = morph.flags.find(COMP_DELIM) != morph.flags.end()
                morph.is_prefix = morph.flags.find(PREFIX) != morph.flags.end()

                if surf_lex_diff:
                    morph.surface = surface
                else:
                    morph.surface = morph.lexical

                must_have_compounds += <int>(morph.flags.find(COMP_MUST_HAVE) != morph.flags.end() or
                                             morph.flags_conv.find(COMP_MUST_HAVE) != morph.flags_conv.end())

                stem.morphs.push_back(morph)

                # van-e 2 egymást követő compound member, (ha igen, tuti összetett)
                sure_compound |= prev_compound and compound_member
                prev_compound = compound_member

                # ha volt már tő és ez képző => a konvertáltjait megkeressük, ha compound member, akkor beállítjuk
                tmp_bool = look_for_compound and morph.flags_conv.find(COMP_MEMBER) != morph.flags_conv.end()
                compound_member |= tmp_bool
                morph.is_compound_member |= tmp_bool

                if it_is_stem:
                    if morph.lexical == b'-':
                        hyphen_pos = stem.morphs.size() - 1

                    if stem.stem_code == -1:
                        stem.stem_code = stem.morphs.size() - 1  # save pos...

                    last_stem_code = stem.morphs.size() - 1
                    if prev_last_stem_code != -1 and morph.lexical != b'-':
                        convert = False
                        # Mutate list in loop!
                        for i in range(last_stem_code, prev_last_stem_code - 1, -1):
                            m = &stem.morphs[i]
                            convert = convert or m.is_stem
                            if convert and m.is_derivative:
                                r = cpp_tag_convert.find(m.category)
                                if r != cpp_tag_convert.end():
                                    m.category = deref(r).second  # TODO: A None itt nincs kezelve
                                m.flags = m.flags_conv
                                m.is_stem = m.is_stem or morph.flags.find(STEM) != morph.flags.end()

                    prev_last_stem_code = last_stem_code
                    # első tőalkotó után bekapcsoljuk, ha ez True, akkor keresünk olyan képzőt,
                    #  ami compound membert csinál belőle
                    look_for_compound |= not derivative

                # ha cmember => növelem
                # ha tő ÉS jön egy compoundMember kepző => növelem
                if compound_member:
                    stem.compounds += 1
                    look_for_compound = False

                morph = make_morpheme_info()
                sz_cur_cod = b''
                state = 2
            elif c_str == b'`':
                # 6-3-as szabály miatt (2011.07.18. NA: "Azt kéne csinálni, hogy a morfológia által
                #  visszaadott cimkék elején lévő részt a `-ig ki kell törölni mielőtt bármi mást csinálnál")
                sz_cur_cod = b''
            else:
                sz_cur_cod += c_str

        elif state == 2:
            if c_str == b'+':
                state = 0
            # iLastPlusPos = curr_analysis.sz_accented_form.length();
            elif c_str == b'=':
                state = 3

        elif state == 3:
            # surface form is arriving, it may replace stem
            if c_str == b'+':
                state = 0
                convert_case(cpp_copy2surface_str, hyphen_pos, &stem, surface)
                surface = b''
            else:
                surface += c_str

    if surface.length() > 0:  # surface form és nincs utána semmi
        convert_case(cpp_copy2surface_str, hyphen_pos, &stem, surface)

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
    cdef size_t k
    if sure_compound:  # curr_analysis.compounds > 1){
        # ez biztos összetett szó, mert 2 egymast követő compundmember van benne
        # ha nincs benne FN, de képzett főnév igen, azt megmenti
        # look for stem if compounds
        for k in range(stem.morphs.size()):
            m = &stem.morphs[k]  # Mutate list in loop!
            if m.flags.find(STEM_IF_COMP) != m.flags.end():
                m.is_stem = True
                r = cpp_tag_convert.find(m.category)
                if r != cpp_tag_convert.end():
                    m.category = deref(r).second  # TODO: A None itt nincs kezelve
                m.flags = m.flags_conv
                stem.stem_code = k
                if <int>k >= last_stem_code:
                    last_stem_code = k

    compound = stem.compounds > 1 and hyphen_pos == -1 or must_have_compounds > 0
    if hyphen_pos > 0 and compound:
        # kötőjeles akkor lehet összetett szó, ha a kötőjel előtt [compound before hyphen] all
        # "aa[FN][NOM]-bb[FN][NOM]" vagy "aa[FN]-bb[FN]"
        # pl "Árpad-ház"

        m = &stem.morphs[hyphen_pos - 1]
        # ha a kotojel elotti ures es az azt megelozo toalkoto =>
        # ha a kotojel elott rag van, akkor ez nem osszetett szo

        # TODO: Simplify bool expression...
        if m.flags.find(COMP_BEFORE_HYPHEN) == m.flags.end() or (hyphen_pos > 1 and m.lexical.length() == 0 and
                                                                 m.surface.length() == 0 and
                                                                 not stem.morphs[hyphen_pos - 2].is_stem):
            compound = False

    stem.compound_word = compound

    internal_punct = False

    cdef size_t n
    # most megmentjuk attol, hogy a PUNCT, PER vegu szavak to tipusa PUNCT legyen
    for n in range(stem.morphs.size()-1, 0, -1):
        m = &stem.morphs[n]  # Mutate list in loop!
        if m.flags.find(INT_PUNCT) == m.flags.end():
            break
        internal_punct = True
        m.is_stem = False

    while last_stem_code > 0 and not stem.morphs[last_stem_code].is_stem:
        last_stem_code -= 1

    if compound and not sure_compound:
        # összetett szavaknál a stemIfCompoundokat átalakítja
        for k in range(stem.morphs.size()):
            m = &stem.morphs[k]  # Mutate list in loop!
            if m.flags.find(INT_PUNCT) != m.flags.end():
                m.is_stem = True
                r = cpp_tag_convert.find(m.category)
                if r != cpp_tag_convert.end():
                    m.category = deref(r).second  # TODO: A None itt nincs kezelve
                m.flags = m.flags_conv
                if <int>k >= last_stem_code:
                    last_stem_code = k

    # összetett szavaknál beteszi a + jelet...
    cdef int coffset = 0
    for mo in stem.morphs:
        if mo.is_compound_member or mo.is_compound_delimiter:
            if coffset != 0:
                stem.compound_delims.push_back(coffset)  # az utolsó nem kell: ott már vége a szónak
            coffset += mo.surface.length()

    cdef cpp_bool internal_punct_and = True
    if internal_punct and hyphen_pos > 0:
        # végén van egy kötőjel, ha előtte ragozoztt szó áll, nem lehet szoösszetétel
        # pl. "magán-"
        m = &stem.morphs[hyphen_pos - 1]
        # ha a kötőjel előtti üres és az azt megelőző tőalkotó =>
        # hadd éljen, nem megy bele az ikerszó ágba
        # ez már ikerszó nem lehet
        # TODO: Simplify bool expression...
        if m.flags.find(COMP_BEFORE_HYPHEN) != m.flags.end() and not (hyphen_pos > 1 and m.lexical.length() == 0
                                                                      and m.surface.length() == 0
                                                                      and not stem.morphs[hyphen_pos - 2].is_stem):
            internal_punct_and = False

    # beleégetjük hogy a szóközi kötőjel stem
    for n in range(1, stem.morphs.size()-1):
        m = &stem.morphs[n]
        m.is_stem = m.is_stem or (stem.morphs[n-1].is_stem and stem.morphs[n + 1].is_stem and \
                     (m.surface == b'-' or m.lexical == b'-'))

    cdef cpp_string tmp1 = b''
    cdef cpp_string tmp2 = b''
    cdef int l
    if internal_punct_and and hyphen_pos != -1 and not compound:
        # ikerszo

        half = False
        half_pos = stem.stem_code  # hyphen_pos;//last_stem_code;//;
        for z in range(max(hyphen_pos - 1, 0), 0, -1):
            if stem.morphs[z].is_stem:
                half_pos = z
                break

        tmp1 = b''
        tmp2 = b''
        for n in range(stem.morphs.size()):
            m = &stem.morphs[n]
            if m.lexical == b'-':
                half = True
                half_pos = last_stem_code

            if m.is_stem:
                if <int>n < half_pos and m.surface.length() != 0:
                    stem.sz_stem += m.surface
                else:
                    stem.sz_stem += m.lexical
            else:
                if not half:
                    tmp1.append(m.category)
                    tmp1.append(b' ')
                else:
                    tmp2.append(m.category)
                    tmp2.append(b' ')

        if tmp1 != tmp2:
            # BAD input, stem is dropped
            stem.incorrect_word = True
            stem.sz_stem.append(b'<incorrect word>')
            # return 0;

    else:
        # simple case

        if <int>stem.morphs.size() >= last_stem_code:
            for l in range(last_stem_code + 1):
                if stem.morphs[l].is_stem:
                    if l < last_stem_code:
                        stem.sz_stem += stem.morphs[l].surface
                    elif l == last_stem_code:  # /*curr_analysis.stem_code*/
                        stem.sz_stem += stem.morphs[l].lexical

    stem.stem_code = last_stem_code

    """
    //          if (m_regexp_stem_decision)
    //          {
    //              //call regular function
    //              SelectStem(curr_analysis);
    //          }
    """
    cdef cpp_vector[cpp_string] ret
    # print("STEM_OUTPUT:", stem)
    if not stem.incorrect_word:
        ret.push_back(stem.sz_stem)
        ret.push_back(get_tags(stem.morphs, stem.stem_code, False))

    return ret
