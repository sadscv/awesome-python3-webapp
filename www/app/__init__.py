import logging
import os
from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from config import COOKIE_NAME, COOKIE_KEY
from .frame import add_routes, add_static
from .frame.orm import create_pool
from .factorys import logger_factory, auth_factory, data_factory, response_factory, datetime_filter

logging.basicConfig(level=logging.INFO)

def init_jinja2(app, **kw):
    logging.info('init jinja2..')
    options = {
        'autoescape': kw.get('autoescape', True),
        'block_start_string': kw.get('block_start_string', '{%'),
        'block_end_string': kw.get('block_end_string', '%}'),
        'variable_start_string': kw.get('variable_start_string', '{{'),
        'variable_end_string': kw.get('variable_end_string', '}}'),
        'auto_reload': kw.get('auto_reload', True)
    }
    path = kw.get('path', os.path.join(__path__[0], 'templates'))
    logging.info('set jinja2 template path:%s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters')
    if filters is not None:
        for name, ftr in filters.items():
            env.filters[name] = ftr
    app['__templating__'] = env


async def create_server(loop, config_mod_name):
    try:
        # python　__import (module, fromlist).
        # here fromlist is useless cuz when python import a module ,it will directly compile the whole module rather than
        #the few functions listed in the 'fromlist'.
        #fromlist make sense when you import a package instead of a  module
        config = __import__(config_mod_name, fromlist=['get config'])
    except ImportError as e:
        raise e

    await create_pool(loop, **config.db_config)
    #a middleware factory is a kind of
    app = web.Application(loop=loop, middlewares=[
        logger_factory, auth_factory, data_factory, response_factory
    ])
    add_routes(app, 'app.route')
    add_routes(app, 'app.api')
    add_static(app)
    init_jinja2(app, filters=dict(datetime=datetime_filter), **config.jinja2_config)
    server = await loop.create_server(app.make_handler(), '127.0.0.1', 9900)
    logging.info('server started at localhost:9900')
    return server
