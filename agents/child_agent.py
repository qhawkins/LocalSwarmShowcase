from agents.base_agent import BaseAgent
import json

class ChildAgent(BaseAgent):
    def __init__(self, name: str, engine: str, agent_type: str, api_key: str, memory, prompt: str, description: str, tools: json):
        super().__init__(name, engine, agent_type, api_key, memory)
        self.prompt = prompt
        self.description = description
        self.tools = tools

    async def create_own_agent(self, name: str):
        print(f'Creating {name} child agent with prompt: {self.prompt}')
        await self.shared_memory.register_agent(name, {"agent_info":{"description": self.description, "status": "create_agent"}, "agent_class": self}, agent_class=self)
        self.agent = await self.client.beta.assistants.create(model=self.engine, name=name, tools=self.tools, instructions=self.prompt)

    async def run_function(self, retrieved):
        message = retrieved['required_action']['submit_tool_outputs']['tool_calls']
        tool_list = []
        run_id = retrieved['id']
        thread_id = retrieved['thread_id']
        for elem in message:
            print(elem['function']['name'])
            tool_id = elem['id']
            arguments = json.loads(elem['function']['arguments'].replace(r"\n", "").replace(r"\t", "").replace(r"\'", ""))
            
            if elem['function']['name'] == 'prompt_user':
                response = self.prompt_user(prompt_to_user=arguments['prompt_to_user'])
                print(response)

            else:
                response = 'No response, invalid function'
                print(response)
                
            tool_list.append({'tool_call_id': str(tool_id), 'output': str(response)})
            
        return tool_list, run_id, thread_id