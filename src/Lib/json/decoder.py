"""Implementation of JSONDecoder
"""
import re

from json import scanner
try:
    from _json import scanstring as c_scanstring
except ImportError:
    c_scanstring = None

__all__ = ['JSONDecoder', 'JSONDecodeError']


# Regular expression flags to match multiple lines and enable verbose mode
FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL


# Float NaN object
NaN = float('nan')

# Float infinity object
PosInf = float('inf')

# Float -infinity object
NegInf = float('-inf')


#
class JSONDecodeError(ValueError):
    """Subclass of ValueError with the following additional properties:

    msg: The unformatted error message
    doc: The JSON document being parsed
    pos: The start index of doc where parsing failed
    lineno: The line corresponding to pos
    colno: The column corresponding to pos

    """
    # Note that this exception is used from _json
    def __init__(self, msg, doc, pos):
        # Error line number
        lineno = doc.count('\n', 0, pos) + 1

        # Error column number
        colno = pos - doc.rfind('\n', 0, pos)

        # Get error message with error location
        errmsg = '%s: line %d column %d (char %d)' % (msg, lineno, colno, pos)

        # Call super method
        ValueError.__init__(self, errmsg)

        # Error message
        self.msg = msg

        # JSON data
        self.doc = doc

        # Error in-line position
        self.pos = pos

        # Error line number
        self.lineno = lineno

        # Error column number
        self.colno = colno

    def __reduce__(self):
        # Return reduce value
        return self.__class__, (self.msg, self.doc, self.pos)


# Map special float value's name to object
_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
}


# A regular expression object to match JSON string chunk.
# It non-greedily matches zero or more any character, which are the content
# characters. Then it matches a `"`, a `\`, or a code value in range 0 to 31,
# which is the terminator character.
STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)


# Map character after backslash to decoded character
BACKSLASH = {
    '"': '"', '\\': '\\', '/': '/',
    'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t',
}


#
def _decode_uXXXX(s, pos):
    # Decode Unicode escape into Unicode code value.
    #
    # @param s: JSON data.
    #
    # @param pos: JSON data's parsing end position.
    #
    # @return: Decoded Unicode code value.

    # Get 4-character sequence after "u"
    esc = s[pos + 1:pos + 5]

    # If the sequence length is 4,
    # and the first character is not "x" or "X"
    if len(esc) == 4 and esc[1] not in 'xX':
        #
        try:
            # Decode the sequence as 4 hex digits.
            # Return the decoded Unicode code value.
            return int(esc, 16)

        # If the sequence is not 4 hex digits
        except ValueError:
            # Ignore the error. Let code below handle.
            pass

    # Get error message
    msg = "Invalid \\uXXXX escape"

    # Raise error
    raise JSONDecodeError(msg, s, pos)


