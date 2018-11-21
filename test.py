#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import emmorphpy

emmorph = emmorphpy.EmMorphPy()

for l in open('test/test_words.txt'):
    for i in emmorph.dstem(l.strip(), out_mode=list):
        if len(i) == 5:
            print(l.strip(), i[2], i[0], i[1], sep='\t')
        else:
            print(l.strip(), '<unknown>', sep='\t')
    print()
