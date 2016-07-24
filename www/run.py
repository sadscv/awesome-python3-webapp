import asyncio
from app import create_server

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_server(loop, 'config'))
    loop.run_forever()