#
def py_scanstring(s, end, strict=True,
        _b=BACKSLASH, _m=STRINGCHUNK.match):
    """Scan the string s for a JSON string. End is the index of the
    character in s after the quote that started the JSON string.
    Unescapes all valid JSON string escape sequences and raises ValueError
    on attempt to decode an invalid string. If strict is False then literal
    control characters are allowed in the string.

    Returns a tuple of the decoded string and the index of the character in s
    after the end quote."""

    # Scan for a JSON string chunk until a terminator character is met.
    # Decode the string chunk.
    #
    # @param s: JSON data.
    #
    # @param end: JSON data's parsing end position.
    #
    # @param strict: Whether disallow literal control characters.
    #
    # @param _b: Dict that maps character after backslash to decoded character.
    #
    # @param _m: String chunk match function.
    #
    # @return: Decoded string chunk, and parsing end position.

    # A list of chunks
    chunks = []

    # Cache append method
    _append = chunks.append

    # Get begin position for error message
    begin = end - 1

    # Loop
    while 1:
        # Match string chunk
        chunk = _m(s, end)

        # If no match result
        if chunk is None:
            # Raise error
            raise JSONDecodeError("Unterminated string starting at", s, begin)

        # If have match result.

        # Get match result's end position
        end = chunk.end()

        # Get content characters and the terminator character
        content, terminator = chunk.groups()

        # If content characters are not empty.
        #
        # Content is contains zero or more unescaped string characters
        if content:
            # Add the content characters to chunks list
            _append(content)

        # If the terminator character is `"`,
        # it means end of JSON string.
        #
        # Terminator is the end of string, a literal control character,
        # or a backslash denoting that an escape sequence follows
        if terminator == '"':
            # Stop scanning
            break

        # If the terminator character is not `\`,
        # it means the terminator character is a literal control character with
        # code value in range 0 to 31.
        elif terminator != '\\':
            # If disallow literal control character
            if strict:
                # Get error message.
                #
                #msg = "Invalid control character %r at" % (terminator,)
                msg = "Invalid control character {0!r} at".format(terminator)

                # Raise error
                raise JSONDecodeError(msg, s, end)

            # If allow literal control character
            else:
                # Add the literal control character to chunks list
                _append(terminator)

                # Continue scanning
                continue

        # If the terminator character is `\`.

        #
        try:
            # Get the next character
            esc = s[end]

        # If no next character
        except IndexError:
            # Raise error
            raise JSONDecodeError("Unterminated string starting at", s, begin)

        # If the character is not "u",
        # it means it is non-Unicode escape.
        #
        # If not a unicode escape sequence, must be in the lookup table
        if esc != 'u':
            try:
                # Get decoded character from the lookup table
                char = _b[esc]

            # If decoded character is not found in the lookup table
            except KeyError:
                # Get error message
                msg = "Invalid \\escape: {0!r}".format(esc)

                # Raise error
                raise JSONDecodeError(msg, s, end)

            # If decoded character is found in the lookup table,
            # Increment parsing end position.
            end += 1

        # If the character is "u",
        # it means it is Unicode escape.
        else:
            # Get the Unicode code value
            uni = _decode_uXXXX(s, end)

            # Forward end position
            end += 5

            # If the code value is in low surrogate range,
            # and the JSON data's next two characters are `\u`,
            # it means the code value may be part of a surrogate pair.
            if 0xd800 <= uni <= 0xdbff and s[end:end + 2] == '\\u':
                # Get the second Unicode code value
                uni2 = _decode_uXXXX(s, end + 1)

                # If the second Unicode code value is in high surrogate range,
                # it means the two code values are a surrogate pair.
                if 0xdc00 <= uni2 <= 0xdfff:
                    # Convert the surrogate pair to code point
                    uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))

                    # Forward end position
                    end += 6

            # If the code value is not in low surrogate range,
            # or the JSON data's next two characters are not `\u`,
            # consider the Unicode code point 1-byte,
            # even if the code value is in low surrogate range.

            # Convert the code point to character
            char = chr(uni)

        # Add decoded character to chunks list
        _append(char)

    # Join chunks into a result string.
    # Return the result string and the parsing end position.
    return ''.join(chunks), end


# If C version is available, use C version.
# Else, use Python version.
#
# Use speedup if available
scanstring = c_scanstring or py_scanstring


# Regular expression object to match zero or more white spaces
WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)

# White-space character set
WHITESPACE_STR = ' \t\n\r'


