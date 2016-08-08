import asyncio
from app import create_server

'''
before python execute the following code,it will initilize  several virables. one of which is called __name__
if python is ruuning this module as the main program, the __name__ will be set as '__main__'
otherwise , it will be set as  the module's name

 so we check the __name__ virable in order to make sure that you want run to this module as a program
'''
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_server(loop, 'config'))
    loop.run_forever()