#!/usr/bin/python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from flask import Flask, request, abort
from flask_restful import Resource, Api

# Import emMorphPy wrapper
import emmorphpy

import atexit
import threading

from json import dumps
from flask import make_response


def jsonify(status=200, indent=2, sort_keys=True, **kwargs):
    """
    http://stackoverflow.com/a/23320628/7145849
    """
    response = make_response(dumps(dict(**kwargs), indent=indent, sort_keys=sort_keys, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['mimetype'] = 'application/json'
    response.status_code = status
    return response


# lock to control access to variable
emmorphpy_lock = threading.Lock()

# Initiate
emmorphpy_morphology = emmorphpy.EmMorphPy()
atexit.register(emmorphpy_morphology.close)

app = Flask(__name__)
api = Api(app)


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
        with emmorphpy_lock:
            stem = emmorphpy_morphology.stem(token)
        return jsonify(**{token: stem})

    @staticmethod
    @app.route('/dstem/')
    def dstem_usage():
            return 'Usage: /dstem/word'

    @staticmethod
    @app.route('/dstem/<token>')
    def dstem(token):
        with emmorphpy_lock:
            stem = emmorphpy_morphology.dstem(token)
        return jsonify(**{token: stem})

    @staticmethod
    @app.route('/analyze/')
    def analyze_usage():
            return 'Usage: /analyze/word'

    @staticmethod
    @app.route('/analyze/<token>')
    def analyze(token):
        with emmorphpy_lock:
            stem = emmorphpy_morphology.analyze(token)
        return jsonify(**{token: stem})

    @staticmethod
    @app.route('/batch_stem')
    def batch_stem_usage():
            return 'Usage: HTTP POST /batch_stem a JSON dict with "words" as key and the list of words as value'

    @staticmethod
    @app.route('/batch_stem', methods=['POST'])
    def batch_stem():
        if not request.json:
            abort(400)
        data = set(request.get_json()['words'])
        with emmorphpy_lock:
            stems = {token: emmorphpy_morphology.stem(token) for token in data}
        return jsonify(**stems)

    @staticmethod
    @app.route('/batch_dstem')
    def batch_dstem_usage():
            return 'Usage: HTTP POST /batch_dstem a JSON dict with "words" as key and the list of words as value'

    @staticmethod
    @app.route('/batch_dstem', methods=['POST'])
    def batch_dstem():
        if not request.json:
            abort(400)
        data = set(request.get_json()['words'])
        with emmorphpy_lock:
            stems = {token: emmorphpy_morphology.dstem(token) for token in data}
        return jsonify(**stems)

    @staticmethod
    @app.route('/batch_analyze')
    def batch_analyze_usage():
            return 'Usage: HTTP POST /batch_analyze a JSON dict with "words" as key and the list of words as value'

    @staticmethod
    @app.route('/batch_analyze', methods=['POST'])
    def batch_analyze():
        if not request.json:
            abort(400)
        data = set(request.get_json()['words'])
        with emmorphpy_lock:
            stems = {token: emmorphpy_morphology.analyze(token) for token in data}
        return jsonify(**stems)


if __name__ == '__main__':
    app.run(debug=False)
