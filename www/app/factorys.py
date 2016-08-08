import logging
import json
import time
from datetime import datetime
from aiohttp import web
from urllib import parse

from app import COOKIE_NAME
from .models import User

# it returns a new handler
# a little bit different from the decorator.
async  def logger_factory(app, handler):
    async def logger(request):
        logging.info('Response:%s %s' % (request.method, request.path))
        return await handler(request)
    return logger

async def auth_factory(app, handler):
    async def auth(request):
        logging.info('auth_factory...check user: %s %s' % (request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = await User.find_by_cookie(cookie_str)
            if user:
                logging.info('set current user: %s ' % user.email)
                request.__user__ = user
        if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/')
        return await handler(request)
    return auth

async def data_factory(app, handler):
    async def parse_date(request):
        logging.info('data_factory...')
        if request.method == 'POST':
            if not request.content_type:
                return web.HTTPBadRequest(text='Missing Content-Type')
            content_type = request.content_type.lower()
            if content_type.startswith('application/json'):
                request.__data__ = await request.json()
                if not isinstance(request.__data__, dict):
                    return web.HTTPBadRequest(text='JSON body must be object.')
                logging.info('request json: %s' % request.__data__)
            elif content_type.startswith(('application/x-www-form-urlencoded', 'multipart/form-data')):
                params = await request.post()
                request.__data__ = dict(**params)
                logging.info('request form: %s' % request.__data__)
            else:
                return web.HTTPBadRequest(text='Unsupported Content-Type: %s' % content_type)
        elif request.method == 'GET':
            qs = request.query_string
            request.__data__ = {k:v[0] for k, v in parse.parse_qs(qs, True).items()}
            logging.info('request query: %s' % request.__data__)
        else:
            request.__data__ = dict()
        return await handler(request)
    return parse_date


async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o:o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                r['__user__'] = request.__user__
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and 100 <= r < 600:
            return web.Response(status=r)
        if isinstance(r, tuple) and len(r) == 2:
            status, message = r
            if isinstance(status, int) and 100 <= status < 600:
                return web.Response(status=status, text=str(message))

        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return await handler(request)
    return response


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1 min ago'
    if delta < 3600:
        return u'%s min ago' % (delta //60)
    if delta < 86400:
        return u'%s hours ago' % (delta //3600)
    if delta < 604800:
        return u'%s days ago' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)