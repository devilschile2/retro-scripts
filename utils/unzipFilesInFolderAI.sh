#!/bin/bash

function unzip_all_files {
    for file in "$1"/*; do
        if [[ -d "$file" ]]; then
            unzip_all_files "$file"
        elif [[ "$file" == *.zip ]]; then
            unzip -o "$file" -d "${file%.*}"
            rm "$file"
        fi
    done
}

if [ -z "$1" ]; then
    echo "Usage: $0 directory"
    exit 1
fi

if [ ! -d "$1" ]; then
    echo "$1 is not a directory"
    exit 1
fi

unzip_all_files "$1"
