cat ../test/gold_output.txt | grep -v '^$' | sed 's/^[^[]*//'| sed 's/\]=[^[]*/]/g' | sed 's/\]\[/]\n[/g' > gold.txt
cat gold.txt | wc -l
cat gold.txt | sort | uniq > gold_sorted.txt


