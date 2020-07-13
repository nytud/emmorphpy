#!/bin/bash

# Create tag list
cat ../gold_output.txt | grep -v '^$' | sed 's/^[^[]*//'| sed 's/\]=[^[]*/]/g' | sed 's/\]\[/]\n[/g' > gold.txt
cat gold.txt | wc -l
cat gold.txt | sort | uniq > gold_sorted.txt

# Only in gold (gold vs. config)
cat gold_sorted.txt gold_sorted.txt config_sorted.txt | sort | uniq -c | egrep "^ +2 "
# Only in config (gold vs. config)
cat gold_sorted.txt gold_sorted.txt config_sorted.txt | sort | uniq -c | egrep "^ +1 "
# etc.