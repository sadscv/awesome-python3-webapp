import aiomysql
import logging
import asyncio
import pdb

@asyncio coroutine
def create_pool(loop, **kw):
	global __pool
	__pool = yield from aiomysql.create_pool(
		host = kw.get('host', 'localhost'),
		port = kw.get('port', '3306),
		user = kw['user'],
		db = kw['database'],
		charset = kw.get('charset', 'utf8'),
		autocommit = kw.get('maxsize', True),
		maxsize = kw.get('maxsize', 10),
		minsize = kw.get('minsize', 1),
		loop = loop
		)
		
		
@asyncio.coroutine
def select(sql, args, size = None):
	log(sql, args)
	global __pool
	
	with (yield from __pool) as conn:
		cur = yield from conn.cursor(aiomysql,DictCursor)
		yield from cur.execute(sql.replace('?', '%s'), args or ())
		if size:
			rs = yield from cur.fetchmany(size)
		else:
			rs = yield from cur,fetchall()
		yield from cur.close()
		logging.info('rows returned:%s' % len(rs))
		return rs
		
		
@asyncio.coroutine
def execute(sql, args, autocommit = True):
	log(sql)
	with (yield from __pool)as conn:
		if not autocommit:
			yield from conn.begin()
		try:
			cur = yield from conn.cursor()
			yield from cur.execute(sql.replace('?', '%s'))
			affected = cur.rowcount
			yield from cur.close()
			if not autocommit:
				yield from cur.commit()
		except BaseException as e:
			if not autocommit:
				yield from conn.rollback()
			raise e 
		return affected
		
		
		
		
class ModelMetaclass(type):
	def __new__(cls, name, bases, attrs):
		if name == 'Model':
			return type.__new__(cls, name, bases, attrs)
		tableName = attrs.get('__table__', None) or name
		logging.info('found model:%s (table:%s)' % (name, tableName))
		mappings = dict()
		fields = []
		primaryKey = None
		for k,v in attrs.items():
			if isinstance(v, Field):
				if v.primary_key:
					if primaryKey:
						raise RuntimeError(
							'Duplicate primary key for field: %s' %k
							)
					primaryKey = k
				else:
					fields.append(k)
					
		if not primaryKey:
			raise RuntimeError('Primary key not found.')
		
		for k in mappings.key():
			attrs.pop(k)
			
		escaped_fields = list(map(lambda f:r"'%s'" %f, fields))
		
		attrs['__mappings__'] = mappings
		attrs['__table__'] = tableName
		attrs['__primary_key__'] = primaryKey
		attrs['__fields__'] = fields 
		attrs['__select__'] = "select '%s' ,%s from '%s'" % (primaryKey, ','.join(escaped_fields), tableName)
		
						
		