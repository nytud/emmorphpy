#!/usr/bin/python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import codecs

# import atexit

from json import dumps as json_dumps

from flask import Flask, request, Response, stream_with_context, make_response
from flask_restful import Api, Resource
from werkzeug.exceptions import abort


# BEGIN Add personality...

# Import emMorphPy wrapper
import emmorphpy

# Default args
tagger_args = ()
tagger_kwargs = {'source_fields': {'form'}, 'target_fields': ['anas']}
tagger = emmorphpy.EmMorphPy

# END Add personality...

prog = tagger(*tagger_args, **tagger_kwargs)


def make_json_response(json_text, status=200):
    """https://stackoverflow.com/questions/16908943/display-json-returned-from-flask-in-a-neat-way/23320628#23320628 """
    response = make_response(json_text)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['mimetype'] = 'application/json'
    response.status_code = status
    return response


def add_params(restapi, resource_class, internal_apps, presets, conll_comments):
    if internal_apps is None:
        raise ValueError('No internal_app is given!')

    kwargs = {'internal_apps': internal_apps, 'presets': presets, 'conll_comments': conll_comments}
    # To bypass using self and @route together, default values are at the function declarations
    restapi.add_resource(resource_class, '/', '/<path:path>', resource_class_kwargs=kwargs)


class RESTapp(Resource):
    def get(self, path=''):
        # fun/token
        fun = None
        token = ''
        if '/' in path:
            fun, token = path.split('/', maxsplit=1)
            fun = self._keywords.get(fun)

        if len(path) == 0 or len(token) == 0 or fun is None:
            abort(400, 'Usage: /stem/word, /analyze/word, /dstem/word with HTTP GET or '
                       '/stem, /analyze, /dstem with HTTP POST a file mamed as \'file\' '
                       'in the apropriate TSV format. '
                       'Further info: https://github.com/ppke-nlpg/emmorphpy')

        json_text = json_dumps({token: fun(token)}, indent=2, sort_keys=True, ensure_ascii=False)  # TODO THIS!

        return make_json_response(json_text)

    def post(self, path):  # TODO: USE THE xtsv variant!
        conll_comments = request.form.get('conll_comments', self._conll_comments)
        fun = None
        for keyword, key_fun in self._keywords.items():
            if path == keyword:
                fun = key_fun
                break

        if 'file' not in request.files or fun is None:
            abort(400, 'ERROR: input file not found in request!')

        inp_file = codecs.getreader('UTF-8')(request.files['file'])
        last_prog = self.process(inp_file, fun)

        return Response(stream_with_context((line.encode('UTF-8') for line in last_prog)),
                        direct_passthrough=True)

    def process(self, stream, fun):  # TODO: Remove this!
        # Simplified version of the TSVHandler process function...
        source_fields = self._internal_apps.source_fields
        target_fields = self._internal_apps.target_fields

        fields = next(stream).strip().split('\t')  # Read header to fields

        # process_header START
        if not source_fields.issubset(set(fields)):
            abort(400, 'ERROR: input header missing!')
        fields.extend(target_fields)  # Add target fields
        header = '{0}\n'.format('\t'.join(fields))
        # process_header END
        yield header

        for line in stream:
            line = line.strip()
            if len(line) > 0:
                yield '{0}\t{1}'.format(line, json_dumps(fun(line), ensure_ascii=False))
            else:
                yield line
            yield '\n'

    # TODO: These three functions has moved into EmMorphPy
    def do_stem(self, token):
        return self._internal_apps.stem(token, out_mode=lambda x: [self._internal_apps.zip_w_keys(analysis,
                                                                                                  ('lemma', 'tag'))
                                                                   for analysis in x])

    def do_analyze(self, token):
        return self._internal_apps.analyze(token, out_mode=lambda x: [self._internal_apps.zip_w_keys((analysis,),
                                                                                                     ('morphana',))
                                                                      for analysis in x])

    def do_dstem(self, token):
        return self._internal_apps.dstem(token, out_mode=lambda x: [self._internal_apps.zip_w_keys(analysis)
                                                                    for analysis in x])

    def __init__(self, internal_apps=None, presets=(), conll_comments=False):
        """
        Init REST API class
        :param internal_apps: pre-inicialised applications
        :param presets: pre-defined chains eg. from tokenisation to dependency parsing'
        :param conll_comments: CoNLL-U-style comments (lines beginning with '#') before sentences
        """
        self._internal_apps = internal_apps
        self._presets = presets
        self._conll_comments = conll_comments
        self._keywords = {'stem': self.do_stem, 'analyze': self.do_analyze, 'dstem': self.do_dstem}  # TODO Remove this!
        # atexit.register(self._internal_apps.__del__)  # For clean exit...


def pipeline_rest_api(name, available_tools, presets, conll_comments):
    app = Flask(name)
    api = Api(app)
    add_params(api, RESTapp, available_tools, presets, conll_comments)

    return app


# Create app with the desired parameters...
flask_app = pipeline_rest_api(__name__, available_tools=prog, presets={}, conll_comments=False)

if __name__ == '__main__':
    flask_app.run(debug=False)
