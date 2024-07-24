from agents.base_agent import BaseAgent
import asyncio
import json

class EvaluatorAgent(BaseAgent):
    def __init__(self, name: str, engine: str, agent_type: str, api_key: str, memory, description: str):
        super().__init__(name, engine, agent_type, api_key, memory, description)
        self.engine = "gpt-3.5-turbo"
    
    def add_to_ledger(self, addition: dict):
        with open("ledger.txt", "a") as f:
            for elem in addition.keys():
                f.write(f"{elem}: {addition[elem]}\n")
        return "Added to ledger"
    
    def check_ledger(self, item: str):
        with open("ledger.txt", "r") as f:
            for line in f.readlines():
                if item in line:
                    return line.replace(f"{item}", "").replace(":", "")
                else:
                    continue
        return False

    def classify_transactions(self, transactions: list):
        return_dict = {}
        for transaction in transactions:
            check = self.check_ledger(transaction)
            if check:
                return_dict[transaction] = check
            else:
                return_dict[transaction] = input(f"\nPlease classify the transaction: {transaction}\n")

        print(self.add_to_ledger(return_dict))
        return return_dict


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
                
            if elem['function']['name'] == 'classify_transactions':
                response = self.classify_transactions(transactions=arguments['unsure_transactions'])
                print(response)
            else:
                response = f"Function {elem['function']['name']} not found"

            tool_list.append({'tool_call_id': str(tool_id), 'output': str(response)})
            
        return tool_list, run_id, thread_id
        