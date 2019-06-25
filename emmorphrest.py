#!/usr/bin/python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from xtsv import init_everything, pipeline_rest_api
from emmorphpy.emmorphpy import EmMorphPy

em_morph_stem = (EmMorphPy, (), {'task': 'stem', 'source_fields': {'form'}, 'target_fields': ['anas']})
em_morph_dstem = (EmMorphPy, (), {'task': 'dstem', 'source_fields': {'form'}, 'target_fields': ['anas']})
em_morph_analyze = (EmMorphPy, (), {'task': 'analyze', 'source_fields': {'form'}, 'target_fields': ['anas']})


tools = {'stem': em_morph_stem, 'dstem': em_morph_dstem, 'analyze': em_morph_analyze}

inited_tools = init_everything({k: v for k, v in tools.items()})

app = pipeline_rest_api('emMorph', inited_tools, {},  False)

if __name__ == '__main__':
    app.run(debug=False)
