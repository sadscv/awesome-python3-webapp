from .frame import get
from .frame.halper import Page, set_valid_value, markdown_highlight
from .models import Blog
@get('/test')
async def test():
    return {
        '__template__' : 'test.html',
    }

@get('/')
async def index():
    return 'redirect:/uk/'

@get('/{template}/')
async def home(template, *, page='1', size='10'):
    num = await Blog.countRows()
    page = Page(num, set_valid_value(page), set_valid_value(size, 10))
    if num == 0:
        blogs = []
    else:
        blogs = await Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
    for blog in blogs:
        blog.content = markdown_highlight(blog.content)
    return {
        # '__template__' : '%s-blogs.html' % (template),
        '__template__' : 'uk-blogs.html',
        'blogs' : blogs,
        'page' : page
    }

@get('/{template}/register')
def register(template):
    return {
        # '__template__' : 'uk-register.html' % (template)
        '__template__' : 'uk-register.html',
    }

@get('/{template}/signin')
def signin(template):
    return{
        # '__template__' : 'uk-signin.html' % (template)
        '__template__' : 'uk-signin.html'
    }

@get('/{template}/blog/{id}')
async def get_blog(template, id):
    blog = await Blog.find(id)
    blog.content = markdown_highlight(blog.content)
    return {
        '__template__' : 'uk-blog.html',
        # '__template__' : 'uk-blog.html' % (template),
        'blog' : blog
    }

@get('/{template}/manage')
def manage(template):
    return 'redirect:/uk/manage/blogs',
    # return 'redirect:/uk/manage/blogs' % (template)

@get('/{template}/manage/{table}')
def manage_table(template, table):
    return {
        '__template__' : 'uk-manage.html',
        # '__template__' : 'uk-manage.html' % (template),
        'table' : table
    }

@get('/{template}/manage/blogs/create')
def manage_create_blog(template):
    return{
        '__template__' : 'uk-blog_edit.html'
        # '__template__' : 'uk-blog_edit.html' % (template)
    }

@get('/{template}/manage/blogs/edit')
def manage_edit_blog(template):
    return {
        '__template__' : 'uk-blog_edit.html',
        # '__template__' : 'uk-blog_edit.html' % (template)
    }