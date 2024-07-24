from openai import AsyncOpenAI
import time
import asyncio
import json

class MemoryAgent:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MemoryAgent, cls).__new__(cls)
            # __init__ will be called automatically after __new__
        return cls._instance

    def __init__(self, name: str, engine: str, agent_type: str, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.thread = None
        self.run = None
        self.name = name
        self.agent_type = agent_type
        self.engine = engine
        self.file_dict = {}
        self.active_agents = {}
        self.context = []
        self.summarized = {}
        self.ledger = {}
        self.agent_conversations = {}
        self.lock = asyncio.Lock()  # Add a lock for asynchronous operations
        self.conversation_ids = [0]
        asyncio.gather(self.create_own_agent(name=self.name))
        self.status = "active"

    #prompt user function
    def prompt_user(self, prompt_to_user: str):
        return input(prompt_to_user)
  
    def agent_status(self):
        return self.status
    

    async def check_agent_status(self, target):
        agent_obj = await self.ledger_get_agent(target)
        agent_obj = agent_obj["agent_class"]
        return agent_obj.agent_status()

    #create instance of main agent
    async def create_own_agent(self, name: str):
        print(f'registering {name}')
        agent_name = await self.register_agent(agent_name=name, agent_info={"description": "no description", "status": "create_agent"}, agent_class=self)
        print(f'Creating {agent_name}')
        self.agent = await self.client.beta.assistants.create(model=self.engine, name=agent_name, tools=self.load_tools(f'tools/{self.agent_type}.json'), instructions=self.load_prompt(f'prompts/{self.agent_type}.txt'))

    #create async method to communicate between multiple agents, need to be able to retrieve the objects of every agent from the ledger for this to work
    async def create_agent_conversation(self, agent_names: list):
        async with self.lock:
            self.conversation_ids.append(self.conversation_ids[-1]+1)
            self.agent_conversations[self.conversation_ids[-1]] = {"chat":[], "participants": agent_names}
        return f"Conversation created successfully, chat ID is: {self.conversation_ids[-1]}"
        
    #add chat to conversation
    async def add_chat_to_conversation(self, conversation_id: int, agent_name: str, chat: str):
        async with self.lock:
            print(f'Adding chat to conversation {conversation_id}')
            print(f'Chat: {chat}')
            print(f"Dictionary: {self.agent_conversations}")
            print(self.agent_conversations.keys())
            self.agent_conversations[int(conversation_id)]["chat"].append({agent_name: chat})

    #retrieve conversation
    async def get_conversation(self, conversation_id: int):
        async with self.lock:
            conversation_id = int(conversation_id)
            print(f'Getting conversation {conversation_id}')
            print(f"Conversation dictionary: {self.agent_conversations}")
            if conversation_id in self.agent_conversations.keys():
                to_model = f'Conversation with ID of {conversation_id}\n\n'
                for chat in self.agent_conversations[conversation_id]["chat"]:
                    for agent, message in chat.items():
                        to_model += f"{agent}: {message}\n"
                
                return to_model
            return None

    #remove conversation
    async def remove_conversation(self, conversation_id: int):
        async with self.lock:
            self.agent_conversations[conversation_id]["chat"] = []

    #method to send conversation to agent (very early implementation)
    async def send_chat_to_agent(self, agent_name: str, conversation_id: int):
        print(f'Sending chat to {agent_name}')
        agent_obj = await self.ledger_get_agent(agent_name)
        agent_obj = agent_obj["agent_class"]
        conversation = await self.get_conversation(conversation_id)
        if agent_obj.agent is None:
            await agent_obj.create_own_agent(agent_name)

        if agent_obj.thread is None:
            await agent_obj.create_own_thread()

        while agent_obj.status == "in_progress":
            time.sleep(.5)
            print(f'{agent_name} model status: {agent_obj.status}')

        await agent_obj.add_own_message("user", conversation)
        await agent_obj.create_own_run()
        
    #method to await the ingestion of a conversation by an agent and return the response
    async def await_agent_completion(self, agent_name: str, conversation_id: int):
        print(f'Awaiting completion of {agent_name}')
        agent_obj = await self.ledger_get_agent(agent_name)
        agent_obj = agent_obj["agent_class"]
        status = "in progress"
        while status != "completed" or status != "failed":
            await asyncio.sleep(.25)
            response, status = await agent_obj.get_response()
            print(f'{agent_name} model status: {status}')
            if status == "completed":
                print(response)
                await self.add_chat_to_conversation(conversation_id=conversation_id, agent_name=agent_name, chat=response)

                return response
            if status == "failed":
                print(f'{agent_name} failed to complete')
                return "Failed!"
            print(f"Agent response: {response}")
        
        return response

    #check for existence of agent in the ledger
    async def ledger_check_for_agent(self, agent_name: str):
        print(f'Checking for {agent_name} in ledger')
        if agent_name in self.active_agents.keys():
            print("True")
            return True
        else:
            print("False")
            return False

    #add agent to ledger
    async def ledger_add_agent(self, agent_name: str, agent_info: dict, agent_class):
        async with self.lock:
            self.active_agents[agent_name] = {"agent_info":agent_info, "agent_class": agent_class}

    #remove agent from ledger
    async def ledger_remove_agent(self, agent_name: str):
        async with self.lock:
            del self.active_agents[agent_name]

    #modify agent in ledger
    async def ledger_modify_agent(self, agent_name: str, agent_info: dict, agent_class):
        async with self.lock:
            self.active_agents[agent_name] = {"agent_info":agent_info, "agent_class": agent_class}

    #get agent from ledger
    async def ledger_get_agent(self, agent_name: str=''):
        if agent_name == (None or ''):
            return None
        return self.active_agents[agent_name]


    '''context needs to be implemented correctly with summarization and lifetime management of agents'''
    
    #async method to check chat length (for summarization call)
    async def context_check_chat_length(self):
        for ids in list(self.agent_conversations.keys()):
            print(f'Checking chat length for conversation {ids}')
            print(f'Chat length: {len(self.agent_conversations[ids]["chat"])}')
            if len(self.agent_conversations[ids]['chat']) > 2:
                print(f'Chat length of {ids} is greater than 2, summarizing conversation...')
                await self.context_summarize_lifetime(ids)
            else:
                continue
        return "all chats summarized successfully"

    #async method to summarize lifetime of agent, needs to be fixed
    '''this method needs to be called by the memory agent when the length of the conversation is above n messages in order to save on context'''
    async def context_summarize_lifetime(self, conversation_id: int):
        full_chat = ''
        for chat in self.agent_conversations[conversation_id]['chat']:
            agent_name = chat.keys()
            agent_chat = chat.values()
            full_chat += f"{agent_name}:\n{agent_chat}\n\n"

        self.agent_conversations[conversation_id]['chat'] = []
            

        print(f'Summarizing conversation {conversation_id}')
        #del self.agent_conversations[conversation_id]
        print(f'Conversation {conversation_id} deleted')
        if self.thread is None:
            print("Creating thread")
            await self.create_own_thread()
        print("Adding message")
        while self.status == "in_progress":
            time.sleep(.5)
        await self.add_own_message("user", "Summarize the following dialogue between agents:"+"\n"+full_chat)
        print("Creating run")
        await self.create_own_run()
        while self.status == "in_progress":
            response, self.status = await self.get_response()
            print(self.status)
            if self.status == "completed":
                await self.create_agent_conversation(agent_names=["main_agent", "memory_agent"])
                await self.add_chat_to_conversation(conversation_id=conversation_id, agent_name="memory_agent", chat=response)

            print("summarization in progress")
        print("Summarization complete")
        #await self.send_chat_to_agent("main_agent", conversation_id)
        #await self.await_agent_completion("main_agent", conversation_id)

    #async method to register agent in ledger
    async def register_agent(self, agent_name: str, agent_info: dict, agent_class):
        print("register agent started")
        print("lock acquired")
        exists = await self.ledger_check_for_agent(agent_name)
        print(f'{agent_name} exists: {exists}')
        
        counter = 1
        while exists:
            #identify integers in self.name and replace them with counter
            agent_name = ''.join([i for i in agent_name if not i.isdigit()]) + str(counter)
            exists = await self.ledger_check_for_agent(agent_name)
            print(f'{agent_name} already exists in ledger')
            counter += 1
        
        await self.ledger_add_agent(agent_name, agent_info, agent_class)
        print(f'{agent_name} created')
        return agent_name

    #async method to load tools for agent
    def load_tools(self, file):
        with open(file, 'r') as f:
            return json.load(f)
    
    #async method to load prompt for agent
    def load_prompt(self, file):
        with open(file, 'r') as f:
            return f.read()

    async def create_own_thread(self):
        self.thread = await self.client.beta.threads.create()
        await self.ledger_modify_agent(self.name, {"agent_info":{"description": "no description", "status": "create_thread"}, "agent_class": self}, agent_class=self)

    #create thread for other agent
    async def create_thread(self, agent_class):
        await agent_class.create_own_thread()
        await self.ledger_modify_agent(self.name, {"agent_info":{"description": "no description", "status": "create_thread"}, "agent_class": agent_class}, agent_class=agent_class)

    #create run for main agent
    async def create_own_run(self):
        print(f'Creating run for {self.name}')
        self.run = await self.client.beta.threads.runs.create(thread_id=self.thread.id, assistant_id=self.agent.id)
        print(f'Run created for {self.name}')
        await self.ledger_modify_agent(self.name, {"agent_info":{"description": "no description", "status": "create_run"}, "agent_class": self}, agent_class=self)

    #create run for other agent
    async def create_run(self, agent_class):
        await agent_class.create_own_run()
        await self.ledger_modify_agent(self.name, {"agent_info":{"description": "no description", "status": "create_run"}, "agent_class": agent_class}, agent_class=agent_class)

    #add message to agent
    async def add_own_message(self, role, message):
        print(f'Adding message to {self.name}')
        while self.status == "in_progress":
            time.sleep(.5)
            print(f'{self.name} model status: {self.status}')
        await self.client.beta.threads.messages.create(thread_id=self.thread.id, role=role, content=message)
        print(f'Message added to {self.name}')
        #messages = await self.retrieve_own_messages()
        #print(f'Messages: {message}')
        #await self.ledger_modify_agent(self.name, {"agent_info":{'description': "no description", "status": "active", "messages": message}, "agent_class": self}, agent_class=self)


    #add message to other agent
    async def add_message(self, agent_class):
        messages = await agent_class.retrieve_own_messages()
        await self.ledger_modify_agent(self.name, {"agent_info":{'description': "no description", "status": "active", "mesages": messages}, "agent_class": agent_class}, agent_class=agent_class)

    #retrieve messages for main agent
    async def retrieve_own_messages(self):
        messages = await self.client.beta.threads.messages.list(thread_id=self.thread.id)
        return messages.model_dump()['data'][0]['content'][-1]['text']['value']

    #retrieve messages for other agent
    async def retrieve_messages(self, agent_class):
        messages = await agent_class.retrieve_own_messages()
        return messages.model_dump()['data']
    
    async def get_response(self):
        while True:
            retrieved = await self.client.beta.threads.runs.retrieve(run_id=self.run.id, thread_id=self.thread.id)
            self.status = retrieved.model_dump()['status']
            print(f'{self.name} model status: {self.status}, (mem agent get response)')
            if self.status == 'completed':
                messages = await self.client.beta.threads.messages.list(
                thread_id=self.thread.id
                )
                #await self.context_append_chat(agent_name=self.name, chat=messages.model_dump()['data'][0]['content'][-1]['text']['value'])
                await self.context_check_chat_length()
                return messages.model_dump()['data'][0]['content'][-1]['text']['value'], "completed"


            elif self.status == 'requires_action':
                #print(retrieved.model_dump().keys())
                tool_list, run_id, thread_id = await self.run_function(retrieved.model_dump())
                #print(f'{name} tool list: {tool_list}')

                await self.client.beta.threads.runs.submit_tool_outputs(run_id=run_id, thread_id=thread_id, tool_outputs=tool_list)
                

            elif self.status == 'failed':
                print(retrieved.model_dump())
                print(f'{self.name} model failed to complete')
                return None, "failed"

            time.sleep(.25)

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
                
            if elem['function']['name'] == 'prompt_user':
                response = self.prompt_user(prompt_to_user=arguments['prompt_to_user'])
                print(response)

            elif elem['function']['name'] == 'get_conversation':
                response = await self.get_conversation(conversation_id=arguments['conversation_id'])
                print(response)
            
            elif elem['function']['name'] == 'add_chat_to_conversation':
                response = await self.add_chat_to_conversation(conversation_id=arguments['conversation_id'], agent_name=arguments['agent_name'], chat=arguments['chat'])
                print(response)

            elif elem['function']['name'] == 'create_agent_conversation':
                response = await self.create_agent_conversation(agent_names=arguments['agent_names'])
                print(response)

            elif elem['function']['name'] == 'remove_conversation':
                response = await self.remove_conversation(conversation_id=arguments['conversation_id'])
                print(response)

            else:
                response = 'No response, invalid function'
                print(response)
                exit()
                
            tool_list.append({'tool_call_id': str(tool_id), 'output': str(response)})
            
        return tool_list, run_id, thread_id
        