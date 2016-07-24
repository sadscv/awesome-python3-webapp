import mistune
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from .errors import APIPermissionError, APIValueError

class Page(object):

    def __init__(self, item_count, index=1, size=10):
        self.last = item_count // size + (1 if item_count % size > 0 else 0)
        self.index = min(index, self.last) if item_count > 0 else 1
        self.offset = size * (index - 1)
        self.limit = size

def set_valid_value(num_str, value=1):
    try:
        num = int(num_str)

