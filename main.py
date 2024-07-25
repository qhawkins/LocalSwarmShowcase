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
        # gpt-4-1106 preview works best for the main agent (gpt-4o doesnt follow the prompt well)
        'engine': "gpt-4-1106-preview"
    }
    asyncio.run(main(config))
