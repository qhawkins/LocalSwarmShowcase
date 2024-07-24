from agents.base_agent import BaseAgent
from agents.child_agent import ChildAgent

import json
import time

class AgentSpawner(BaseAgent):
    def __init__(self, name: str, engine: str, agent_type: str, api_key: str, memory, prompt: str):
        self.child_agent_tools = json.load(open('tools/child_agent_tools.json'))
        self.own_prompt = prompt
        super().__init__(name, engine, agent_type, api_key, memory)
        
    async def create_own_agent(self, name: str):
        print(f'Creating {name} spawner agent with prompt: {self.own_prompt}')
        await self.shared_memory.register_agent(name, {"agent_info":{"description": "no description", "status": "create_agent"}, "agent_class": self}, agent_class=self)
        self.agent = await self.client.beta.assistants.create(model=self.engine, name=name, tools=self.child_agent_tools, instructions=self.own_prompt)


    async def create_child_agent(self, agent_name, agent_prompt, agent_description):
        
        print(f'Creating child agent: {agent_name}')
        agent_class = ChildAgent(name=agent_name, engine=self.engine, agent_type=agent_name, api_key=self.client.api_key, memory=self.shared_memory, prompt=agent_prompt, description=agent_description, tools=self.child_agent_tools)
        await agent_class.create_own_agent(agent_name)


    async def run_function(self, retrieved):
        message = retrieved['required_action']['submit_tool_outputs']['tool_calls']
        tool_list = []
        run_id = retrieved['id']
        thread_id = retrieved['thread_id']
        for elem in message:
            print(elem['function']['name'])
            time.sleep(1)    
            tool_id = elem['id']
            arguments = json.loads(elem['function']['arguments'].replace(r"\n", "").replace(r"\t", "").replace(r"\'", ""))
        
            if elem['function']['name'] == 'create_child_agent':
                response = await self.create_child_agent(agent_name=arguments['agent_name'], agent_prompt=arguments['agent_prompt'], agent_description=arguments['agent_description'])
                print(response)
            
            elif elem['function']['name'] == 'create_agent_conversation':
                response = await self.shared_memory.create_agent_conversation(agent_names=arguments['agent_names'])
                print(response)
            
            elif elem['function']['name'] == 'add_chat_to_conversation':
                response = await self.shared_memory.add_chat_to_conversation(conversation_id=arguments['conversation_id'], agent_name=arguments['agent_name'], chat=arguments['chat'])
                print(response)

            elif elem['function']['name'] == 'get_conversation':
                response = await self.shared_memory.get_conversation(conversation_id=arguments['conversation_id'])
                print(response)
            
            else:
                response = 'No response, invalid function'
                print(response)
                exit()
                
            tool_list.append({'tool_call_id': str(tool_id), 'output': str(response)})
            
        return tool_list, run_id, thread_id

