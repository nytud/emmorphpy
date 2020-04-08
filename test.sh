#!/bin/bash

time (python3 -m emmorphpy --raw -i test/test_words.txt > test/python_output.txt)

diff -sy --suppress-common-lines test/python_output.txt test/gold_output.txt
