# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)


import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'qqmbr'))

from ml import QqTag, QqParser
# from qqmbr.indexedlist import IndexedList

import unittest

class TestQqTagMethods(unittest.TestCase):
    def test_create_qqtag(self):
        q = QqTag({'a': 'b'})
        self.assertEqual(q.name, 'a')
        self.assertEqual(q.value, 'b')

        q = QqTag('a', [
            QqTag('b', 'hello'),
            QqTag('c', 'world'),
            QqTag('b', 'this'),
            QqTag('--+-', [
                QqTag('b', 'way'),
                "this"
            ])])

        self.assertEqual(q.name, 'a')
        # self.assertEqual(q._children, IndexedList([QqTag('b', ['hello']), QqTag('c', ['world']), QqTag('b', ['this']),
        #                                           QqTag('--+-', [QqTag('b', ['way']), 'this'])]))
        # self.assertEqual(eval(repr(q)), q)
        self.assertEqual(q.as_list(),
                         ['a', ['b', 'hello'], ['c', 'world'],
                          ['b', 'this'], ['--+-', ['b', 'way'], 'this']])

    def test_qqtag_accessors(self):
        q = QqTag('a', [
            QqTag('b', 'hello'),
            QqTag('c', 'world'),
            QqTag('b', 'this'),
            QqTag('--+-', [
                QqTag('b', 'way'),
                "this"
            ])])

        self.assertEqual(q._b.value, 'hello')
        self.assertEqual(q._c.value, 'world')
        self.assertEqual([b.as_list() for b in q('b')], [['b', 'hello'],
                                                         ['b', 'this']])
        self.assertEqual(q.find('--+-')._b.value, 'way')
        self.assertEqual(q[0].value, 'hello')
        self.assertEqual(q[1].value, 'world')
        self.assertEqual(q[3][0].value, 'way')

    def test_qqtag_backlinks(self):
        q = QqTag('a', [
            QqTag('b', 'hello'),
            QqTag('c', 'world'),
            QqTag('b', 'this'),
            QqTag('--+-', [
                QqTag('b', 'way'),
                "this"
            ])])
        self.assertTrue(q._is_consistent())
        new_tag = QqTag({'qqq' : 'bbb'})
        q.append_child(new_tag)
        self.assertEqual(new_tag.index, 4)
        del q[0]
        self.assertEqual(new_tag.index, 3)
        self.assertTrue(q._is_consistent())

        other_tag = QqTag({'other': ['some', 'values']})
        q.insert(2, other_tag)
        self.assertEqual(other_tag.index, 2)
        self.assertEqual(new_tag.index, 4)

        third_tag = QqTag({'this': 'hi'})
        q[3] = third_tag
        self.assertEqual(third_tag.index, 3)
        self.assertTrue(q._is_consistent())

    def test_qqtag_prev_next(self):
        q = QqTag('a', [
            QqTag('b', 'hello'),
            QqTag('c', 'world'),
            QqTag('b', 'this'),
            QqTag('--+-', [
                QqTag('b', 'way'),
                "this"
            ])])

        self.assertEqual(q._c.prev().value, 'hello')
        self.assertEqual(q._b.next().value, 'world')
        self.assertEqual(q._c.next().value, 'this')


