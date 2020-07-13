# !/usr/bin/env pyhton3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from xtsv import pipeline_rest_api, singleton_store_factory

em_morph_stem = ('emmorphpy', 'EmMorphPy', 'stem', (),
                 {'task': 'stem', 'source_fields': {'form'}, 'target_fields': ['anas']})
em_morph_analyze = ('emmorphpy', 'EmMorphPy', 'analyze', (),
                    {'task': 'analyze', 'source_fields': {'form'}, 'target_fields': ['anas']})
em_morph_dstem = ('emmorphpy', 'EmMorphPy', 'dstem', (),
                  {'task': 'dstem', 'source_fields': {'form'}, 'target_fields': ['anas']})

tools = [(em_morph_stem, ('stem',)),
         (em_morph_analyze, ('analyze',)),
         (em_morph_dstem, ('dstem',)),
         ]
app = pipeline_rest_api('emMorph', tools, {},  conll_comments=False, singleton_store=singleton_store_factory(),
                        form_title='emMorph demo', form_type='radio',
                        doc_link='https://github.com/dlt-rilmta/emmorphpy')

if __name__ == '__main__':
    app.run(debug=False)
