#!/usr/bin/python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys
import codecs

import atexit

from json import dumps as json_dumps

from flask import Flask, request, Response, stream_with_context, make_response
from flask_restful import Api, Resource
from werkzeug.exceptions import abort


# BEGIN Add personality...

# Import emMorphPy wrapper
import emmorphpy

# Default args
command = '/<path:path>'
args = ()
kwargs = {}
tagger = emmorphpy.EmMorphPy

# END Add personality...


def jsonify(status=200, indent=2, sort_keys=True, **jsonify_kwargs):
    """
    http://stackoverflow.com/a/23320628/7145849
    """
    response = make_response(json_dumps(dict(**jsonify_kwargs), indent=indent, sort_keys=sort_keys, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['mimetype'] = 'application/json'
    response.status_code = status
    return response


prog = tagger(*args, **kwargs)


def add_params(restapi, endpoint, internal_app):
    if internal_app is None:
        print('No internal_app is given!', file=sys.stderr)
        exit(1)

    app_kwargs = {'endpoint': endpoint, 'internal_app': internal_app}
    # To bypass using self and @route together
    restapi.add_resource(RESTapp, *{'/', endpoint}, resource_class_kwargs=app_kwargs)


def create_rest_app(name, endpoint, internal_app):
    flask_app = Flask(name)
    api = Api(flask_app)
    add_params(api, endpoint, internal_app)

    return flask_app


class RESTapp(Resource):
    usage = 'Usage: /stem/word, /analyze/word, /dstem/word with HTTP GET or ' \
            '/batch_stem, /batch_analyze, /batch_dstem with ' \
            'HTTP POST a file mamed as \'file\' in the apropriate TSV format'

    def get(self, path=''):
        token = ''
        if path.startswith('stem/'):
            fun = self.do_stem
            token = path[5:]
        elif path.startswith('analyze/'):
            fun = self.do_analyze
            token = path[8:]
        elif path.startswith('dstem/'):
            token = path[6:]
            fun = self.do_dstem
        else:
            fun = self.do_stem  # Dummy to silence the IDE

        if len(token) == 0:
            abort(400, RESTapp.usage)
            fun = self.do_stem  # Dummy to silence the IDE

        return jsonify(**{token: fun(token)})

    def post(self, path=''):
        if path == 'stem':
            fun = self.do_stem
        elif path == 'analyze':
            fun = self.do_analyze
        elif path == 'dstem':
            fun = self.do_dstem
        else:
            abort(400, RESTapp.usage)
            fun = self.do_stem

        if 'file' not in request.files:
            abort(400)
        inp_file = codecs.getreader('UTF-8')(request.files['file'])

        return Response(stream_with_context((line.encode('UTF-8')
                                             for line in RESTapp.process(inp_file, fun))),
                        direct_passthrough=True)

    @staticmethod
    def process(stream, fun):
        # Simplified version of the TSVHandler process function...
        fields = next(stream).strip().split()
        if fields != ['string']:
            abort(400, 'ERROR: input header missing!')
        fields.extend(['anas'])  # Add target fields
        header = '{0}\n'.format('\t'.join(fields))
        yield header

        for line in stream:
            line = line.strip()
            if len(line) > 0:
                yield '{0}\t{1}'.format(line, json_dumps(fun(line), ensure_ascii=False))
            else:
                yield line
            yield '\n'

    def do_stem(self, token):
        return self._internal_app.stem(token, out_mode=lambda x: [self._internal_app.zip_w_keys(analysis,
                                                                                                ('lemma', 'tag'))
                                                                  for analysis in x])

    def do_analyze(self, token):
        return self._internal_app.analyze(token, out_mode=lambda x: [self._internal_app.zip_w_keys((analysis,),
                                                                                                   ('morphana',))
                                                                     for analysis in x])

    def do_dstem(self, token):
        return self._internal_app.dstem(token,  out_mode=lambda x: [self._internal_app.zip_w_keys(analysis)
                                                                    for analysis in x])

    def __init__(self, endpoint, internal_app=None):
        """
        Init REST API class
        :param endpoint: the command to answer (parse, tag, analyze, etc.)
        :param internal_app: pre-inicialised application
        """
        self._command = endpoint.rsplit('/<path:path>', maxsplit=1)[0]
        self._internal_app = internal_app
        # atexit.register(self._internal_app.__del__)  # For clean exit...


# Create app with the desired parameters...
app = create_rest_app(__name__, endpoint=command, internal_app=prog)

if __name__ == '__main__':
    app.run(debug=False)
