from .frame import get
from app.frame.halper import Page, set_valid_value, markdown_highlight
from .models import Blog
@get('/test')
async def test():
    return {
        '__template__' : 'test.html',
    }

@get('/')
async def index():
    return 'redirect:/bootstrap/'

@get('/{template}/')
async def home(template, *, page='1', size='10'):
    num = await Blog.countRows()
    page = Page(num, set_valid_value(page), set_valid_value(size, 10))

