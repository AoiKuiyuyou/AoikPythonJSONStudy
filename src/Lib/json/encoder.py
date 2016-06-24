"""Implementation of JSONEncoder
"""
import re

try:
    from _json import encode_basestring_ascii as c_encode_basestring_ascii
except ImportError:
    c_encode_basestring_ascii = None
try:
    from _json import encode_basestring as c_encode_basestring
except ImportError:
    c_encode_basestring = None
try:
    from _json import make_encoder as c_make_encoder
except ImportError:
    c_make_encoder = None


# Regular expression object to match a character that should be escaped.
# The character is either:
# - Character with code value from 0 to 31;
# - Character `\`, `"`, `\b`, `\f`, `\n`, `\r`, or `\t`.
ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t]')


# Regular expression object to match a character that should be escaped
# if the output mode is ASCII-only. The character is either:
# - Character `\` or `"`;
# - Any character that is not space, `-` or `~`.
ESCAPE_ASCII = re.compile(r'([\\"]|[^\ -~])')


# Regular expression object to match a character with code value from 128 to
# 255
HAS_UTF8 = re.compile(b'[\x80-\xff]')


# Map character to escape sequence
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}


# For code point from 0 to 31
for i in range(0x20):
    # Add the character's Unicode escape to "ESCAPE_DCT".
    # E.g. 10 -> \u000a .
    ESCAPE_DCT.setdefault(chr(i), '\\u{0:04x}'.format(i))
    #ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))


# Float type's infinity object
INFINITY = float('inf')


# Float type's repr function
FLOAT_REPR = repr


#
def py_encode_basestring(s):
    """Return a JSON representation of a Python string

    """
    # Escape a string. E.g. `"` -> `\"`.
    # Do not ensure ASCII-only.
    #
    # @param s: String to be escaped.
    #
    # @return: Escaped string.

    # Create replace function used for "re.sub" below.
    def replace(match):
        # Return escape sequence for matched character in given match result.
        #
        # @param match: Match result.
        #
        # @return: Escape sequence for matched character.

        # Get the matched character.
        # Use the matched character as key to get escape sequence.
        # Return the escape sequence.
        return ESCAPE_DCT[match.group(0)]

    # Use regular expression object "ESCAPE" to find each character that should
    # be escaped. For each character, call "replace" to get the escape sequence
    # used as substitution value.
    #
    # Add double quote to both side.
    #
    # Return the escaped string.
    return '"' + ESCAPE.sub(replace, s) + '"'


# If C version is available, use C version.
# Else, use Python version.
encode_basestring = (c_encode_basestring or py_encode_basestring)


def py_encode_basestring_ascii(s):
    """Return an ASCII-only JSON representation of a Python string

    """
    # Escape a string. E.g. `"` -> `\"`.
    # Ensure ASCII-only.
    #
    # @param s: String to be escaped.
    #
    # @return: Escaped string.

    # Create replace function used for "re.sub" below.
    def replace(match):
        # Return escape sequence for matched character in given match result.
        #
        # @param match: Match result.
        #
        # @return: Escape sequence for matched character.

        # Get the matched character
        s = match.group(0)
        try:
            # Use the matched character as key to get escape sequence.
            #
            # If the escape sequence is found,
            # return the escape sequence.
            return ESCAPE_DCT[s]

        # If the escaped sequence is not found,
        # it means the character's code point is outside ASCII range
        except KeyError:
            # Get the character's code point
            n = ord(s)

            # If the character's code point is within two-byte range
            if n < 0x10000:
                # Return the character's two-byte Unicode escape
                return '\\u{0:04x}'.format(n)
                #return '\\u%04x' % (n,)

            # If the character's code point is beyond two-byte range,
            # it means the character needs be encoded using surrogate pair.
            else:
                # surrogate pair
                n -= 0x10000

                # Get high surrogate value
                s1 = 0xd800 | ((n >> 10) & 0x3ff)

                # Get low surrogate value
                s2 = 0xdc00 | (n & 0x3ff)

                # Return the character's four-byte Unicode escape
                return '\\u{0:04x}\\u{1:04x}'.format(s1, s2)

    # Use regular expression object "ESCAPE_ASCII" to find each character that
    # should be escaped. For each character, call "replace" to get the escape
    # sequence used as substitution value.
    #
    # Add double quote to both side.
    #
    # Return the escaped string.
    return '"' + ESCAPE_ASCII.sub(replace, s) + '"'


