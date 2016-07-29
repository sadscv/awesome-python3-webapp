import hashlib
import json
import logging
import re
from aiohttp import web

from app import COOKIE_NAME
from .frame import get, post
from .frame.halper import Page, set_valid_value, check_admin, check_string, markdown_highlight
from .frame.errors import APIValueError, APIPermissionError, APIResourceNotFoundError
from .models import User, Blog, Comment
_RE_EMAIL = re.compile(r'^[a-zA-Z0-9\.\-\_]+\@[a-zA-Z0-9\-\_]+(\.[a-zA-Z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')


@post('/register')
async def register(*, name, email, sha1_pw):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not sha1_pw or not _RE_SHA1.match(sha1_pw):
        raise APIValueError('password')
    users = await User.findAll('email = ?', [email])
    if users:
        raise APIValueError('email', 'Email is already in used')
    user = User(name=name.strip(), email=email, password=sha1_pw, image='/static/img/user.png')
    await user.save()
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user.generate_cookie(86400), max_age=86400, httponly=True)
    user.password='******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@post('/authenticate')
async def austhenticate(*, email, sha1_pw):
    if not email:
        raise APIValueError('email', 'Invalid email')
    if not sha1_pw:
        raise APIValueError('password', 'Invalid password')
    users = await User.findAll('email = ?', [email])
    if users is None:
        raise APIValueError('email', 'Email not exist')
    user = users[0]
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(sha1_pw.encode('utf-8'))
    if user.password != sha1.hexdigest():
        raise APIValueError('password', 'Invalid password')
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user.generate_cookie(86400), max_age=86400, httponly=True)
    user.password = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out')
    return r

@get('/api/{table}')
async def api_get_items(table, *, page='1', size='10'):
    models = {'users': User, 'blogs': Blog, 'comments': Comment}
    num = await models[table].countRows()
    page = Page(num, set_valid_value(page), set_valid_value(size, 10))
    if num == 0:
        return dict(page=page, items=[])
    items = await models[table].findAll(orderBy='created_at desc', limit=(page.offset, page.limit + num % page.limit))
    if table == 'users':
        for user in items:
            user.password = '******'
    return dict(page=page, items=items)

@get('/api/blogs/{id}')
async def api_get_blog(id):
    return await Blog.find(id)

@post('/api/blogs')
async  def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    check_string(name=name, summary=summary, content=content)
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    await blog.save()
    return blog

@post('/api/blogs/{id}')
async def api_update_blog(id, request, *, name, summary, content):
    check_admin(request)
    check_string(name=name, summary=summary, content=content)
    blog =await Blog.find(id)
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    await blog.update()
    return blog

@get('/api/blogs/{id}/comments')
async def api_get_blog_comments(id):
    comments = Comment.findAll('blog_id= ? ', [id], orderBy='created_at desc')
    for c in comments:
        c.content = markdown_highlight(c.content)
        return dict(comments=comments)

@post('/api/blogs/{id}/comments')
async def api_create_comment(id, request, *, content, time):
    user = request.__user__
    if user is None:
        raise APIPermissionError('please signin first')
    if not content or not content.strip():
        raise APIValueError('content')
    blog = await Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.lstrip('\n').rstrip())
    await comment.save()
    comments = await Comment.findAll('blog_id = ? and created_at > ?', [id, time], orderBy='created_at desc')
    for c in comments:
        c.content = markdown_highlight(c.content)
    return dict(comments=comments)

@post('/api/{table}/{id}/delete')
async def api_delete_item(table, id, request):
    models = {'blogs': Blog, 'comments': Comment}
    check_admin(request)
    item = await models[table].find(id)
    if item:
        await item.remove()
    else:
        logging.warn('id:%s not exist in %s' % (id, table))
    if table == 'blogs':
        comments = await Comment.findAll('blog_id = ?', [id])
        for c in comments:
            await c.remove()

    return dict(id=id)




