class TestQqParser(unittest.TestCase):
    def test_block_tags1(self):
        doc = r"""Hello
\tag
    World
"""
        parser = QqParser(allowed_tags={'tag'})
        tree = parser.parse(doc)
        self.assertEqual(tree[0], "Hello\n")

        self.assertEqual(tree._tag.name, 'tag')
        self.assertEqual(tree._tag.value, 'World')

    def test_block_tags_nested(self):
        doc = r"""Hello
\tag
    World
    \othertag
        This
        Is
    A test
The end

Blank line before the end
"""
        parser = QqParser(allowed_tags={'tag', 'othertag'})
        tree = parser.parse(doc)
        self.assertEqual(tree[0], "Hello\n")
        self.assertEqual(tree._tag[0], "World\n")
        self.assertEqual(tree._tag._othertag._children, ["This\nIs\n"])
        self.assertEqual(tree._tag[2], 'A test\n')
        self.assertEqual(tree[2], 'The end\n\nBlank line before the end\n')
        self.assertEqual(tree._tag.parent, tree)
        self.assertEqual(tree._tag._othertag.parent, tree._tag)

    def test_block_additional_indent(self):
        doc = r"""Hello
\tag
    First
        Second
    Third
End"""
        parser = QqParser(allowed_tags={'tag'})
        tree = parser.parse(doc)
        self.assertEqual(tree._tag._children,
                         ['First\n    Second\nThird\n'])

    def test_inline_tag1(self):
        doc = r"""Hello, \tag{inline} tag!
"""
        parser = QqParser(allowed_tags={'tag'})
        tree = parser.parse(doc)
        self.assertEqual(tree[0], 'Hello, ')
        self.assertEqual(tree._tag.value, 'inline')
        self.assertEqual(tree[2], ' tag!\n')

    def test_inline_tag2(self):
        doc = r"""Hello, \othertag{\tag{inline} tag}!
"""
        parser = QqParser(allowed_tags={'tag', 'othertag'})
        tree = parser.parse(doc)
       # self.assertEqual(tree._othertag._tag.value, 'inline')
        self.assertEqual(tree.as_list(), ['_root', 'Hello, ',
                                          ['othertag', ['tag', 'inline'],
                                           ' tag'], '!\n'])

    def test_inline_tag3(self):
        doc = r"""Hello, \tag{
this is a continuation of inline tag on the next line

the next one\othertag{okay}}
"""
        parser = QqParser(allowed_tags={'tag', 'othertag'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(), [
            '_root', 'Hello, ',
            [
                'tag',
                ('\nthis is a continuation of inline tag on the next line'
                 '\n\nthe next one'),
                [
                    'othertag',
                    'okay'
                ]
            ],
            '\n'
        ])

    def test_inline_tag4(self):
        doc = r"Hello, \tag{I'm [your{taggy}] tag} okay"
        parser = QqParser(allowed_tags={'tag', 'othertag'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(), [
            '_root', 'Hello, ',
            [
                'tag',
                "I'm [your{taggy}] tag"
            ],
            " okay"
        ])

    def test_block_and_inline_tags(self):
        doc = r"""Hello,
\tag
    I'm your \othertag{tag}
    \tag
        {
        \tag
            {
            this \tag{is a {a test}
            okay}
        }
    }
"""
        parser = QqParser(allowed_tags={'tag', 'othertag'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(), [
            '_root', 'Hello,\n',
            [
                'tag',
                "I'm your ",
                ['othertag', 'tag'],
                '\n',
                [
                    'tag',
                    '{\n',
                    [
                        'tag',
                        '{\nthis ',
                        [
                            'tag',
                            'is a {a test}\nokay',
                        ],
                        '\n'
                    ],
                    '}\n'
                ],
                '}\n'
            ]
        ])

    def test_sameline_tags(self):
        self.maxDiff = None
        doc = r"""    Hello!
    \h1 Intro to qqmbr

    \h2 Fresh documentation system

    **qqmbr** is a documentation system intended to be extremely simple and extremely extensible.
    It was written to allow writing rich content that can be compiled into different formats.
    One source, multiple media: HTML, XML, LaTeX, PDF, eBooks, any other. Look below to see it in action.

    \h3 This is nice level-3 header

    Some paragraph text. See also \ref{sec:another} (reference to different header).

    There are LaTeX formulas here:

    \eq
        x^2 + y^2 = z^2

    `\eq` is a qqtag. It is better than tag, because it is auto-closing (look at the indent, like Python).

    Here is formula with the label:

    \equation \label eq:Fermat
        x^n + y^n = z^n, \quad n>2

    Several formulas with labels:

    \gather
        \item \label eq:2x2
            2\times 2 = 4
        \item \label eq:3x3
            3\times 3 = 9

    We can reference formula \eqref{eq:Fermat} and \eqref{eq:2x2} just like we referenced header before.

    \h3 Another level-3 header \label sec:another

    Here is the header we referenced.

    \h3 More interesting content

    \figure
        \source http://example.com/somefig.png
        \caption Some figure
        \width 500px

    \question
        Do you like qqmbr?
        \quiz
            \choice \correct false
                No.
                \comment You didn't even try!
            \choice \correct true
                Yes, i like it very much!
                \comment And so do I!
"""
        parser = QqParser(allowed_tags={'h1', 'h2', 'h3', 'eq', 'equation', 'label',
                                        'gather', 'inlne', 'item', 'ref', 'eqref',
                                        'source', 'caption', 'width', 'question', 'quiz', 'choice',
                                        'comment', 'correct', 'figure'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(), ['_root',
 'Hello!\n',
 ['h1', 'Intro to qqmbr\n\n'],
 ['h2', 'Fresh documentation system\n\n'],
 '**qqmbr** is a documentation system intended to be extremely simple and extremely extensible.\nIt was written to allow writing rich content that can be compiled into different formats.\nOne source, multiple media: HTML, XML, LaTeX, PDF, eBooks, any other. Look below to see it in action.\n\n',
 ['h3', 'This is nice level-3 header\n\n'],
 'Some paragraph text. See also ',
 ['ref', 'sec:another'],
 ' (reference to different header).\n\nThere are LaTeX formulas here:\n\n',
 ['eq', 'x^2 + y^2 = z^2\n\n'],
 '`\\eq` is a qqtag. It is better than tag, because it is auto-closing (look at the indent, like Python).\n\nHere is formula with the label:\n\n',
 ['equation', ['label', 'eq:Fermat\n'], 'x^n + y^n = z^n, \\quad n>2\n\n'],
 'Several formulas with labels:\n\n',
 ['gather',
  ['item', ['label', 'eq:2x2\n'], '2\\times 2 = 4\n'],
  ['item', ['label', 'eq:3x3\n'], '3\\times 3 = 9\n\n']],
 'We can reference formula ',
 ['eqref', 'eq:Fermat'],
 ' and ',
 ['eqref', 'eq:2x2'],
 ' just like we referenced header before.\n\n',
 ['h3', 'Another level-3 header ', ['label', 'sec:another\n\n']],
 'Here is the header we referenced.\n\n',
 ['h3', 'More interesting content\n\n'],
 ['figure',
  ['source', 'http://example.com/somefig.png\n'],
  ['caption', 'Some figure\n'],
  ['width', '500px\n\n']],
 ['question',
  'Do you like qqmbr?\n',
  ['quiz',
   ['choice',
    ['correct', 'false\n'],
    'No.\n',
    ['comment', "You didn't even try!\n"]],
   ['choice',
    ['correct', 'true\n'],
    'Yes, i like it very much!\n',
    ['comment', 'And so do I!\n']]]]])

    def test_inline_tag_at_the_beginning_of_the_line(self):
        doc = r"""\tag
    some content here here and here and we have some inline
    \tag{here and \othertag{there}}
    """
        parser = QqParser(allowed_tags={'tag', 'othertag'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(), ['_root', ['tag','some content here here and here and we have some inline\n',
                                          ['tag', 'here and ',['othertag', 'there']],'\n']])


    def test_alias2tag(self):
        doc = r"""\# Heading 1
\## Heading 2
Hello
"""
        parser = QqParser(allowed_tags={'h1', 'h2'}, alias2tag={"#": 'h1', "##": 'h2'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(), ["_root", ["h1", "Heading 1\n"], ["h2", "Heading 2\n"], "Hello\n"])

    def test_split_line_by_tags(self):
        doc = r"""something \subtag other | this \is \a \test"""

        parser = QqParser(allowed_tags={'subtag', 'this', 'is', 'a', 'test'})

        self.assertEqual(parser.split_line_by_tags(doc), ['something ', r'\subtag other ', r'\separator', r'this ',
                                                            r'\is ', r'\a ', r'\test']
                         )

    def test_special_inline_mode(self):
        doc = r"""\blocktag
    Some \inlinetag[started
    and here \otherinlinetag{continued}
    here \otherblocktag started
    and here two lines | separated from each other
    and that's all for inlinetag] we continue
"""
        parser = QqParser(allowed_tags={'blocktag', 'inlinetag', 'otherinlinetag', 'otherblocktag', 'separator'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(),
                         ['_root',
                          ['blocktag',
                           'Some ',
                           ['inlinetag',
                            ["_item", 'started\nand here ',
                             ['otherinlinetag', 'continued'],
                             '\nhere ',
                             ['otherblocktag',
                              'started\nand here two lines ',
                              ]],
                           ["_item", 'separated from each other\nand that\'s all for inlinetag'
                            ]],
                           ' we continue\n'
                           ]
                         ]
                         )

    def test_empty_special_tag(self):
        doc = r"""\blocktag
    Some \empty[

    ] tag
"""
        parser = QqParser(allowed_tags={'blocktag', 'empty'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(),["_root", ['blocktag', 'Some ', ['empty'], ' tag\n']])

    def test_non_allowed_tag_with_bracket(self):
        doc = r"""Hello \inlinetag{some \forbiddentag{here} okay} this"""
        parser = QqParser(allowed_tags={'inlinetag'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(), ["_root", "Hello ", ["inlinetag", "some \\forbiddentag{here} okay"], " this"])

    def test_process_separator_recursively(self):
        doc = r"""\splittedtag[one|two\three|four]"""
        parser = QqParser(allowed_tags={'splittedtag', 'three'})
        tree = parser.parse(doc)

        self.assertEqual(tree.as_list(),
                         ['_root',
                           ['splittedtag',
                            ['_item', 'one'],
                            ['_item', 'two', ['three']],
                            ['_item', 'four']]])

    def test_escape_unescape(self):
        doc = r"""Hello
    \sometag test
    \\sometag test
    \sometag
        \ here we are
        we are here
    some \inline{tag with \{ curve bracket inside} okay
    some \inline[square bracket \[ inside] okay
    """
        parser = QqParser(allowed_tags={'sometag', 'inline'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(), [
            "_root", "Hello\n",
            ["sometag", "test\n"],
            "\\sometag test\n",
            ["sometag", " here we are\nwe are here\n"],
            "some ",
            ["inline", "tag with { curve bracket inside"],
            " okay\nsome ",
            ["inline", "square bracket [ inside"],
            " okay\n"
        ])




