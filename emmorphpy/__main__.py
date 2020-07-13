#!/usr/bin/env pyhton3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys

from . import EmMorphPy

from xtsv import build_pipeline, parser_skeleton, jnius_config, add_bool_arg


def input_wrapper():  # TODO: Include in xtsv?
    while True:
        try:
            inp_str = input('--> ')
            if len(inp_str) == 0:
                raise EOFError
            yield inp_str
        except EOFError:
            return


def raw_dstem_helper(fh):
    emmorph = EmMorphPy()
    for line in fh:
        line = line.strip()
        for i in emmorph.dstem(line, out_mode=list):
            if len(i) == 5:
                print(line, i[2], i[0], i[1], sep='\t')
            else:
                print(line, '<unknown>', sep='\t')
        print()


def raw_input_processor(inp_stream):
    if inp_stream == sys.stdin:
        print('Type one word per line, Ctrl+D or empty word to exit')
        raw_dstem_helper(input_wrapper())
    else:
        raw_dstem_helper(inp_stream)


def main():
    argparser = parser_skeleton(description='emMorphPy - A wrapper, a lemmatizer and REST API implemented in Python for'
                                            ' emMorph (Humor) Hungarian morphological analyzer')
    add_bool_arg(argparser, 'raw', 'Process tokens raw one token per line (without xtsv) incl. interactive mode')

    opts = argparser.parse_args()

    if opts.raw:
        raw_input_processor(opts.input_stream)
        exit()

    jnius_config.classpath_show_warning = opts.verbose  # Suppress warning.
    conll_comments = opts.conllu_comments

    # Set input and output iterators...
    if opts.input_text is not None:
        input_data = opts.input_text
    else:
        input_data = opts.input_stream
    output_iterator = opts.output_stream

    # Set the tagger name as in the tools dictionary
    used_tools = ['morph']
    presets = []

    # Init and run the module as it were in xtsv

    # The relevant part of config.py
    em_morph = ('emmorphpy', 'EmMorphPy', 'emMorph', (),
                {'source_fields': {'form'}, 'target_fields': ['anas']})
    tools = [(em_morph, ('morph', 'emMorph'))]

    # Run the pipeline on input and write result to the output...
    output_iterator.writelines(build_pipeline(input_data, used_tools, tools, presets, conll_comments))

    # TODO this method is recommended when debugging the tool
    # Alternative: Run specific tool for input (still in emtsv format):
    # output_iterator.writelines(process(input_iterator, inited_tools[used_tools[0]]))

    # Alternative2: Run REST API debug server
    # app = pipeline_rest_api('TEST', inited_tools, presets,  False)
    # app.run()


if __name__ == '__main__':
    main()
