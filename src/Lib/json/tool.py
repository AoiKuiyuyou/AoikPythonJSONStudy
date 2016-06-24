r"""Command-line tool to validate and pretty-print JSON

Usage::

    $ echo '{"json":"obj"}' | python -m json.tool
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -m json.tool
    Expecting property name enclosed in double quotes: line 1 column 3 (char 2)

"""
import argparse
import collections
import json
import sys


def main():
    # Program main function.
    #
    # @return: None.

    # Program command passed to ArgumentParser
    prog = 'python -m json.tool'

    # Program description
    description = ('A simple command line interface for json module '
                   'to validate and pretty-print JSON objects.')

    # Create ArgumentParser
    parser = argparse.ArgumentParser(prog=prog, description=description)

    # Add arguments

    #
    parser.add_argument('infile', nargs='?', type=argparse.FileType(),
                        help='a JSON file to be validated or pretty-printed')

    #
    parser.add_argument('outfile', nargs='?', type=argparse.FileType('w'),
                        help='write the output of infile to outfile')

    #
    parser.add_argument('--sort-keys', action='store_true', default=False,
                        help='sort the output of dictionaries alphabetically by key')

    # Parse command arguments
    options = parser.parse_args()

    # Get input file. Default is stdin.
    infile = options.infile or sys.stdin

    # Get output file. Default is stdout.
    outfile = options.outfile or sys.stdout

    # Whether sort dict keys
    sort_keys = options.sort_keys

    # With input file context
    with infile:
        #
        try:
            # If sort dict keys
            if sort_keys:
                # Decode JSON data in input file into Python object
                obj = json.load(infile)

            # If not sort dict keys
            else:
                # Decode JSON data in input file into Python object,
                # using "collections.OrderedDict" as object pairs hook in order
                # to keep original order.
                obj = json.load(infile,
                                object_pairs_hook=collections.OrderedDict)
        # If ValueError is raised
        except ValueError as e:
            # Raise SystemExit to exit
            raise SystemExit(e)

    # With output file context
    with outfile:
        # Encode Python object JSON data with 4-space indentation.
        # Write to output file.
        json.dump(obj, outfile, sort_keys=sort_keys, indent=4)

        # Write a newline
        outfile.write('\n')


# If this module is main module
if __name__ == '__main__':
    # Call "main" function
    main()
