from agents.base_agent import BaseAgent
import time
import json

class SumAgent(BaseAgent):
    def __init__(self, name: str, engine: str, agent_type: str, api_key: str, memory, description: str):
        super().__init__(name, engine, agent_type, api_key, memory, description)
    
    async def sum_amounts(self, amounts: list):
        running_revenue = 0
        for amount in amounts:
            running_revenue += float(amount)
        
        return running_revenue

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
                
            if elem['function']['name'] == 'sum_amounts':
                response = await self.sum_amounts(amounts=arguments['amounts'])
                print(response)

            else:
                response = 'No response, invalid function'
                print(response)
                
            tool_list.append({'tool_call_id': str(tool_id), 'output': str(response)})
            
        return tool_list, run_id, thread_id
        