# If C version is available, use C version.
# Else, use Python version.
encode_basestring_ascii = (
    c_encode_basestring_ascii or py_encode_basestring_ascii)


#
class JSONEncoder(object):
    """Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str               | string        |
    +-------------------+---------------+
    | int, float        | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).

    """

    # Default item separator
    item_separator = ', '

    # Default key separator
    key_separator = ': '

    #
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, default=None):
        """Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is false, then it is a TypeError to attempt
        encoding of keys that are not str, int, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is true, the output is guaranteed to be str
        objects with all incoming non-ASCII characters escaped.  If
        ensure_ascii is false, the output can contain non-ASCII characters.

        If check_circular is true, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is true, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is true, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a non-negative integer, then JSON array
        elements and object members will be pretty-printed with that
        indent level.  An indent level of 0 will only insert newlines.
        None is the most compact representation.

        If specified, separators should be an (item_separator, key_separator)
        tuple.  The default is (', ', ': ') if *indent* is ``None`` and
        (',', ': ') otherwise.  To get the most compact JSON representation,
        you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        """

        # Whether skip non-regular-type keys
        self.skipkeys = skipkeys

        # Whether ensure ASCII-only output
        self.ensure_ascii = ensure_ascii

        # Whether check circular references
        self.check_circular = check_circular

        # Whether allow NaN
        self.allow_nan = allow_nan

        # Whether sort dict keys
        self.sort_keys = sort_keys

        # Indentation argument: a text, or number of spaces
        self.indent = indent

        # If item and key separators are given
        if separators is not None:
            # Set item and key separators
            self.item_separator, self.key_separator = separators

        # If item and key separators are not given,
        # and indentation argument is given.
        elif indent is not None:
            # Set item separators to ","
            self.item_separator = ','

        # If default hook function is given
        if default is not None:
            # Override "JSONEncoder.default" function
            self.default = default

    def default(self, o):
        """Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                # Let the base class default method raise the TypeError
                return JSONEncoder.default(self, o)

        """
        # Handle an unserializable object.
        #
        # @param o: Unserializable object to handle.
        #
        # @return: A serializable object, or raise TypeError.

        # Raise error
        raise TypeError(repr(o) + " is not JSON serializable")

    def encode(self, o):
        """Return a JSON string representation of a Python data structure.

        >>> from json.encoder import JSONEncoder
        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'

        """
        # Encode Python object to JSON data.
        #
        # @param o: Python Object to encode.
        #
        # @return: JSON data.

        # If given object is string.
        #
        # This is for extremely simple cases and benchmarks.
        if isinstance(o, str):
            # If ensure output is ASCII-only
            if self.ensure_ascii:
                # Call ASCII-only string escape function
                return encode_basestring_ascii(o)
            else:
                # Call string escape function
                return encode_basestring(o)

        # If given object is not string,
        # Call "self.iterencode" to get an iterable of output chunks.
        #
        # This doesn't pass the iterator directly to ''.join() because the
        # exceptions aren't as detailed.  The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        chunks = self.iterencode(o, _one_shot=True)

        # If the iterable is not list or tuple
        if not isinstance(chunks, (list, tuple)):
            # Convert the iterable to a list of chunks
            chunks = list(chunks)

        # Join the list of chunks into a result string.
        # Return the result string.
        return ''.join(chunks)

    def iterencode(self, o, _one_shot=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        # Encode-to-iterable function that encodes Python object to JSON data
        # by returning an iterable of result chunks.
        #
        # @param o: Python object to encode.
        #
        # @param _one_shot: Whether the iteration is one-shot.
        #
        # @return: An iterable of result chunks.

        # If check circular references
        if self.check_circular:
            # Create makers dict
            markers = {}
        else:
            # Set makers dict to None
            markers = None

        # If ensure output is ACII-only
        if self.ensure_ascii:
            # Use ACII-only string escape function
            _encoder = encode_basestring_ascii
        else:
            # Use non-ACII-only string escape function
            _encoder = encode_basestring

        # Create an float-to-text function
        def floatstr(o, allow_nan=self.allow_nan,
                _repr=FLOAT_REPR, _inf=INFINITY, _neginf=-INFINITY):
            # Get a float object's text.
            #
            # @param allow_nan: Whether allow NaN.
            #
            # @param _repr: Repr function for regular float objects.
            #
            # @param _inf: Infinity object.
            #
            # @param _neginf: -Infinity object.
            #
            # @return: Float object's text.

            # Check for specials.  Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on the
            # internals.

            # If the object is NaN
            if o != o:
                # Get the object's text
                text = 'NaN'

            # If the object is infinity
            elif o == _inf:
                # Get the object's text
                text = 'Infinity'

            # If the object is -infinity
            elif o == _neginf:
                # Get the object's text
                text = '-Infinity'

            # If the object is not special values above
            else:
                # Use given repr function to get the object's text
                return _repr(o)

            # If NaN is not allowed
            if not allow_nan:
                # Raise error
                raise ValueError(
                    "Out of range float values are not JSON compliant: " +
                    repr(o))

            # Return the object's text
            return text


        # If the iteration is one-shot,
        # and C version of encoder function is available,
        # and indentation argument is not given
        if (_one_shot and c_make_encoder is not None
                and self.indent is None):
            # Use C version of make-encoder function to create iterable
            _iterencode = c_make_encoder(
                markers, self.default, _encoder, self.indent,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, self.allow_nan)

        # If the iteration is not one-shot,
        # or C version of encoder is not available,
        # or indentation argument is given
        else:
            # Use Python version of make-encoder function to create iterable
            _iterencode = _make_iterencode(
                markers, self.default, _encoder, self.indent, floatstr,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, _one_shot)

        # Create and return the iterable
        return _iterencode(o, 0)


#
def _make_iterencode(markers, _default, _encoder, _indent, _floatstr,
        _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot,
        ## HACK: hand-optimized bytecode; turn globals into locals
        ValueError=ValueError,
        dict=dict,
        float=float,
        id=id,
        int=int,
        isinstance=isinstance,
        list=list,
        str=str,
        tuple=tuple,
    ):
    # Factory function of encode-to-iterable function that encodes Python
    # object to JSON data by returning an iterable of result chunks.
    #
    # @param markers: Markers dict to remember circular references.
    #
    # @param _default: Unserializable object handler.
    #
    # @param _encoder: String escape function.
    #
    # @param _indent: Indentation argument: a text, or number of spaces.
    #
    # @param _floatstr: Float-to-text function.
    #
    # @param _key_separator: Key separator.
    #
    # @param _item_separator: Item separator.
    #
    # @param _sort_keys: Whether sort dict keys.
    #
    # @param _skipkeys: Whether skip non-regular-type keys.
    #
    # @param _one_shot: Whether the iteration is one-shot.
    #
    # @return: Encode-to-iterable function.

    # If indentation argument is given,
    # and the value is not string,
    # it means it is number of spaces.
    if _indent is not None and not isinstance(_indent, str):
        # Get indentation text
        _indent = ' ' * _indent

    # Encode-to-iterable function for list object
    def _iterencode_list(lst, _current_indent_level):
        # Encode a list to JSON data by returning an iterable of result chunks.
        #
        # @param lst: A list object.
        #
        # @param _current_indent_level: Indentation level.
        #
        # @return: An iterable of result chunks.

        # If the list is empty
        if not lst:
            # Yield result
            yield '[]'

            # Stop the iteration
            return

        # If check circular references
        if markers is not None:
            # Get the list's object ID
            markerid = id(lst)

            # If the object ID exists in the markers dict
            if markerid in markers:
                # Raise error
                raise ValueError("Circular reference detected")

            # If the object ID not exists in the markers dict,
            # add the object ID to the markers dict.
            markers[markerid] = lst

        # Output chunk to yield
        buf = '['

        # If indentation argument is given
        if _indent is not None:
            # Increment indentation level
            _current_indent_level += 1

            # Get indentation text
            newline_indent = '\n' + _indent * _current_indent_level

            # Add indentation text to item separator
            separator = _item_separator + newline_indent

            # Add indentation text to the output chunk
            buf += newline_indent

        # If indentation argument is not given
        else:
            # Set indentation text to None
            newline_indent = None

            # Use item separator as-is
            separator = _item_separator

        # Whether is the first item in the list
        first = True

        # For each item in the list
        for value in lst:
            # If is the first item,
            # it means use the output chunk above.
            if first:
                # Set the boolean to False
                first = False

            # If is not the first item,
            # it means not use the output chunk above.
            else:
                # Set item separator as output chunk
                buf = separator

            # If the item is string
            if isinstance(value, str):
                # Yield the output chunk plus the item's escaped text.
                yield buf + _encoder(value)

            # If the item is None
            elif value is None:
                # Yield the output chunk plus the item's text.
                yield buf + 'null'

            # If the item is True
            elif value is True:
                # Yield the output chunk plus the item's text.
                yield buf + 'true'

            # If the item is False
            elif value is False:
                # Yield the output chunk plus the item's text.
                yield buf + 'false'

            # If the item is integer
            elif isinstance(value, int):
                # Yield the output chunk plus the item's text.
                #
                # Subclasses of int/float may override __str__, but we still
                # want to encode them as integers/floats in JSON. One example
                # within the standard library is IntEnum.
                yield buf + str(int(value))

            # If the item is float
            elif isinstance(value, float):
                # Yield the output chunk plus the item's text.
                #
                # see comment above for int
                yield buf + _floatstr(float(value))

            # If the item is something else
            else:
                # Yield the output chunk
                yield buf

                # If the item is list or tuple
                if isinstance(value, (list, tuple)):
                    # Create another iterable to encode the item
                    chunks = _iterencode_list(value, _current_indent_level)

                # If the item is dict
                elif isinstance(value, dict):
                    # Create another iterable to encode the item
                    chunks = _iterencode_dict(value, _current_indent_level)

                # If the item is something else
                else:
                    # Create another iterable to encode the item
                    chunks = _iterencode(value, _current_indent_level)

                # Yield from the iterable
                yield from chunks

        # If indentation level is incremented above
        if newline_indent is not None:
            # Decrement indentation level
            _current_indent_level -= 1

            # Yield an indentation
            yield '\n' + _indent * _current_indent_level

        # Yield list ending "]"
        yield ']'

        # If check circular references
        if markers is not None:
            # Delete the object ID from the markers dict
            del markers[markerid]

    # Encode-to-iterable function for dict object
    def _iterencode_dict(dct, _current_indent_level):
        # Encode a dict to JSON data by returning an iterable of result chunks.
        #
        # @param dct: A dict object.
        #
        # @param _current_indent_level: Indentation level.
        #
        # @return: An iterable of result chunks.

        # If the dict is empty
        if not dct:
            # Yield result
            yield '{}'

            # Stop the iteration
            return

        # If check circular references
        if markers is not None:
            # Get the dict's object ID
            markerid = id(dct)

            # If the object ID exists in the markers dict
            if markerid in markers:
                # Raise error
                raise ValueError("Circular reference detected")

            # If the object ID not exists in the markers dict,
            # add the object ID to the markers dict.
            markers[markerid] = dct

        # Yield starting `{`
        yield '{'

        # If indentation argument is given
        if _indent is not None:
            # Increment indentation level
            _current_indent_level += 1

            # Get indentation text
            newline_indent = '\n' + _indent * _current_indent_level

            # Add indentation text to item separator
            item_separator = _item_separator + newline_indent

            # Yield indentation text
            yield newline_indent
        else:
            # Set indentation text to None
            newline_indent = None

            # Use item separator as-is
            item_separator = _item_separator

        # Whether is the first item in the dict
        first = True

        # If sort dict keys
        if _sort_keys:
            # Get iterable of sorted items
            items = sorted(dct.items(), key=lambda kv: kv[0])

        # If not sort dict keys
        else:
            # Get iterable of items
            items = dct.items()

        # For each item
        for key, value in items:
            # If the key is string
            if isinstance(key, str):
                # No need to convert the key to text
                pass

            # If the key is float.
            #
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                # Convert the key to text.
                #
                # see comment for int/float in _make_iterencode
                key = _floatstr(float(key))

            # If the key is True
            elif key is True:
                # Convert the key to text
                key = 'true'

            # If the key is False
            elif key is False:
                # Convert the key to text
                key = 'false'

            # If the key is None
            elif key is None:
                # Convert the key to text
                key = 'null'

            # If the key is integer
            elif isinstance(key, int):
                # Convert the key to text.
                #
                # see comment for int/float in _make_iterencode
                key = str(int(key))

            # If the key is of non-regular-type,
            # and skip non-regular-type keys
            elif _skipkeys:
                # Skip the item
                continue

            # If the key is of non-regular-type,
            # and not skip non-regular-type keys
            else:
                # Raise error
                raise TypeError("key " + repr(key) + " is not a string")

            # If is the first item
            if first:
                # Set the boolean to False
                first = False

            # If is not the first item
            else:
                # Yield item separator
                yield item_separator

            # Yield escaped key
            yield _encoder(key)

            # Yield key separator
            yield _key_separator

            # If the item value is string
            if isinstance(value, str):
                # Yield the item value's escaped text
                yield _encoder(value)

            # If the item value is None
            elif value is None:
                # Yield the item value's text
                yield 'null'

            # If the item value is True
            elif value is True:
                # Yield the item value's text
                yield 'true'

            # If the item value is False
            elif value is False:
                # Yield the item value's text
                yield 'false'

            # If the item value is integer
            elif isinstance(value, int):
                # Yield the item value's text.
                #
                # see comment for int/float in _make_iterencode
                yield str(int(value))

            # If the item value is float
            elif isinstance(value, float):
                # Yield the item value's text.
                #
                # see comment for int/float in _make_iterencode
                yield _floatstr(float(value))

            # If the item value is something else
            else:
                # If the item value is list or tuple
                if isinstance(value, (list, tuple)):
                    # Create another iterable to encode the item value
                    chunks = _iterencode_list(value, _current_indent_level)

                # If the item value is dict
                elif isinstance(value, dict):
                    # Create another iterable to encode the item value
                    chunks = _iterencode_dict(value, _current_indent_level)

                # If the item value is something else
                else:
                    # Create another iterable to encode the item value
                    chunks = _iterencode(value, _current_indent_level)

                # Yield from the iterable
                yield from chunks

        # If indentation level is incremented above
        if newline_indent is not None:
            # Decrement indentation level
            _current_indent_level -= 1

            # Yield an indentation
            yield '\n' + _indent * _current_indent_level

        # Yield dict ending "]"
        yield '}'

        # If check circular references
        if markers is not None:
            # Delete the object ID from the markers dict
            del markers[markerid]

    # Encode-to-iterable function for object
    def _iterencode(o, _current_indent_level):
        # Encode an object to JSON data by returning an iterable of result
        # chunks.
        #
        # @param o: An object.
        #
        # @param _current_indent_level: Indentation level.
        #
        # @return: An iterable of result chunks.

        # If the object is string
        if isinstance(o, str):
            # Yield the object's escaped text
            yield _encoder(o)

        # If the object is None
        elif o is None:
            # Yield the object's text
            yield 'null'

        # If the object is True
        elif o is True:
            # Yield the object's text
            yield 'true'

        # If the object is False
        elif o is False:
            # Yield the object's text
            yield 'false'

        # If the object is integer
        elif isinstance(o, int):
            # Yield the object's text.
            #
            # see comment for int/float in _make_iterencode
            yield str(int(o))

        # If the object is float
        elif isinstance(o, float):
            # Yield the object's text.
            #
            # see comment for int/float in _make_iterencode
            yield _floatstr(float(o))

        # If the object is list or tuple
        elif isinstance(o, (list, tuple)):
            # Create another iterable to encode the object.
            # Yield from the iterable.
            yield from _iterencode_list(o, _current_indent_level)

        # If the object is dict
        elif isinstance(o, dict):
            # Create another iterable to encode the object
            # Yield from the iterable.
            yield from _iterencode_dict(o, _current_indent_level)

        # If the object is something else
        else:
            # If check circular references
            if markers is not None:
                # Get the object ID
                markerid = id(o)

                # If the object ID exists in the markers dict
                if markerid in markers:
                    # Raise error
                    raise ValueError("Circular reference detected")

                # If the object ID not exists in the markers dict,
                # add the object ID to the markers dict.
                markers[markerid] = o

            # Call unserializable object handler to convert the object to
            # a serializable object.
            o = _default(o)

            # Create another iterable to encode the serializable object.
            # Yield from the iterable.
            yield from _iterencode(o, _current_indent_level)

            # If check circular references
            if markers is not None:
                # Delete the object ID from the markers dict
                del markers[markerid]

    # Return the encode-to-iterable function for object
    return _iterencode
