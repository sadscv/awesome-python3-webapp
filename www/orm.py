import aiomysql
import logging
import asyncio
import pdb


@asyncio.coroutine
def create_pool(loop, **kw):
	logging.info('create database connection pool...')
	global __pool
	__pool = yield from aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )

	
	
def log(sql, args = ()):
		logging.info('SQL:%s' % sql)
	

@asyncio.coroutine
def select(sql, args, size = None):
	log(sql, args)
	global __pool
	
	
	with (yield from __pool) as conn:
		cur = yield from conn.cursor(aiomysql.DictCursor)
		yield from cur.execute(sql.replace('?', '%s'), args or ())
		if size:
			rs = yield from cur.fetchmany(size)
		else:
			rs = yield from cur.fetchall()
		yield from cur.close()
		logging.info('rows returned:%s' % len(rs))
		return rs
		
		
@asyncio.coroutine
def execute(sql, args):
	log(sql)
	with (yield from __pool) as conn:
		try:
			cur = yield from conn.cursor()
			yield from cur.execute(sql.replace('?', '%s'), args)
			affected = cur.rowcount
			yield from cur.close()
			
		except BaseException as e:
			raise
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
		for k, v in attrs.items():
			if isinstance(v, Field):
				logging.info('found mapping: %s ==> %s' % (k, v))
				mappings[k] = v
				
				if v.primary_key:
					if primaryKey:
						raise RuntimeError(
							'Duplicate primary key for field:%s' % k)
					primaryKey = k
				else:
					fields.append(k)
					
		if not primaryKey:
			raise RuntimeError('Primary key not found')
		
		for k in mappings.keys():
			attrs.pop(k)
		
		escaped_fields = list(map(lambda f: r"`%s`" % f, fields))
		
		attrs['__mappings__'] = mappings # 保存属性和列的映射关系
		attrs['__table__'] = tableName
		attrs['__primary_key__'] = primaryKey # 主键属性名
		attrs['__fields__'] = fields
 
		attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
		attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
		
		return type.__new__(cls, name, bases, attrs)
		
def create_args_string(num):
	L = []
	for n in range(num):
		L.append('?')
	return ','.join(L)
	
	

	
	

class Model(dict, metaclass = ModelMetaclass):
	def __init__(self, **kw):
		super(Model, self).__init__(**kw)
		
	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(
                "'Model' object has no attribute '%s'" % key)
				
	def __setattr__(self, key, value):
		self[key] = value
	
	def getValue(self, key):
		return getattr(self, key, None)
		
	def getValueOrDefault(self, key):
		value =  getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s:%s' % (key, str(value)))
				setattr(self, key, value)
		return value
			
		

	@classmethod
	@asyncio.coroutine
	def findAll(cls, where = None, args = None, **kw):
		sql = [cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
			
		orderBy = kw.get('orderBy', None)
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
			
		limit = kw.get('limit', None)    # mysql中可以使用limit关键字
		if limit is not None:
			sql.append('limit')
			if isinstance(limit, int):   # 如果是int类型则增加占位符
				sql.append('?')
				args.append(limit)
			elif isinstance(limit, tuple) and len(limit) == 2:   # limit可以取2个参数，表示一个范围
				sql.append('?,?')
				args.extend(limit)
			else:       # 其他情况自然是语法问题
				raise ValueError('Invalid limit value: %s' % str(limit))
			# 在原来默认SQL语句后面再添加语句，要加个空格
		
		rs = yield from select(' '.join(sql), args)
		return [cls(**r) for r in rs]
		
	@classmethod
	@asyncio.coroutine
	def findNumber(cls, selectField, where = None, args = None):
		sql = ['select %s _num_ from `%s` % (selectField, cls.__table__)']
		if where:
			sql.append('where')
			sql.append(where)
		rs = yield from select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']
	
	
	@classmethod
	@asyncio.coroutine
	def find (cls, pk):
		rs = yield from select('%s where `%s`=?' % cls.__select__, cls.__primary_key__, [pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])
		
	@asyncio.coroutine
	def save(self):
		args = list(map(self.getValueOrDefault, self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = yield from execute(self.__insert__, args)
		if rows != 1:
			logging.warn(
				'failed to update to primary key: affected rows:%s' % rows)
			
	@asyncio.coroutine
	def remove(self):
		args = [self.getValue(self.__primary_key__)]
		rows = yield from execute(self.__delete__, args)
		if rows != 1:
			logging.warn(
				'failed to remove by primary key: affected rows %s' % rows)
		
		

		
		
		
class Field(object):  # 属性的基类，给其他具体Model类继承

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default 			# 如果存在default，在getValueOrDefault中会被用到

    def __str__(self):  # 直接print的时候定制输出信息为类名和列类型和列名
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        # String一般不作为主键，所以默认False,DDL是数据定义语言，为了配合mysql，所以默认设定为100的长度
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'biginit', primary_key, default)


class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)  # 这个是不能作为主键的对象，所以这里直接就设定成False了		
		
		
		
		
		

			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
			
		