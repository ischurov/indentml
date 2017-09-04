# (c) Ilya V. Schurov, 2016 — 2017
# Available under MIT license (see LICENSE file in the root folder)

from collections import Sequence, MutableSequence, namedtuple
from indentml.indexedlist import IndexedList
import re
from functools import total_ordering
import os

class QqError(Exception):
    pass


class QqTag(MutableSequence):
    """
    QqTag is essentially an IndexedList with name attached. It behaves
    mostly like eTree Element.

    It provides eTree and BeautifulSoup-style navigation over its child:
    - ``tag.find('subtag')`` returns first occurrence of a child with name
      ``subtag``. (Note that in contrast with BeautifulSoup, this is not
      recursive: it searches only through tag's direct childrens.)
    - ``tag._subtag`` is a shortcut for ``tag.find('subtag')``
      (works if ``subtag`` is valid identifier)
    - ``tag.find_all('subtag')`` returns all occurrences of tag with
      name 'subtag'
    - ``tag('subtag')`` is shortcut for ``tag.find_all('subtag')``

    If QqTag has only one child, it is called *simple*. Then its `.value`
    is defined. (Useful for access to property-like subtags.)
    """
    def __init__(self, name, children=None, parent=None, index=None,
                 adopt=False):
        if isinstance(name, dict) and len(name) == 1:
            self.__init__(*list(name.items())[0], parent=parent)
            return

        self.name = name
        self.parent = parent
        self.index = index
        # tag has to know its place in the list of parents children
        # to be able to navigate to previous / next siblings

        self.adopter = adopt
        # tag is called 'adopter' if it does not register itself as
        # a parent of its children
        # TODO: write test for adoption

        if children is None:
            self._children = IndexedList()
        elif (isinstance(children, str) or isinstance(children, int) or
              isinstance(children, float)):
            self._children = IndexedList([children])
        elif isinstance(children, Sequence):
            self._children = IndexedList(children)
        else:
            raise QqError("I don't know what to do with children " +
                          str(children))

        if not adopt:
            for i, child in enumerate(self):
                if isinstance(child, QqTag):
                    child.parent = self
                    child.index = i

    def __repr__(self):
        if self.parent is None:
            return "QqTag(%s, %s)" % (repr(self.name),
                                      repr(self._children))
        else:
            return "QqTag(%s, %s, parent = %s)" % (repr(self.name),
                                                   repr(self._children),
                                                   repr(self.parent.name))

    def __str__(self):
        return "{%s : %s}" % (self.name, self._children)

    def __eq__(self, other):
        if other is None or not isinstance(other, QqTag):
            return False
        return self.as_list() == other.as_list()

    @property
    def is_simple(self):
        """
        Simple tags are those containing only one child
        and it is string
        :return:
        """
        return len(self) == 1 and isinstance(self[0], str)

    @property
    def value(self):
        if self.is_simple:
            return self[0].strip()
        raise QqError(
            "More than one child, value is not defined, QqTag: " +
            str(self))

    @value.setter
    def value(self, value):
        if self.is_simple:
            self[0] = value
        else:
            raise QqError("More than one child, cannot set value")

    def qqkey(self):
        return self.name

    def __getattr__(self, attr):
        if attr[0] == "_":
            return self.find(attr[1:])
        raise AttributeError("Attribute " + attr + " not found")

    def find(self, key):
        """
        Returns direct children with the given key if it exists,
        otherwise returns None
        :param key: key
        :return: QqTag
        """
        if key in self._children._directory:
            return self._children.find(key)

    def find_all(self, key):
        return QqTag("_", self._children.find_all(key), adopt=True)

    def __call__(self, key):
        return self.find_all(key)

    def as_list(self):
        ret = [self.name]
        for child in self:
            if isinstance(child, QqTag):
                ret.append(child.as_list())
            else:
                ret.append(child)
        return ret

    def insert(self, index: int, child) -> None:
        self._children.insert(index, child)
        if not self.adopter and isinstance(child, QqTag):
            # TODO: testme
            child.parent = self
            child.index = index
            for i in range(index+1, len(self)):
                self._children[i].index += 1

    def __delitem__(self, index: int):
        del self._children[index]
        if not self.adopter:
            # TODO: testme
            for i in range(index, len(self)):
                self._children[i].index -= 1

    def append_child(self, child):
        self.insert(len(self), child)

    def _is_consistent(self):
        if self.adopter:
            raise QqError("Adopter cannot be checked for consistency")
        for i, child in enumerate(self):
            if child.parent != self or child.index != i:
                return False
        return True

    def append_line(self, line):
        if line:
            self._children.append(line)

    def __getitem__(self, item):
        return self._children[item]

    def __setitem__(self, index, child):
        self._children[index] = child
        if not self.adopter:
            #TODO testme
            child.parent = self
            child.index = index

    def __iter__(self):
        return iter(self._children)

    def __len__(self):
        return len(self._children)

    @property
    def text_content(self):
        chunk = []
        for child in self:
            if isinstance(child, str):
                chunk.append(child)
        return "".join(chunk)

    def exists(self, key):
        """
        Returns True if a child with given key exists
        :param key:
        :return:
        """
        return key in self._children._directory

    def get(self, key, default_value=None):
        """
        Returns a value of a direct child with a given key.
        If it is does not exists or is not simple, returns default value (default: None)
        :param key: key
        :param default_value: what to return if there is no such key or the corresponding child is ot simple
        :return: the value of a child
        """
        tag = self.find(key)
        if tag and tag.is_simple:
            return tag.value
        else:
            return default_value

    def ancestor_path(self):
        """
        Returns list of ancestors for self.

        Example:

            \tag
                \othertag
                    \thirdtag

        thirdtag.ancestor_path == [thirdtag, othertag, tag, _root]

        :return: list
        """
        tag = self
        path = [tag]
        while tag.parent:
            tag = tag.parent
            path.append(tag)
        return path

    def get_eva(self):
        """
        Returns ancestor which is a direct child of a root

        :return:
        """
        return self.ancestor_path()[-2]

    def next(self):
        if (not self.parent or self.index is None or
                    self.index == len(self.parent) - 1):
            return None
        return self.parent[self.index + 1]

    def prev(self):
        if not self.parent or self.index is None or self.index == 0:
            return None
        return self.parent[self.index - 1]

    def clear(self):
        self._children.clear()

    def extend_children(self, children):
        for child in children:
            self.append_child(child)

    def children_values(self, strings='raise', not_simple='raise'):
        """
        Make a list of .value applied to all children instances

        :param strings: one of 'raise', 'keep', 'none', 'skip'
        :param not_simple: one of 'raise', 'keep', 'none', 'skip'

        What to do if string or not simple tag occurs:
        - 'raise': raise an exception
        - 'keep': keep tags/strings as is
        - 'none': replace with None
        - 'skip': skip this item
        :return: list of strings
        """
        assert strings in ['raise', 'keep', 'none', 'skip']
        assert not_simple in ['raise', 'keep', 'none', 'skip']
        values = []
        for child in self:
            if isinstance(child, str):
                if strings == 'raise':
                    raise QqError(
                        "string does not have value (set strings option"
                        " to 'keep', 'none' or 'skip' to workaround)"
                    )
                if strings == 'keep':
                    values.append(child.strip())
                elif strings == 'none':
                    values.append(None)
                # if strings == 'skip': pass
            else: #  QqTag assumed
                if child.is_simple:
                    values.append(child.value)
                    continue
                # child is not simple
                if not_simple == 'raise':
                    raise QqError(
                        ("Child {} is not simple. Use not_simple option "
                         "to tweak the behavior").format(child))
                if not_simple == 'none':
                    values.append(None)
                if not_simple == 'keep':
                    values.append(child)
                # if not_simple == 'skip': pass
        return values

    @property
    def itemized(self) -> bool:
        """
        Returns True if all children are '_item's
        :return: bool
        """
        return len(self.find_all("_item")) == len(self)

    def itemize(self):
        """
        If self's children are _items, return... #TODO
        :return:
        """
        if self.itemized:
            return self
        return QqTag(self.name, [QqTag("_item", self, adopt=True)])

    def unitemized(self):
        """
        If self is simple (only one child and it is string), return self
        If self's only child is "_item", return it
        :return:
        """
        # TODO testme

        if self.is_simple:
            return self
        if len(self) == 1 and self[0].name == "_item":
            return self[0]
        raise QqError("Can't unitemize tag " + str(self))


    def process_include_tags(self, parser, includedir, follow=True):
        """
        Recursively processes include tags (as defined by parser.include)
        Reads files from includedir

        Does not modify current tag, returns a new one instead

        :param parser:
        :param includedir:
        :param follow: follow include directives in included files
            recursively
        :return: processed tree
        """

        # TODO FIXME Sanity checks for includedir

        newtree = QqTag(self.name)
        for child in self:
            if isinstance(child, str):
                newtree.append_child(child)
            else: # child is QqTag
                if child.name == parser.include:
                    include_path = child.value
                    # FROM: https://www.guyrutenberg.com/2013/12/06/
                    # preventing-directory-traversal-in-python/
                    include_path = os.path.normpath('/' +
                                               include_path).lstrip('/')
                    # END FROM

                    include_parsed = parser.parse_file(
                        os.path.join(includedir, include_path))
                    if follow:
                        include_parsed = (
                            include_parsed.process_include_tags(
                                parser, includedir, follow))
                    newtree.extend_children(include_parsed)
                else:
                    newtree.append(child.process_include_tags(
                        parser, includedir, follow))
        return newtree

