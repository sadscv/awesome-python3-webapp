import logging
import aiomysql
from .fields import Field

logging.basicConfig(level=logging.INFO)

def log(sql, args=None):
    logging.info('SQL:[%s] args : %s' % (sql, args or []))

async def create_pool(loop, user, password, db, **kw):
    global __pool
    __pool = await aiomysql.create_pool(
        loop=loop,
        user=user,
        password=password,
        db=db,
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1)

    )

async def select(sql, args, size=None):
    log(sql, args)
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args)
            if size:
                resultset = await cur.fetchmany(size)
            else:
                resultset = await cur.fetchall()
        logging.info('rows returned: %s' % len(resultset))
        return resultset


async def execute(sql, args, autocommit=True):
    log(sql, args)
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise e
        return affected


class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        # 忽略父类
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        # 找到表名
        table = attrs.get('__table__', name)
        logging.info('found model: %s (table: %s)' % (name, table))
        # 建立映射关系表和找到主键
        mappings = {}
        escaped_fields = []
        primary_key = None
        for key, val in attrs.copy().items():
            if isinstance(val, Field):
                # 把Field属性类保存在映射映射关系表，并从原属性列表中删除
                mappings[key] = attrs.pop(key)
                logging.info('found mapping: %s ==> %s' % (key, val))
                # 查找并检验主键是否唯一
                if val.primary_key:
                    if primary_key:
                        raise KeyError('Duplicate primary key for field: %s' % key)
                    primary_key = key
                else:
                    escaped_fields.append(key)
        if not primary_key:
            raise KeyError('Primary key not found.')
        # 创建新的类的属性
        attrs['__table__'] = table                            # 保存表名
        attrs['__mappings__'] = mappings                      # 映射关系表
        attrs['__primary_key__'] = primary_key                # 主键属性名
        attrs['__fields__'] = escaped_fields + [primary_key]  # 所有字段名
        # -----------------------默认SQL语句--------------------------
        attrs['__select__'] = 'select * from `%s`' % (table)
        attrs['__insert__'] = 'insert into `%s` (%s) values (%s)' % (table, ', '.join('`%s`' % f for f in mappings), ', '.join('?' * len(mappings)))
        attrs['__update__'] = 'update `%s` set %s where `%s` = ?' % (table, ', '.join('`%s` = ?' % f for f in escaped_fields), primary_key)
        attrs['__delete__'] = 'delete from `%s` where `%s`= ?' % (table, primary_key)

        return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError("'Model' object has no such attr '%s'" % attr)

    def __setattr__(self, attr, value):
        self[attr] = value

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s:%s' % (key, value))
                setattr(self, key, value)
        return value

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        sql = [cls.__select__]
        if args is None:
            args = []
        if where:
            sql.append('where %s' % (where))
        if kw.get('orderBy') is not None:
            sql.append('order by %s' % kw['orderBy'])
        limit = kw.get('limit')
        if kw.get('limit') is not None:
            if isinstance(limit, int):
                sql.append('limit ?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('limit ?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % limit)
        resultset = await select(' '.join(sql), args)
        return [cls(**r) for r in resultset]

    @classmethod
    async def countRows(cls, selectField='*', where=None, args=None):
        sql = ['select count(%s) _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where %s' % (where))
        resultset = await select(' '.join(sql), args, 1)
        if not resultset:
            return 0
        return resultset[0].get('_num_', 0)

    @classmethod
    async def find(cls, pk):
        resultset = await select('%s where `%s` = ?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        return cls(**resultset[0]) if resultset else None

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__mappings__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warning('failed to insert record:affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.get, self.__fields__))
        rows = await execute(self.__update__, args)
        if rows !=1:
            logging.warning('failed to update by primary key:affected rows: %s' % rows)

    async def remove(self):
        args = [self.get(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows !=1:
            logging.warning('remove error')