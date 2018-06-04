#!/bin/bash

time (python3 test.py > test/python_output.txt)

diff -sy --suppress-common-lines test/python_output.txt test/gold_output.txt
