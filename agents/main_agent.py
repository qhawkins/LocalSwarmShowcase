from openai import AsyncOpenAI
import time
import json
from agents.memory_agent import MemoryAgent
from agents.base_agent import BaseAgent
import asyncio

#from memory_agent import MemoryAgent        

#main agent class
class MainAgent(BaseAgent):
    def __init__(self, name: str, engine: str, agent_type: str, api_key: str, memory: MemoryAgent, description: str):
        super().__init__(name=name, engine=engine, agent_type=agent_type, api_key=api_key, memory=memory, description="Main agent for the swarm")
    
    async def create_agent(self, agent_name: str, agent_type: str, agent_description: str):
        agent = BaseAgent(agent_name, self.engine, agent_type, self.client.api_key, self.shared_memory, agent_description)
        await agent.create_own_agent()
        
        return f"Agent {agent_name} created successfully"

    #run function for agent
    async def run_function(self, retrieved):
        message = retrieved['required_action']['submit_tool_outputs']['tool_calls']
        tool_list = []
        run_id = retrieved['id']
        thread_id = retrieved['thread_id']
        for elem in message:
            print(elem['function']['name'])
            await asyncio.sleep(1)    
            tool_id = elem['id']
            arguments = json.loads(elem['function']['arguments'].replace(r"\n", "").replace(r"\t", "").replace(r"\'", ""))
                
            if elem['function']['name'] == 'prompt_user':
                response = self.prompt_user(prompt_to_user=arguments['prompt_to_user'])
                print(response)
            
            #elif elem['function']['name'] == 'create_agent':
            #    response = await self.create_agent(agent_name=arguments['agent_name'], agent_type=arguments['agent_type'], agent_description=arguments['agent_description'])
            #    print(response)
            
            elif elem['function']['name'] == 'initiate_connection':
                print("Main Agent: Initiating connection")
                response = await self.initiate_connection(target=arguments['target'])
                print(response)

            elif elem['function']['name'] == 'check_agent_status':
                print("Main Agent: Checking agent status")
                response = await self.check_agent_status(target=arguments['target'])
                print(response)

            elif elem['function']['name'] == 'add_agent_message':
                print("Main Agent: Adding agent message")
                response = await self.add_agent_message(agent_name=arguments['agent_name'], message=arguments['message'])
                print(response)

            elif elem['function']['name'] == 'create_run':
                print("Main Agent: Creating run")
                response = await self.create_run(target=arguments['target'], aggregate_messages=arguments['aggregate_messages'], agents=arguments['agents'])
                print(response)

            else:
                response = 'No response, invalid function'
                print(response)
                
            tool_list.append({'tool_call_id': str(tool_id), 'output': str(response)})
            
        return tool_list, run_id, thread_id
        