import asyncio
from modules.swarm import Swarm
import os

async def main(config):
    swarm = Swarm(config)
    await swarm.run()
    while True:
        await asyncio.sleep(1) 


if __name__ == '__main__':
    config = {
        'openai_key': os.environ.get('OPENAIKEY'),
        'engine': "gpt-4o"
    }
    asyncio.run(main(config))