#
def JSONObject(s_and_end, strict, scan_once, object_hook, object_pairs_hook,
               memo=None, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    # Parse JSON object to Python dict object.
    #
    # @param s_and_end: A tuple of (JSON data, parsing end position).
    #
    # @param strict: Whether disallow literal control characters.
    #
    # @param scan_once: Scan function.
    #
    # @param object_hook: Object hook function.
    #
    # @param object_pairs_hook: Object pairs hook function.
    #
    # @param memo: Memo dict for caching decoded string chunks.
    #
    # @param _w: White space match function.
    #
    # @param _ws: White-space character set.
    #
    # @return: Python dict object.

    # Get JSON data, and parsing end position
    s, end = s_and_end

    # An ordered list of JSON object property items
    pairs = []

    # Cache append function
    pairs_append = pairs.append

    # If memo dict is not given.
    #
    # Backwards compatibility
    if memo is None:
        # Create memo dict
        memo = {}

    # Cache setdefault function
    memo_get = memo.setdefault

    # Get next character.
    #
    # Use a slice to prevent IndexError from being raised, the following
    # check will raise a more specific ValueError if the string is empty
    nextchar = s[end:end + 1]

    # If the character is not `"`.
    #
    # Normally we expect nextchar == '"'
    if nextchar != '"':
        # If the character is white space
        if nextchar in _ws:
            # Skip white spaces
            end = _w(s, end).end()

            # Get next character
            nextchar = s[end:end + 1]

        # If the character is `}`.
        #
        # Trivial empty object
        if nextchar == '}':
            # If object pairs hook function is given
            if object_pairs_hook is not None:
                # Call object pairs hook function to create result
                result = object_pairs_hook(pairs)

                # Return the result, and parsing end position
                return result, end + 1

            # If object pairs hook function is not given

            # Create result dict
            pairs = {}

            # If object hook function is given
            if object_hook is not None:
                # Call object hook function
                pairs = object_hook(pairs)

            # Return the result dict, and parsing end position
            return pairs, end + 1

        # If the character is not `}` and `"`,
        # it means start of property name is expected but not found.
        elif nextchar != '"':
            # Raise error
            raise JSONDecodeError(
                "Expecting property name enclosed in double quotes", s, end)

        # If the character is `"`,
        # it means start of property name.

    # If the character is `"`,
    # it means start of property name.

    # Increment parsing end position
    end += 1

    # Loop
    while True:
        # Scan for a JSON string chunk until a terminator character is met.
        # Decode the string chunk, get parsing end position
        key, end = scanstring(s, end, strict)

        # Cache the decoded string chunk
        key = memo_get(key, key)

        # If next character is not `:`.
        #
        # To skip some function call overhead we optimize the fast paths where
        # the JSON key separator is ": " or just ":".
        if s[end:end + 1] != ':':
            # Skip white spaces
            end = _w(s, end).end()

            # If next character is not `:`
            if s[end:end + 1] != ':':
                # Raise error
                raise JSONDecodeError("Expecting ':' delimiter", s, end)

        # Increment parsing end position
        end += 1

        #
        try:
            # If next character is white space
            if s[end] in _ws:
                # Increment parsing end position
                end += 1

                # If next character is white space
                if s[end] in _ws:
                    # Skip white spaces
                    end = _w(s, end + 1).end()

        # If no next character
        except IndexError:
            # Ignore the error
            pass

        #
        try:
            # Scan property value, get parsing end position
            value, end = scan_once(s, end)

        # If no more value
        except StopIteration as err:
            # Raise error
            raise JSONDecodeError("Expecting value", s, err.value) from None

        # Add property item to pairs list
        pairs_append((key, value))

        #
        try:
            # Get next character
            nextchar = s[end]

            # If next character is white space
            if nextchar in _ws:
                # Skip white spaces
                end = _w(s, end + 1).end()

                # Get next character
                nextchar = s[end]

        # If no next character
        except IndexError:
            # Set next character to empty
            nextchar = ''

        # Increment parsing end position
        end += 1

        # If the character is `}`
        if nextchar == '}':
            # Stop scanning dict items
            break

        # If the character is not `}` and `,`,
        # it means delimiter is expected but not found
        elif nextchar != ',':
            # Raise error
            raise JSONDecodeError("Expecting ',' delimiter", s, end - 1)

        # Skip white spaces
        end = _w(s, end).end()

        # Get next character
        nextchar = s[end:end + 1]

        # Increment parsing end position
        end += 1

        # If the character is not `}` and `"`,
        # it means start of property name is expected name but not found.
        if nextchar != '"':
            # Raise error
            raise JSONDecodeError(
                "Expecting property name enclosed in double quotes", s, end - 1)

        # If the character is `"`,
        # it means start of property name.
        # Continue the loop.

    # If object pairs hook function is given
    if object_pairs_hook is not None:
        # Call object pairs hook function to create result
        result = object_pairs_hook(pairs)

        # Return the result, and parsing end position
        return result, end

    # Create result dict
    pairs = dict(pairs)

    # If object hook function is given
    if object_hook is not None:
        # Call object hook function
        pairs = object_hook(pairs)

    # Return the result dict, and parsing end position
    return pairs, end


#
def JSONArray(s_and_end, scan_once, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    # Parse JSON array to Python list object.
    #
    # @param s_and_end: A tuple of (JSON data, parsing end position).
    #
    # @param scan_once: Scan function.
    #
    # @param _w: White space match function.
    #
    # @param _ws: White-space character set.
    #
    # @return: Python list object, and parsing end position.

    # Get JSON data, and parsing end position
    s, end = s_and_end

    # A list of values
    values = []

    # Get next character
    nextchar = s[end:end + 1]

    # If the character is white space
    if nextchar in _ws:
        # Skip white spaces
        end = _w(s, end + 1).end()

        # Get next character
        nextchar = s[end:end + 1]

    # If the character is `]`.
    #
    # Look-ahead for trivial empty array
    if nextchar == ']':
        # Return the list of values, and parsing end position
        return values, end + 1

    # If the character is not `]`.

    # Cache append function
    _append = values.append

    # Loop
    while True:
        #
        try:
            # Scan next value, get parsing end position
            value, end = scan_once(s, end)

        # If no more value
        except StopIteration as err:
            # Raise error
            raise JSONDecodeError("Expecting value", s, err.value) from None

        # Append the value to list
        _append(value)

        # Get next character
        nextchar = s[end:end + 1]

        # If the character is white space
        if nextchar in _ws:
            # Skip white spaces
            end = _w(s, end + 1).end()

            # Get next character
            nextchar = s[end:end + 1]

        # Increment parsing end position
        end += 1

        # If the character is `]`
        if nextchar == ']':
            # Stop scanning list values
            break

        # If the character is not `]` and `,`,
        # it means delimiter is expected but not found.
        elif nextchar != ',':
            # Raise error
            raise JSONDecodeError("Expecting ',' delimiter", s, end - 1)

        #
        try:
            # If next character is white space
            if s[end] in _ws:
                # Increment parsing end position
                end += 1

                # If next character is white space
                if s[end] in _ws:
                    # Skip white spaces
                    end = _w(s, end + 1).end()

        # If no next character
        except IndexError:
            # Ignore the error. Let next loop round handle.
            pass

    # Return the list of values, and parsing end position
    return values, end


#
class JSONDecoder(object):
    """Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | str               |
    +---------------+-------------------+
    | number (int)  | int               |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.

    """

    def __init__(self, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True,
            object_pairs_hook=None):
        """``object_hook``, if specified, will be called with the result
        of every JSON object decoded and its return value will be used in
        place of the given ``dict``.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        ``object_pairs_hook``, if specified will be called with the result of
        every JSON object decoded with an ordered list of pairs.  The return
        value of ``object_pairs_hook`` will be used instead of the ``dict``.
        This feature can be used to implement custom decoders that rely on the
        order that the key and value pairs are decoded (for example,
        collections.OrderedDict will remember the order of insertion). If
        ``object_hook`` is also defined, the ``object_pairs_hook`` takes
        priority.

        ``parse_float``, if specified, will be called with the string
        of every JSON float to be decoded. By default this is equivalent to
        float(num_str). This can be used to use another datatype or parser
        for JSON floats (e.g. decimal.Decimal).

        ``parse_int``, if specified, will be called with the string
        of every JSON int to be decoded. By default this is equivalent to
        int(num_str). This can be used to use another datatype or parser
        for JSON integers (e.g. float).

        ``parse_constant``, if specified, will be called with one of the
        following strings: -Infinity, Infinity, NaN.
        This can be used to raise an exception if invalid JSON numbers
        are encountered.

        If ``strict`` is false (true is the default), then control
        characters will be allowed inside strings.  Control characters in
        this context are those with character codes in the 0-31 range,
        including ``'\\t'`` (tab), ``'\\n'``, ``'\\r'`` and ``'\\0'``.

        """
        # Object hook function
        self.object_hook = object_hook

        # Parse float function
        self.parse_float = parse_float or float

        # Parse int function
        self.parse_int = parse_int or int

        # Parse constant function
        self.parse_constant = parse_constant or _CONSTANTS.__getitem__

        # Whether disallow literal control characters
        self.strict = strict

        # Object pairs hook function
        self.object_pairs_hook = object_pairs_hook

        # Parse object function
        self.parse_object = JSONObject

        # Parse array function
        self.parse_array = JSONArray

        # Parse string function
        self.parse_string = scanstring

        # Memo dict for caching decoded string chunks
        self.memo = {}

        # Create scan function
        self.scan_once = scanner.make_scanner(self)


    def decode(self, s, _w=WHITESPACE.match):
        """Return the Python representation of ``s`` (a ``str`` instance
        containing a JSON document).

        """
        # Decode JSON data to Python object.
        # If JSON data have extraneous data at the end, raise error.
        #
        # @param s: JSON data.
        #
        # @param _w: White space match function.
        #
        # @return: Python object.

        # Skip starting white spaces.
        # Call "raw_decode" to decode the JSON data.
        # Get result object, and parsing end position.
        obj, end = self.raw_decode(s, idx=_w(s, 0).end())

        # Skip ending white spaces, get parsing end position
        end = _w(s, end).end()

        # If parsing end position is not JSON data end
        if end != len(s):
            # Raise error
            raise JSONDecodeError("Extra data", s, end)

        # Return the result object
        return obj

    def raw_decode(self, s, idx=0):
        """Decode a JSON document from ``s`` (a ``str`` beginning with
        a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.

        """
        # Decode JSON data to Python object.
        #
        # @param s: JSON data.
        #
        # @param _w: White space match function.
        #
        # @return: Python object, and parsing end position.

        #
        try:
            # Scan a value, get parsing end position
            obj, end = self.scan_once(s, idx)

        # If no more value
        except StopIteration as err:
            # Raise error
            raise JSONDecodeError("Expecting value", s, err.value) from None

        # Return the Python object, and parsing end position
        return obj, end