def dedent(line, indent):
    if line[:indent] == " " * indent:
        return line[indent:]
    raise QqError("Can't dedent line {} by {}".format(repr(line), indent))

def get_indent(s, empty_to_none=False):
        if not s.strip() and empty_to_none:
            return None
        m = re.match(r'\s*', s)
        beginning = m.group(0)
        if '\t' in beginning:
            raise QqError("No tabs allowed in QqDoc at the beginning of line!")
        m = re.match(r' *', s)
        return len(m.group(0))

@total_ordering
class Position(object):
    def __init__(self, line, offset, lines):
        self.line = line
        self.offset = offset
        self.lines = lines
        if line is None:
            self.line = len(lines)

    def __lt__(self, other):
        return (self.line, self.offset) < (other.line, other.offset)

    def __eq__(self, other):
        return (self.line, self.offset) == (other.line, other.offset)

    def nextchar(self):
        self.offset += 1
        if self.offset >= len(self.lines[self.line]):
            self.nextline()
        return self

    def nextline(self):
        self.offset = 0
        self.line += 1
        return self

    def copy(self):
        return Position(line=self.line,
                        offset=self.offset,
                        lines=self.lines)

    def __str__(self):
        return "Position: line_number: {}, offset: {}, line: {}".format(
            self.line, self.offset, get(self.lines, self.line))

    def __repr__(self):
        return "Position(line={}, offset={})".format(
            self.line, self.offset)

    def lines_before(self, stop):
        pos = self.copy()
        out = []
        while pos < stop:
            out.append(pos.clipped_line(stop))
            pos.nextline()
        return out


    def clipped_line(self, stop):
        """
        Returns line clipped before stop

        :param line_idx:
        :param stop:
        :return:
        """

        if stop.line > self.line:
            inline_stop_offset = None
        else:
            inline_stop_offset = stop.offset
        return self.getline[self.offset:inline_stop_offset]

    @property
    def getline(self):
        return self.lines[self.line]

    @property
    def getchar(self):
        return self.getline[self.offset]

    def get_end_of_line(self):
        return Position(self.line, len(self.getline), self.lines)

