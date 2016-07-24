import functools
import hashlib
import time
import uuid
import logging

from . import COOKIE_KEY
from .frame.fields import *
from .frame.orm import Model

StringField = functools.partial(StringField, ddl='varchar(50)')

def next_id():
    return '%015d%s000' % (int(time.time() *1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id)
    email = StringField()
    password = StringField()
    admin = BooleanField()
    name = StringField()
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)

    async def save(self):
        self.id = next_id()
        sha1_pw = '%s:%s' % (self.id, self.password)
        self.password = hashlib.sha1(sha1_pw.encode('utf-8')).hexdigest()
        await super().save()

    def generate_cookie(self, max_age):
        expires = str(int(time.time() + max_age))
        s = '%s-%s-%s-%s' % (self.id, self.password, expires, COOKIE_KEY)
        L = [self.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
        return '-'.join(L)

    @classmethod
    async def find_by_cookie(cls, cookie_str):
        if not cookie_str:
            return None
        try:
            L = cookie_str.split('-')
            if len(L) != 3:
                return None
            uid, expires, sha1 = L
            if int(expires) < time.time():
                return None
            user = await cls.find(uid)
            if user is None:
                return None
            s = '%s-%s-%s-%s' % (uid, user.password, expires, COOKIE_KEY)
            if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
                logging.info('invalid sha1')
                return None
            user.passwd = '******'
            return user
        except Exception as e:
            logging.exception(e)
            return None


class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id)
    user_id = StringField()
    user_name = StringField()
    user_image = StringField(ddl='varchar(500)')
    name = StringField()
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)


class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id)
    blog_id = StringField()
    user_id = StringField()
    user_name = StringField()
    user_image = StringField(ddl='varchar(500)')
    cotent = TextField()
    created_at = FloatField(default=time.time)

