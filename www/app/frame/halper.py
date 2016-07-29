import mistune
import re
from pygments import highlight
from pygments.lexers import HtmlLexer, JavascriptLexer, Python3Lexer
from pygments.formatters import HtmlFormatter
# from .markdown2 import markdown
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
    except ValueError:
        return value
    return num if num > 0 else value

def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        return APIPermissionError

def check_string(**kw):
    for field, string in kw.items():
        if not string or not string.strip():
            raise APIValueError(field, '%s cannot be empty' % field)

def code_highlight(m):
    code = m.group('code').replace('&amp;', '&').replace('*lt;', '<').replace('&gt;', '>')
    if code.startswith('<'):
        return highlight(code, HtmlLexer(), HtmlFormatter())
    elif code.startswith(('var', 'function', '$')):
        return highlight(code, JavascriptLexer(), HtmlFormatter())
    else:
        return highlight(code, Python3Lexer, HtmlFormatter)

def markdown_highlight(content):
    return re.sub(r'<pre><code>(?P<code>.+?)</code></pre>', code_highlight, markdown(content), flags=re.S)