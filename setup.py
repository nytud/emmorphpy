#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

from distutils.core import setup
from setuptools.command.build_ext import build_ext
from Cython.Build import cythonize


class BuildExt(build_ext):
    def build_extensions(self):
        self.compiler.compiler_so.remove('-Wstrict-prototypes')
        super(BuildExt, self).build_extensions()


setup(
    cmdclass={'build_ext': BuildExt},
    ext_modules=cythonize("emmorphpy/stemmer.pyx", annotate=True)
)
