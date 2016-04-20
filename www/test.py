import orm
import asyncio
from models import User, Blog, Comment

def test(loop):
	yield from orm.create_pool(loop = loop, user = 'root', password = 'sadsad', db = 'awesome')
	
	u = User(name = 'Test', email = 'qiyue6', passwd = '123456', image = 'about:blank')
	
	yield from u.save()
	
	


	
loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
# loop.run_forever()