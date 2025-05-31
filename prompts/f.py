#!/usr/bin/env python3
import sys
import re

def is_list_item(line):
    """Check if line is a markdown list item (starts with -, +, or *)"""
    stripped = line.lstrip()
    return stripped.startswith(('-', '+', '*'))

def process_line(line):
    """Process a single line according to the formatting rules"""
    # Check if line contains # character
    if '#' in line:
        # Find the first # character
        hash_pos = line.find('#')
        if hash_pos > 0:
            # Split before the first #
            before_hash = line[:hash_pos].rstrip()
            hash_part = line[hash_pos:]
            return [before_hash, '', hash_part, '']
        else:
            # # is at the beginning or line is just #
            return [line, '']
    
    # If it's a list item, return as-is
    if is_list_item(line):
        return [line]
    
    # If it's an empty line, return as-is
    if not line.strip():
        return [line]
    
    # Normal paragraph - add extra newline
    return [line, '']

def main():
    lines = []
    for line in sys.stdin:
        line = line.rstrip('\n\r')
        processed = process_line(line)
        lines.extend(processed)
    
    # Handle list item spacing - add blank line after last item in a group
    result = []
    i = 0
    while i < len(lines):
        current_line = lines[i]
        result.append(current_line)
        
        # Check if current line is a list item
        if is_list_item(current_line):
            # Look ahead to see if next non-empty line is not a list item
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                result.append(lines[j])
                j += 1
            
            # If next non-empty line exists and is not a list item, ensure blank line
            if j < len(lines) and lines[j].strip() and not is_list_item(lines[j]):
                # Check if we already have a blank line
                if result and result[-1].strip():
                    result.append('')
            i = j - 1
        
        i += 1
    
    # Output the result
    for line in result:
        print(line)

if __name__ == '__main__':
    main()