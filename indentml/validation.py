from indentml.parser import QqParser, QqTag
from typing import Set, Union, List, Dict, Tuple

class TextType(object):
    pass

Text = TextType()
# TODO: how to make singleton?

class Grammar(object):
    def __init__(self, schema: QqTag):
        self.schema = schema
        self.tags = {node.text_content: node for node in schema
                     if node.name == 'tag'}
        self.families = {node.text_content: node for node in schema
                         if node.name == 'family'}
        self.groups = {node.text_content: node for node in schema
                         if node.name == 'group'}

    def allowed(self, node: QqTag) -> Dict[str, QqTag]:
        """
        Finds a list of all tags allowed from tag node

        :param node:
        :return:
        """
        allowed: Dict[str, QqTag] = {}
        for child in node:
            child: QqTag
            name = child.name
            id = child.text_content
            if name == 'tag':
                allowed[id] = child
            elif name == 'inherit':
                pass
                
