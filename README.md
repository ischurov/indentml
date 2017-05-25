# indentml
## General-purpose indent-based markup language

**indentml** (previously known as *MLQQ*) is a simple general-purpose indent-based markup language designed to represent tree-like structures in human-readable way. It is similar to *YAML* but simpler.

### Install

    pip install indentml
   
Currently only Python 3 supported.

### Code samples

    \topic
        \id dicts-objects
        \heading \lang en
            Dicts / objects
        \description \lang en
            The standard structure to store elements accessible by arbitrary keys
            (mapping) in Python is called a dict (dictionary) and in JavaScript
            — object.
        \compare
            \id dict-object-creation
            \what \lang en
                Creation of dictionary / object
            \python
                my_dict = {'a': 10, 'b': 20}
                my_dict['a']
                my_dict.a # error
            \js
                var my_obj = {a: 10, b: 20};
                my_obj['a']
                my_obj.a
                \comment \lang en
                    You can access elements of an object either with square brackets
                    or with dot-notation.

    \figure
        \source http://example.com/somefig.png
        \caption Some figure
        \width 500px
    
    \question
        Do you like qqmbr?
        \quiz
            \choice
                No.
                \comment You didn't even try!
            \choice \correct
                Yes, i like it very much!
                \comment And so do I!


### Syntax
#### Special characters
The following characters have special meaning in **indetml**:

1. **Tag beginning character.** This character is used to mark the beginning of any tag. By default, it is backslash `\` 
(like in LaTeX), but can be configured to any other character. If you need to enter this character literally, you have 
to escape it with the same character (like `\\`). You can also escape other special characters listed below with *tag beginning character*.
2. **Separator character** is used to separate the rest of line which contains *block tag* (see below). By default it is pipe `|`.
3. Opening and closing brackets: `{`, `}`, and `[`, `]`, used to indicate the content that belongs to *inline tags*, see below.
4. Tabs are forbidden at the beginning of the line in **indentml** (just like in YAML).

#### Block tags
Block tags are typed at the beginning of the line, after several spaces that mark *indent* of a tag.  
Block tag starts with *tag beginning character* and ends with the whitespace or newline character. All the lines below the block tag
which indent is greater than tag's indent are appended to the tag. When indent decreases, tag is closed. E.g.

    \tag
        Hello
        \othertag
            I'm indentml
        How are you?
    I'm fine
    
will be translated into the following XML tree:

    <tag>Hello
    <othertag>I'm indentml
    </othertag>How are you?
    </tag>I'm fine

The rest of a line where block tag begins will be attached to that tag either, but it is handled a bit differently
if it contains other valid block tags or a *separator character*. Every block tag begins new line.
For example:

    \image \src http://example.com \width 100%
        Some image

Is equivalent to
    
    \image
        \src
            http://example.com
        \width
            100%
    Some image

And renders to the following XML:

    <image><src>http://example.com </src><width>100%
    </width>Some image</image>

If *separator character* presented, the line is splitted by this character and every part is attached to its own `_item` tag. For example:

    \a http://example.com | some example
    
Is translated to

    \a
        \_item 
            http://example.com
        \_item
            some example
        
This allows to add attribute-like subtags in a compact way.

Tag name doesn't necessary should be valid Python identifier, e.g. one can introduce markdown-style header tags like

    \### I'm header of 3'd level
    \#### And I'm header of 4'th level

Tag name cannot contain space-like characters, opening brackets `{` and `[`, separator character (default `|`) 
and ampresand `&` (as it is used internally to escape special characters). By convention, tag name should not begin with 
the underscore `_` as it is reserved for internal uses (like `_item` tags).

#### Inline tags
Inline tags are started with *tag beginning character* and ended by bracket: `{` or `[`. Type of bracket affects the 
processing. Tag contents is everything between its opening bracket and corresponding closing bracket. 
It can spread over several lines, however it is forbidden to open new block tags inside inline tags (but it is possible
to do so with special processing of square brackets, see below).

Brackets (of the same kind) inside the tag should be either balanced or escaped.

For example,

    This is \tag{with some {brackets} inside}
    
is valid markup: the contents of tag `tag` will be `with some {brackets} inside`.

#### Square bracket inline tags
The content of tags with square brackets are processed just like the first line of a block tag.

For example

    Look at \a[Wikipedia, free encyclopedia\href http://ru.wikipedia.org].
    
Is equivalent to

    Look at
    \a
        Wikipedia, free encyclopedia
        \href
            http://ru.wikipedia.org

Another example:

    \ref[Theorem\nonumber|thm:existence]
    
Is equivalent to
    
    \ref
        \_item 
            Theorem
            \nonumber
        \_item 
            thm:existence
 
There is no difference between block tags and inline tags in terms of resulting tree.

#### Allowed tags
Only those tags are processed that are explicitly *allowed*. There are two sets defined: allowed block tags and allowed inline tags.
The sequences that look like tags but are not in the appropriate set is considered as simple text.

#### Indents and whitespaces
Indent of the first line after the block tag is a *base indent* of this tag. All lines that belong to tag will be stripped 
from the left by the number of leading whitespaces that corresponds to the base indent. The rest of whitespaces will be preserved.

For example:

    \pythoncode
        for i in range(1, 10):
            print(i)

Here the contents of `pythoncode` tag is 

    for i in range(1, 10):
        print(i)

Note four whitespaces before `print`.

If a line has an indent that is less than *base indent*, it MUST be equal to the indent of one of open block tags. Than 
all the tags up to that one (including that one) will be closed.

For example, the following is forbidden:

    \code
        some string with indent 4
      some string with indent 2

It is possible to use any indent values but multiples of 4 are recommended (like [PEP-8](https://www.python.org/dev/peps/pep-0008/)).
