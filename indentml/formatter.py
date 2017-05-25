from indentml.parser import QqTag, QqParser
import inspect
import re

class QqFormatter(object):
    """
    This is basic formatter class. Custom formatters can inherit from it.
    """

    def __init__(self, root: QqTag=None, allowed_tags=None):
        self.root = root
        self.allowed_tags = allowed_tags or set()

    def uses_tags(self):
        members = inspect.getmembers(self, predicate=inspect.ismethod)
        handles = [member for member in members
                   if member[0].startswith("handle_") or
                   member[0] == 'preprocess']
        alltags = set([])
        for handle in handles:
            if handle[0].startswith("handle_"):
                alltags.add(handle[0][len("handle_"):])
            doc = handle[1].__doc__
            if not doc:
                continue
            for line in doc.splitlines():
                m = re.search(r"Uses tags:(.+)", line)
                if m:
                    tags = m.group(1).split(",")
                    tags = [tag.strip() for tag in tags]
                    alltags.update(tags)
        return alltags

    def format(self, content) -> str:
        """
        :param content: could be QqTag or any iterable of QqTags
        :param blanks_to_pars: use blanks_to_pars (True or False)
        :return: str: text of tag
        """
        if content is None:
            return ""

        out = []

        for child in content:
            if isinstance(child, str):
                out.append(child)
            else:
                out.append(self.handle(child))
        return "".join(out)

    def handle(self, tag):
        name = tag.name
        tag_handler = 'handle_'+name
        if hasattr(self, tag_handler):
            return getattr(self, tag_handler)(tag)
        elif hasattr(self, 'handle__fallback'):
            return self.handle__fallback(tag)
        else:
            return ""

    def do_format(self):
        return self.format(self.root)

class DummyXMLFormatter(QqFormatter):
    def handle__fallback(self, tag):
        return "<{name}>{content}</{name}>".format(
            name=tag.name, content=self.format(tag)
        )

def parse_and_format(doc: str,
                     formatter_factory,
                     allowed_tags = None) -> str:
    formatter = formatter_factory()
    if allowed_tags is None:
        allowed_tags = formatter.uses_tags()

    parser = QqParser(allowed_tags=allowed_tags)

    tree = parser.parse(doc)
    formatter.root = tree

    return formatter.do_format()