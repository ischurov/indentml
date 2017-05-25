# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'indentml'))

from formatter import DummyXMLFormatter, parse_and_format
from textwrap import dedent

import unittest


class TestDummyXMLFormatter(unittest.TestCase):
    def test_dummy_xml_formatter1(self):
        doc = dedent(r"""
                        \tag
                            Hello
                            \othertag
                                I'm indentml
                            How are you?
                        I'm fine""")

        obtained = parse_and_format(doc, DummyXMLFormatter,
                                    allowed_tags={'tag', 'othertag'})
        expected = dedent("""
                            <tag>Hello
                            <othertag>I'm indentml
                            </othertag>How are you?
                            </tag>I'm fine""")

        self.assertEqual(obtained, expected)

    def test_dummy_xml_formatter2(self):
        doc = dedent(r"""
                \image \src http://example.com \width 100%
                    Some image""")
        obtained = parse_and_format(doc, DummyXMLFormatter,
                                    allowed_tags={'image', 'src', 'width'})
        expected = dedent(r"""
                        <image><src>http://example.com </src><width>100%
                        </width>Some image</image>""")
        self.assertEqual(obtained, expected)