def get(s, i, default=None):
    try:
        return s[i]
    except IndexError:
        return default


def first_nonspace_idx(line, start=0, stop=None):
    if stop is None:
        stop = len(line)
    m = re.match(r"\s*", line[start:stop])
    return start + m.end(0)

class QqParser(object):
    """
    General indentml parser.
    """
    def __init__(self, tb_char='\\',
                 allowed_tags=None,
                 allowed_inline_tags=None, alias2tag=None,
                 include='_include'):
        self.tb_char = tb_char
        self.command_regex = re.escape(self.tb_char)
        if allowed_tags is None:
            self.allowed_tags = set([])
        else:
            self.allowed_tags = allowed_tags
        self.tag_regex = r"([^\s\{\[\&" + self.command_regex + "]+)"
        if allowed_inline_tags is None:
            self.allowed_inline_tags = self.allowed_tags
        else:
            self.allowed_inline_tags = allowed_inline_tags
        if alias2tag is None:
            self.alias2tag = {}
        else:
            self.alias2tag = alias2tag
        self.escape_stub = '&_ESCAPE_Thohhe1eieMam6Yo_'
        self.include = include
        self.allowed_tags.add(include)
        self._lines = None
        self._indents = None
        self.blocktag_rc = re.compile(self.command_regex +
                              self.tag_regex +
                              r"(?= |{}|$)".format(self.command_regex))
        self.anytag_rc = re.compile(self.command_regex +
                                    self.tag_regex +
                                    r"(?= |{}|{{|\[|$)".format(
                                        self.command_regex))

    def escape_line(self, s):
        """
        Replaces '\\' and '\ ' with special stub
        :param s: a line
        :return: escaped line
        """
        s = s.replace(self.tb_char * 2, self.escape_stub + 'COMMAND_&')
        s = s.replace(self.tb_char + " ", self.escape_stub + 'SPACE_&')
        s = s.replace(self.tb_char + "{",
                      self.escape_stub + 'OPEN_CURVE_&')
        s = s.replace(self.tb_char + "[",
                      self.escape_stub + 'OPEN_SQUARE_&')
        s = s.replace(self.tb_char + "}",
                      self.escape_stub + 'CLOSE_CURVE_&')
        s = s.replace(self.tb_char + "]",
                      self.escape_stub + 'CLOSE_SQUARE_&')

        return s

    def unescape_line(self, s):
        """
        Replaces special stub's inserted by ``escape_line()``
        with '\' and ' '

        Note: this is **NOT** an inverse of escape_line.

        :param s: a line
        :return: unescaped line
        """
        s = s.replace(self.escape_stub + 'SPACE_&', " ")
        s = s.replace(self.escape_stub + 'COMMAND_&', self.tb_char)
        s = s.replace(self.escape_stub + 'OPEN_CURVE_&', '{')
        s = s.replace(self.escape_stub + 'OPEN_SQUARE_&', '[')
        s = s.replace(self.escape_stub + 'CLOSE_CURVE_&', '}')
        s = s.replace(self.escape_stub + 'CLOSE_SQUARE_&', ']')

        return s

    def position(self, line, offset):
        return Position(line=line, offset=offset, lines=self._lines)

    def parse_init(self, text):
        """
        :param lines:
        :return:
        """
        if isinstance(text, str):
            lines = text.splitlines(keepends=True)
        else:
            lines = text

        lines = [self.escape_line(line) for line in lines]

        self._lines = lines
        self._indents = [get_indent(line, empty_to_none=True) for line in lines]

    def parse(self, lines):
        self.parse_init(lines)
        start = self.position(0, 0)
        stop = self.position(None, 0)
        tags = self.parse_fragment(start, stop,
                                   current_indent=get_indent(
                                       self._lines[0]))
        return QqTag("_root", tags)

    def append_chunk_and_clear(self, tags, chunk):
        joined = "".join(chunk)
        if joined:
            tags.append(self.unescape_line(joined))
        chunk.clear()

    def parse_fragment(self, start, stop, current_indent,
                       merge_lines=False):

        tags = []

        pos = start.copy()
        chunk = []

        while pos < stop:
            # loop invariant: everything before pos is appended to tags
            # or chunk

            line = pos.clipped_line(stop)
            if not line.strip():
                if line and line[-1] == '\n':
                    chunk.append("\n")
                pos.nextline()
                continue
            if pos.offset == 0:
                line = dedent(line, current_indent)
                pos.offset = current_indent
                blockmode = True
            else:
                blockmode = False

            if (not merge_lines and blockmode and line.strip() and
                    line[0] == self.tb_char):
                # possibly block tag line
                m = self.blocktag_rc.match(line)
                if m:
                    tag = m.group(1)
                    tag = self.alias2tag.get(tag, tag)
                    if tag in self.allowed_tags:

                        rest_of_line = line[m.end(1):]
                        spaces = re.match(r"\s*", rest_of_line).end(0)
                        newstart_pos = (current_indent +
                                        first_nonspace_idx(line, m.end(1)))
                        newstop_line, tag_contents_indent = (
                            self.block_tag_stop_line_indent(
                                pos.line, stop.line
                            )
                        )
                        parsed_content = self.parse_fragment(
                            self.position(pos.line, newstart_pos),
                            self.position(newstop_line, 0),
                            tag_contents_indent
                        )
                        self.append_chunk_and_clear(tags, chunk)
                        tags.append(QqTag(tag, children=parsed_content))
                        pos.line = newstop_line
                        pos.offset = 0
                        continue

            tag_position, tag, ttype, after = self.locate_tag(pos, stop)
            if tag is not None:
                chunk.append(pos.clipped_line(tag_position))
                self.append_chunk_and_clear(tags, chunk)
            if ttype == "block":
                next_bt_position, _ = self.scan_after_attribute_tag(
                    after, stop, merge_lines=merge_lines)
                parsed_content = self.parse_fragment(after,
                                                     next_bt_position,
                                                     current_indent)
                tags.append(QqTag(tag, children=parsed_content))
                pos = next_bt_position.copy()
                continue
            if ttype == "inline":
                items = self.inline_tag_contents(after, stop)
                parsed_items = []

                for item in items:
                    parsed_content = self.parse_fragment(
                        item['start'], item['stop'], current_indent,
                        merge_lines=True)
                    if item['type'] == '{':
                        parsed_items.extend(parsed_content)
                    else: # item['type'] == '['
                        parsed_items.append(QqTag("_item",
                                                  children=parsed_content))
                tags.append(QqTag(tag, children=parsed_items))
                pos = items[-1]["stop"].copy().nextchar()
                continue

            chunk.append(line)
            pos.nextline()

        self.append_chunk_and_clear(tags, chunk)
        return tags

    def block_tag_stop_line_indent(self, start_line, stop_line):
        tag_indent = self._indents[start_line]
        if stop_line <= start_line + 1:
            # don't have more lines
            # e.g.
            # \tag rest of line
            # EOF
            # indent is of no importance, so set it to -1
            return start_line + 1, -1

        cur_line = start_line + 1
        while self._indents[cur_line] is None and cur_line < stop_line:
            # skip empty lines
            cur_line += 1
        if cur_line == stop_line:
            # we have only empty lines
            return cur_line, -1

        # we have non-empty line
        contents_indent = self._indents[cur_line]
        if contents_indent <= tag_indent:
            # tag is already closed
            return cur_line, -1

        for i in range(cur_line + 1, stop_line):
            cur_indent = self._indents[i]
            if (cur_indent is not None and
                    cur_indent < contents_indent):
                if cur_indent > tag_indent:
                    raise QqError("Incorrect indent at line: "
                                  + self._lines[i])
                return i, contents_indent
        # processed all lines, no dedent

        return stop_line, contents_indent

    def locate_tag(self, start: Position, stop: Position):
        """
        locates inline or block tag on line
        beginning with given position pos

        does not propogate on the following lines

        :param start: position to start with
        :param stop: position to stop
        :return: (tag_position: Position of first tag character (\\)
                  tag: tag name,
                  type: 'block' or 'inline',
                  after: Position of first non-space character after tag
                    (if it is block tag) or simply first character after
                    tag (if it is inline tag)
        """
        line = start.clipped_line(stop)

        for m in self.anytag_rc.finditer(line):
            tag = m.group(1)
            tag_position = self.position(start.line,
                                         start.offset + m.start(0))
            after = self.position(
                start.line, start.offset +
                first_nonspace_idx(line, m.end(1)))
            next_char = get(line, m.end(1))
            if next_char not in ['{', '[']:
                if tag in self.allowed_tags:
                    return tag_position, tag, 'block', after
            else:
                if tag in self.allowed_inline_tags:
                    return tag_position, tag, 'inline', after
        return min(start.get_end_of_line(), stop), None, None, None

    def inline_tag_contents(self, start: Position, stop: Position):
        """
        Finds the contents of inline tag:

        :param start:
        :param stop:
        :return: a list of dicts {'type': '[' or '{',
                                  'start': Position,
                                  'stop': Position}
        """
        items = []
        pos = start.copy()
        while pos < stop and pos.getchar in ['[', '{']:
            type = pos.getchar
            end = self.match_bracket(pos, stop)
            items.append({'type': type,
                          'start': pos.copy().nextchar(),
                          'stop': end.copy()})
            pos = end
            pos.nextchar()
        return items

    def match_bracket(self, start: Position, stop: Position) -> Position:
        """
        Finds the matching closing bracket
        :param start: start position, its value should be '[' or '{'
        :param stop: stop position
        :return: position of matching closing bracket
        """
        open_bracket = self._lines[start.line][start.offset]
        assert open_bracket in ['[', '{']
        pos = start.copy()
        counter = 0
        # open bracket counter
        closing_bracket = {'[': ']', '{': '}'}[open_bracket]
        bracket_rc = re.compile(re.escape(open_bracket) + "|" +
                                re.escape(closing_bracket))

        while pos < stop:
            line = pos.clipped_line(stop)
            for m in bracket_rc.finditer(line):
                if (self.position(pos.line, pos.offset + m.start(0)) >=
                        stop):
                    raise QqError("No closing bracket found: "
                                  "start: {}, stop: {}".format(start,
                                                               stop))
                if m.group(0) == open_bracket:
                    counter += 1
                else:
                    counter -= 1
                    if counter == 0:
                        return self.position(pos.line,
                                             pos.offset + m.start(0))
            pos.nextline()
        raise QqError("No closing bracket found: " 
                      "start: {}, stop: {}".format(start, stop))

    def scan_after_attribute_tag(self, start: Position,
                                 stop: Position, merge_lines = False):
        """
        scans the rest of line / fragment after block tag found inline
        looking for another block tag
        skipping every inline tag with its contents

        :param start: first character to scan
        :param stop: where to stop
        :return: (Position of the first character of next block tag or EOL,
                  Position of the first non-space character after block tag
                  or None if EOL found)
        """
        if not merge_lines:
            stop = min(stop, start.copy().nextline())
            # looking only for current line

        pos = start.copy()
        ret = start.copy()

        while pos < stop:
            tag_position, tag, type, after = self.locate_tag(pos, stop)
            if tag is None:
                pos.nextline()
                ret = tag_position
                continue
            if type == 'block':
                return tag_position, after
            else:
                contents = self.inline_tag_contents(after, stop)
                pos = contents[-1]['stop'].nextchar()
                ret = min(pos.get_end_of_line(), stop)

        return ret, None

    def parse_file(self, filename):
        with open(filename) as f:
            lines = f.readlines()
        return self.parse(lines)