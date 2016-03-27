import orm
from models import User, Blog, Comment

def test()
	yield from orm.create_pool(user = 'www-data', password = 'www-data', database = 'awesome')
	
	u = User(name = 'Test', email = 'test@example.com', passwd = '123456', image = 'about:blank')
	
	yield from u.save()
	
	
for x ion test():
	pass