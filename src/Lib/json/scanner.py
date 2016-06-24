"""JSON token scanner
"""
import re
try:
    from _json import make_scanner as c_make_scanner
except ImportError:
    c_make_scanner = None

__all__ = ['make_scanner']


# Regular expression object to match a number.
#
# NUMBER_RE = r"""
# # Required integer part, must match at least a digit
# (
#     # Optional minus sign
#     -?
#     # Non-capturing group
#     (?:
#         # 0
#         0
#         # or
#         |
#         # First non-zero digit
#         [1-9]
#         # Zero or more digits
#         \d*
#     )
# )
#
# # Optional fraction part
# (
#     # A dot to indicate start of fraction part
#     \.
#     # One or more digits
#     \d+
# )?
#
# # Optional exponent part
# (
#     # Lower or upper case letter e to indicate start of exponent part
#     [eE]
#     # Optional minus or plus sign of the exponent
#     [-+]?
#     # One or more digits of the exponent
#     \d+
# )?
# """
NUMBER_RE = re.compile(
    r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?',
    (re.VERBOSE | re.MULTILINE | re.DOTALL))


#
def py_make_scanner(context):
    # Scanner function's factory function.
    #
    # @param context: Decoder object.
    #
    # @return: Scanner function.

    # Get parse object function
    parse_object = context.parse_object

    # Get parse array function
    parse_array = context.parse_array

    # Get parse string function
    parse_string = context.parse_string

    # Get match number function
    match_number = NUMBER_RE.match

    # Whether disallow literal control characters
    strict = context.strict

    # Get parse float function
    parse_float = context.parse_float

    # Get parse int function
    parse_int = context.parse_int

    # Get parse constant function
    parse_constant = context.parse_constant

    # Get object hook function
    object_hook = context.object_hook

    # Get object pairs hook function
    object_pairs_hook = context.object_pairs_hook

    # Get memo dict for caching decoded string chunks
    memo = context.memo

    # Create scanner function
    def _scan_once(string, idx):
        # Scan next symbol from input string.
        # Call parse function according to the symbol's type.
        #
        # @param string: JSON data.
        #
        # @param idx: JSON data's parsing position.
        #
        # @return: Next symbol or structure's parsed value.

        #
        try:
            # Get next character
            nextchar = string[idx]

        # If no next character
        except IndexError:
            # Raise StopIteration to notify caller
            raise StopIteration(idx)

        # If have next character.

        # If the character is starting `"` of JSON string,
        if nextchar == '"':
            # Call parse string function,
            # return parsed value, and parsing end position
            return parse_string(string, idx + 1, strict)

        # If the character is starting `{` of JSON object,
        elif nextchar == '{':
            # Call parse object function,
            # return parsed value, and parsing end position
            return parse_object((string, idx + 1), strict,
                _scan_once, object_hook, object_pairs_hook, memo)

        # If the character is starting `[` of JSON array,
        elif nextchar == '[':
            # Call parse array function,
            # return parsed value, and parsing end position
            return parse_array((string, idx + 1), _scan_once)

        # If next symbol is "null"
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            # Return None, and parsing end position
            return None, idx + 4

        # If next symbol is "true"
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            # Return True, and parsing end position
            return True, idx + 4

        # If next symbol is "false"
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            # Return False, and parsing end position
            return False, idx + 5

        # Match a number
        m = match_number(string, idx)

        # If have match result
        if m is not None:
            # Get integer, fraction, and exponent parts
            integer, frac, exp = m.groups()

            # If fraction part or exponent part exists
            if frac or exp:
                # Call parse float function
                res = parse_float(integer + (frac or '') + (exp or ''))

            # If fraction part and exponent part not exist
            else:
                # Call parse int function
                res = parse_int(integer)

            # Return parsed value, and parsing end position
            return res, m.end()

        # If no match result.

        # If next symbol is "NaN"
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            # Call parse constant function,
            # return parsed value, and parsing end position
            return parse_constant('NaN'), idx + 3

        # If next symbol is "Infinity"
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            # Call parse constant function,
            # return parsed value, and parsing end position
            return parse_constant('Infinity'), idx + 8

        # If next symbol is "-Infinity"
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            # Call parse constant function,
            # return parsed value, and parsing end position
            return parse_constant('-Infinity'), idx + 9

        # If rules above all failed
        else:
            # Raise StopIteration to notify caller
            raise StopIteration(idx)

    # Create a wrapping function that clears memo dict after each call. Unused.
    def scan_once(string, idx):
        # Scan next symbol from input string.
        # Call parse function according to the symbol's type.
        #
        # @param string: JSON data.
        #
        # @param idx: JSON data's parsing position.
        #
        # @return: Next symbol or structure's parsed value.
        try:
            # Return parsed value, and parsing end position
            return _scan_once(string, idx)
        # Before returning
        finally:
            # Clear memo dict
            memo.clear()

    # Return scanner function
    return _scan_once


# If C version is available, use C version.
# Else, use Python version.
make_scanner = c_make_scanner or py_make_scanner
