#!/usr/bin/python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from flask import Flask
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
            return 'Usage: /stem/word, /analyze/word or /dstem/word'

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


if __name__ == '__main__':
    app.run(debug=False)
