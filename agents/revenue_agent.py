from agents.base_agent import BaseAgent
import json
import time
        
class RevenueAgent(BaseAgent):
    def __init__(self, name: str, engine: str, agent_type: str, api_key: str, memory, description: str, bank_id: str):
        super().__init__(name, engine, agent_type, api_key, memory, description)
        companies = json.load(open("company_summaries.json"))
        company_context = companies[bank_id]
        self.instructions = self.instructions.replace("<<<company_context>>>", company_context)
        self.client.create_message(self.instructions, system=True)
        print("Revenue Agent: Instructions created")
    
    async def add_agent_message(self, message):
        self.client.create_message(message)
        print("Revenue Agent: Message added")
        return "Message added"
    
    async def send_message(self):
        await self.client.send_message()
        print("Revenue Agent: Message sent")
        return "Message sent"
    
    def create_run(self):
        self.client.create_run()
        return "Run created"
    
    async def get_response(self):
        message = await self.client.retrieve()
        
        #await self.shared_memory.context_check_chat_length()
        with open(f"logs/{self.name}.txt", "w+") as f:
            f.write(message)
                
        return message, "completed"


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
        