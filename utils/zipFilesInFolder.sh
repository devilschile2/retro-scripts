#!/bin/bash
#find . -type f -exec zip -D '$1/{}.zip' '{}' \; 


# Find all files in the folder and its subdirectories and zip each one into its own ZIP file

find . -type f -exec sh -c 'zip -j "$0.zip" "$0"' {} \;