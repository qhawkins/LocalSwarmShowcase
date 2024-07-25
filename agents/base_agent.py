import asyncio
#from BaseLLM import BaseLLM
from modules.VLLM import BaseVLLM
import json
import time
from openai import AsyncOpenAI

class BaseAgent:
    def __init__(self, name: str, engine: str, agent_type: str, api_key: str, memory, description: str):
        self.engine = engine
        if "mixtral" in engine.lower() or "llama" in engine.lower():
            #self.client = BaseLLM(model_id=engine, batch_size=1)
            self.client = BaseVLLM(request_id=name, engine=engine)
        elif "gpt" in engine.lower():
            self.client = AsyncOpenAI(api_key=api_key, timeout=3600)
        else:
            print("Invalid engine")
            exit()
        self.thread = None
        self.run = None
        self.name = name
        self.agent_type = agent_type
        self.file_dict = {}
        self.status = "not created"
        self.description = description
        self.tools = self.load_tools(f'tools/{self.agent_type}.json')
        self.instructions = self.load_prompt(f'prompts/{self.agent_type}.txt')
        asyncio.gather(self.create_own_agent())
        self.lock = asyncio.Lock()
        self.shared_memory = memory
        self.st_memory = []
        self.connected_agents = []
        print(f'Agent {self.name} successfully initialized')

    def prompt_user(self, prompt_to_user: str):
        return input(prompt_to_user)

    def end_chat(self, prompt_to_user: str):
        print(prompt_to_user) 
        return "Chat ended"
     
    def load_tools(self, path):
        with open(path, 'r') as f:
            return json.load(f)
    
    def load_prompt(self, path):
        with open(path, 'r') as f:
            return f.read()

    async def create_own_agent(self):
        print(f'registering {self.name}')
        await self.shared_memory.register_agent(agent_name=self.name, agent_info={"description": self.description, "status": self.status}, agent_class=self)
        if "gpt" in self.engine:
            self.agent = await self.client.beta.assistants.create(model=self.engine, name=self.name, tools=self.tools, instructions=self.instructions)
        else:
            self.agent = "filler, may not be needed"
        
            
        while self.agent is None:
            await asyncio.sleep(.25)
            print(f'Creating {self.name}')
        print(f'Created {self.name}')
        
        if "gpt" in self.engine:
            self.thread = await self.client.beta.threads.create()
        else:
            print("Thread not needed")
        
        while self.thread is None and "gpt" in self.engine:
            await asyncio.sleep(.25)
            print(f'Creating thread')
        print(f'Created thread {self.thread.id}')
        self.status = "ready"
        return f"Agent {self.name} created successfully"
    
    async def create_run(self, target: str, aggregate_messages: bool = False, agents: list = []):
        print(f'Creating run for {target}')
        agent_obj = await self.shared_memory.ledger_get_agent(target)
        agent_obj = agent_obj["agent_class"]
        
        if aggregate_messages is True:
            print(f"Aggregating Messages: {aggregate_messages}")
            await agent_obj.aggregate_messages(agents)

        if "gpt" in self.engine:
            agent_obj.run = await agent_obj.client.beta.threads.runs.create(thread_id=agent_obj.thread.id, assistant_id=agent_obj.agent.id)
        else:
            agent_obj.run = agent_obj.create_run()
        
        while agent_obj.run is None:
            await asyncio.sleep(.25)
            print(f'Creating run')
        
        print(f'Created run {agent_obj.run.id}')
        response, agent_obj.status = await agent_obj.get_response()

        return response, agent_obj.status

    async def aggregate_messages(self, agents: list = []):
        for agent in agents:
            print(f"Aggregating messages for {agent} (am)")
            status = await self.check_agent_status(agent)
            while status != "ready":
                if status == "requires_action" or status == "completed" or status == "failed":
                    break
                print(f"Agent Status: {status} (am)")
                await asyncio.sleep(.25)
                status = await self.check_agent_status(agent)
        for conversation in self.st_memory:
            #async with self.lock:
            print(f"Aggregating message: {conversation}")
            if "gpt" in self.engine:
                await self.client.beta.threads.messages.create(thread_id=self.thread.id, role="user", content=conversation)
            else:
                await self.client.create_message(conversation)
        #async with self.lock:
        self.st_memory = []
        return f"Messages aggregated to {self.name}"

    def agent_status(self):
        return self.status
    
    async def check_agent_statuses(self):
        agent_statuses = []
        for agent in self.connected_agents:
            agent_statuses.append(await self.check_agent_status(agent))
        return agent_statuses

    async def check_agent_status(self, target):
        agent_obj = await self.shared_memory.ledger_get_agent(target)
        agent_obj = agent_obj["agent_class"]
        return agent_obj.agent_status()

    async def initiate_connection(self, target):
        print(f"Initiating connection with {target}")
        agent_obj = await self.shared_memory.ledger_get_agent(target)
        agent_obj = agent_obj["agent_class"]
        #agent_status = await agent_obj.check_agent_status(target)
        #while agent_status != "ready":
        #    await asyncio.sleep(.25)
        #    print(f"Agent Status: {agent_status}")
        #    agent_status = await agent_obj.check_agent_status(self.name)

        print(f'Initiating connection with {target}')
        await agent_obj.add_agent_message(agent_name=self.name, message=f"Connection initiated with {target}")
        self.connected_agents.append(target)
        return f"Connection initiated with {target}"

    async def send_over_connection(self, target, message):
        agent_obj = await self.shared_memory.ledger_get_agent(target)
        agent_obj = agent_obj["agent_class"]
        agent_status = await agent_obj.check_agent_status(target)
        while agent_status != "ready":
            await asyncio.sleep(.25)
            agent_status = await agent_obj.check_agent_status(target)
        print(f'Sending message to {target}')
        await agent_obj.add_message(agent_name=self.name, message=message)
        print(f'Message sent to {target}')

    async def add_agent_message(self, agent_name, message):
        agent_obj = await self.shared_memory.ledger_get_agent(agent_name)
        agent_obj = agent_obj["agent_class"]
        print(f"Agent st memory: {agent_obj.st_memory}")
        async with self.lock:
            agent_obj.st_memory.append(f"Agent Name: {self.name}\n\nMessage: {message}")

        #await self.client.beta.threads.messages.create(thread_id=self.thread.id, role="assistant", content=message)
        return f"Message added to memory of {agent_name}"
    
    async def retrieve_st_memory(self):
        return self.st_memory

    #get response of agent run
    async def get_response(self):
        while True:
            if "gpt" in self.engine:
                retrieved = await self.client.beta.threads.runs.retrieve(run_id=self.run.id, thread_id=self.thread.id)
            else:
                retrieved = self.client.retrieve()
            
            self.status = retrieved.model_dump()['status']
            print(f'{self.name} model status: {self.status}, (mem agent get response)')
            if self.status == 'completed':
                if "gpt" in self.engine:
                    messages = await self.client.beta.threads.messages.list(
                        thread_id=self.thread.id
                    )
                
                else:
                    messages = self.client.list_messages()
                
                
                #await self.shared_memory.context_check_chat_length()
                #with open(f"logs/{self.name}.txt", "w+") as f:
                #    f.write(messages.model_dump()['data'][0]['content'][-1]['text']['value'])
                
                #print(100*'-')

                return messages.model_dump()['data'][0]['content'][-1]['text']['value'], "completed"


            elif self.status == 'requires_action':
                #print(retrieved.model_dump().keys())
                tool_list, run_id, thread_id = await self.run_function(retrieved.model_dump())
                #print(f'{name} tool list: {tool_list}')
                if "gpt" in self.engine:
                    await self.client.beta.threads.runs.submit_tool_outputs(run_id=run_id, thread_id=thread_id, tool_outputs=tool_list)
                else:
                    self.client.create_tool_outputs(tool_list)


            elif self.status == 'failed':
                print(retrieved.model_dump())
                print(f'{self.name} model failed to complete')
                return None, "failed"

            await asyncio.sleep(.25)

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

            elif elem['function']['name'] == 'end_chat':
                response = self.end_chat(prompt_to_user=arguments['prompt_to_user'])
                print(response)
                self.status = "exited"

            elif elem['function']['name'] == 'initiate_connection':
                response = await self.initiate_connection(target=arguments['target'])
                print(response)

            elif elem['function']['name'] == 'check_agent_status':
                response = await self.check_agent_status()
                print(response)
            
            elif elem['function']['name'] == 'create_run':
                response = await self.create_run(target=arguments['target'], aggregate_messages=arguments['aggregate_messages'], agents=arguments['agents'])
                print(response)

            else:
                response = 'No response, invalid function'
                print(response)
                
            tool_list.append({'tool_call_id': str(tool_id), 'output': str(response)})
            
        return tool_list, run_id, thread_id
        