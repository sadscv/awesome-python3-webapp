import asyncio
import logging

from app.frame.orm import create_pool
from app.models import User
from www.config.orm_test import db_config

async def test():
    await create_pool(loop, **db_config)

    rows = await User.countRows()
    logging.info('rows is :%s' % rows)

    if rows < 2:
        for idx in range(5):
            u = User(
                name='test%s' % (idx),
                email='test%s@orm.org' % (idx),
                password='pw',
                image='/static/img/user.png'
            )
            rows = await User.countRows(where='email =?', args=[u.email])
            if rows == 0:
                await u.save()
            else:
                print('the email was already used')

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
