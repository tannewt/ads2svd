#! /bin/bash

if [ $# -eq 0 ]; then
    input="out/Cortex-M*.xml"
else
    input=$1
fi

for x in $input ; do
    echo $x
    saxon -s:$x -xsl:ads2svd.xslt -o:${x%xml}svd ;
done

