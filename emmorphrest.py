#!/usr/bin/python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from xtsv import pipeline_rest_api, singleton_store_factory
from emmorphpy.emmorphpy import EmMorphPy

em_morph_stem = (EmMorphPy, (), {'task': 'stem', 'source_fields': {'form'}, 'target_fields': ['anas']})
em_morph_dstem = (EmMorphPy, (), {'task': 'dstem', 'source_fields': {'form'}, 'target_fields': ['anas']})
em_morph_analyze = (EmMorphPy, (), {'task': 'analyze', 'source_fields': {'form'}, 'target_fields': ['anas']})

tools = {'stem': em_morph_stem, 'dstem': em_morph_dstem, 'analyze': em_morph_analyze}

app = pipeline_rest_api('emMorph', tools, {},  conll_comments=False, singleton_store=singleton_store_factory())

if __name__ == '__main__':
    app.run(debug=False)
