#!/usr/bin/python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import codecs

from flask import Flask, request, abort, Response, stream_with_context
from flask_restful import Resource, Api

# Import emMorphPy wrapper
import emmorphpy

import atexit

from json import dumps as json_dumps
from flask import make_response


def jsonify(status=200, indent=2, sort_keys=True, **kwargs):
    """
    http://stackoverflow.com/a/23320628/7145849
    """
    response = make_response(json_dumps(dict(**kwargs), indent=indent, sort_keys=sort_keys, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['mimetype'] = 'application/json'
    response.status_code = status
    return response


# Initiate
emmorphpy_morphology = emmorphpy.EmMorphPy()
atexit.register(emmorphpy_morphology.close)

app = Flask(__name__)
api = Api(app)


# TODO: Reimplement this in dynamically loadable morphology-style like in e-magyar-tsv
class EmMorphPyREST(Resource):
    @staticmethod
    @app.route('/')
    def usage():
            return 'Usage: /stem/word, /analyze/word, /dstem/word, /batch_stem, /batch_analyze or /batch_dstem'

    @staticmethod
    @app.route('/stem/')
    def stem_usage():
            return 'Usage: /stem/word'

    @staticmethod
    @app.route('/stem/<token>')
    def stem(token):
        stem = EmMorphPyREST.do_stem(token)
        return jsonify(**{token: stem})

    @staticmethod
    def do_stem(token):
        return emmorphpy_morphology.stem(token, out_mode=lambda x: [emmorphpy_morphology.zip_w_keys(analysis,
                                                                                                    ('lemma', 'tag'))
                                                                    for analysis in x])

    @staticmethod
    @app.route('/dstem/')
    def dstem_usage():
            return 'Usage: /dstem/word'

    @staticmethod
    @app.route('/dstem/<token>')
    def dstem(token):
        stem = EmMorphPyREST.do_dstem(token)
        return jsonify(**{token: stem})

    @staticmethod
    def do_dstem(token):
        return emmorphpy_morphology.dstem(token,  out_mode=lambda x: [emmorphpy_morphology.zip_w_keys(analysis)
                                                                      for analysis in x])

    @staticmethod
    @app.route('/analyze/')
    def analyze_usage():
            return 'Usage: /analyze/word'

    @staticmethod
    @app.route('/analyze/<token>')
    def analyze(token):
        stem = EmMorphPyREST.do_analyze(token)
        return jsonify(**{token: stem})

    @staticmethod
    def do_analyze(token):
        return emmorphpy_morphology.analyze(token, out_mode=lambda x: [emmorphpy_morphology.zip_w_keys((analysis,),
                                                                                                       ('morphana',))
                                                                       for analysis in x])

    @staticmethod
    @app.route('/batch_stem')
    def batch_stem_usage():
            return 'Usage: HTTP POST /batch_stem a JSON dict with "words" as key and the list of words as value'

    @staticmethod
    @app.route('/batch_stem', methods=['POST'])
    def batch_stem():
        if 'file' not in request.files:
            abort(400, 'ERROR: input file not found in request!')
        inp_file = codecs.getreader('UTF-8')(request.files['file'])

        return Response(stream_with_context((line.encode('UTF-8')
                                             for line in EmMorphPyREST.process(inp_file, EmMorphPyREST.do_stem))),
                        direct_passthrough=True)

    @staticmethod
    @app.route('/batch_dstem')
    def batch_dstem_usage():
            return 'Usage: HTTP POST /batch_dstem a JSON dict with "words" as key and the list of words as value'

    @staticmethod
    @app.route('/batch_dstem', methods=['POST'])
    def batch_dstem():
        if 'file' not in request.files:
            abort(400, 'ERROR: input file not found in request!')
        inp_file = codecs.getreader('UTF-8')(request.files['file'])

        return Response(stream_with_context((line.encode('UTF-8')
                                             for line in EmMorphPyREST.process(inp_file, EmMorphPyREST.do_dstem))),
                        direct_passthrough=True)

    @staticmethod
    @app.route('/batch_analyze')
    def batch_analyze_usage():
            return 'Usage: HTTP POST /batch_analyze a JSON dict with "words" as key and the list of words as value'

    @staticmethod
    @app.route('/batch_analyze', methods=['POST'])
    def batch_analyze():
        if 'file' not in request.files:
            abort(400, 'ERROR: input file not found in request!')
        inp_file = codecs.getreader('UTF-8')(request.files['file'])

        return Response(stream_with_context((line.encode('UTF-8')
                                             for line in EmMorphPyREST.process(inp_file, EmMorphPyREST.do_analyze))),
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


if __name__ == '__main__':
    app.run(debug=False)
