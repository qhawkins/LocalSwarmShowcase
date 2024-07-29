import time
import json
from agents.memory_agent import MemoryAgent
from agents.base_agent import BaseAgent
from agents.revenue_agent import RevenueAgent
from agents.evaluator_agent import EvaluatorAgent
from agents.sum_agent import SumAgent
import pandas as pd
import asyncio

class AsyncIterable:
    def __init__(self, data):
        self.data = data

    async def __aiter__(self):
        for item in self.data:
            yield item

class TaskDelegatorAgent(BaseAgent):
    def __init__(self, name: str, engine: str, agent_type: str, api_key: str, memory: MemoryAgent, description: str, path: str):
        super().__init__(name=name, engine=engine, agent_type=agent_type, api_key=api_key, memory=memory, description="Task delegator agent")
        self.data = pd.read_csv(path)  # Load company data from CSV

    async def call_revenue_agent(self, number, month, year, data, bank_account):
        # Create and call a RevenueAgent for specific month, year, and bank account
        agent = RevenueAgent(f"revenue_agent_month_{month}_year_{year}_{bank_account}", 
                             "/media/qhawkins/SSD3/llama-3-70b-instruct-awq", 
                             "revenue_agent", 
                             self.client.api_key, 
                             self.shared_memory, 
                             "Revenue agent", 
                             bank_account)
        
        chat = f"Here is the data: \n{str(data)}\n\nMake sure to strictly adhere to the system prompt.\n"
        print("chat created")
        await asyncio.sleep(.25)
        await agent.add_agent_message(chat)
        print("message added")
        await asyncio.sleep(.25)
        await agent.send_message()
        print("message sent")
        await asyncio.sleep(.25)
        response = await agent.get_response()
        print("getting response")
        parsed_response = response[0].replace(chat, "")
        return parsed_response, response[1]

    def serial_parse(self, series: str):
        # Remove specific patterns from the string
        split = series.split(" ")
        temp_str = ''
        for elem in split:
            if "st-" in elem.lower():
                continue
            else:
                temp_str += elem + " "
        return temp_str            

    async def call_sum_agent(self, agent_num, data):
        # Create and call a SumAgent to summarize data
        agent_name = f"sum_agent_{agent_num}"
        agent = SumAgent(agent_name, self.engine, "sum_agent", self.client.api_key, self.shared_memory, "Sum agent")
        chat = f"Read, evaluate and classify the following transactions. Here is the data: \n\n{str(data)}\n\nMake sure to strictly adhere to the format given in the prompt."
        await asyncio.sleep(.25)
        await agent.add_agent_message(agent_name, chat)
        await asyncio.sleep(.25)
        await agent.create_run(agent.name, True, [agent.name])
        await asyncio.sleep(.25)
        response = await agent.get_response()
        parsed_response = response[0].replace(chat, "")
        return parsed_response, response[1]

    async def call_evaluator_agent(self, agent_num, data):
        # Create and call an EvaluatorAgent to evaluate transactions
        agent_name = f"evaluator_agent_{agent_num}"
        agent = EvaluatorAgent(agent_name, self.engine, "evaluator_agent", self.client.api_key, self.shared_memory, "Evaluator agent")
        with open("ledger.txt", "r") as f:
            ledger = f.read()
        chat = f"Read, evaluate and classify the following transactions. Here is the data: \n\n{str(data)}###Ledger###\n{ledger}\n\nMake sure to strictly adhere to the format given in the prompt."
        await asyncio.sleep(.25)
        await agent.add_agent_message(agent_name, chat)
        await asyncio.sleep(.25)
        await agent.create_run(agent.name, True, [agent.name])
        await asyncio.sleep(.25)
        response = await agent.get_response()
        parsed_response = response[0].replace(chat, "")
        return parsed_response, response[1]

    async def retrieve_field_names(self):
        # Get column names from the loaded CSV data
        return self.data.columns

    async def parse_csv(self, date_field: str, description_field: str, amount_field: str, bankaccount_field: str):
        # Process and analyze the CSV data
        self.data = self.data[self.data[amount_field] < 0]  # Filter for negative amounts
        self.data = self.data[[date_field, description_field, amount_field, bankaccount_field]]

        # Clean up description field
        self.data['description'] = self.data[description_field].str.replace(r'\d+', '0', regex=True)
        self.data['description'] = self.data['description'].apply(lambda x: self.serial_parse(x))
        
        self.data['amount'] = -self.data[amount_field]  # Convert to positive values

        # Convert date to datetime and extract month
        self.data['datetime'] = pd.to_datetime(self.data[date_field], format="mixed")
        self.data['month'] = self.data['datetime'].dt.month

        agent_counter = 0
        sum_agent_num = 0
        unique_bank_accounts = self.data[bankaccount_field].unique()

        for bank_account in unique_bank_accounts:  
            start_time = time.time()
            print(f"Bank Account: {bank_account}") 
            overall_responses = []
            revenue_list = []
            ba_data = self.data[self.data[bankaccount_field]==bank_account] 
            
            for year in ba_data['datetime'].dt.year.unique():
                print(f"Year: {year}")
                tasks = []
                
                async for month in AsyncIterable(ba_data[ba_data['datetime'].dt.year==year]['month'].unique()):
                    print(f"Month: {month}")
                    monthly_data = ba_data[(ba_data['month']==month) & (ba_data['datetime'].dt.year==year)][["description", "amount"]]
                    clusters = monthly_data['description'].unique()
                    
                    # Aggregate data by description
                    for z in clusters:
                        sum_of_amounts = monthly_data[(monthly_data['description']==z)]['amount'].sum()
                        monthly_data.loc[monthly_data['description']==z, 'amount'] = sum_of_amounts
                        monthly_data.drop_duplicates(inplace=True, subset=['description', 'amount'])
                    
                    # Prepare data for revenue agent
                    sel = f"Transactions for Month: {month} in Year: {year} from Bank Account: {bank_account}\n\n"
                    for y in clusters:
                        sum_of_amounts = monthly_data[(monthly_data['description']==y)]['amount'].sum()
                        sel += f"Description: {y.replace(':', ' ')}, Total transaction amount: {sum_of_amounts}\n"
                    
                    # Create task for revenue agent
                    task = asyncio.create_task(self.call_revenue_agent(agent_counter, month, year, sel, bank_account))
                    tasks.append(task)
                    agent_counter = agent_counter + 1
                    
                # Wait for all revenue agent tasks to complete
                responses = await asyncio.gather(*tasks)
                await asyncio.sleep(.25)
                responses = AsyncIterable(responses)
                tasks = []

                # Create tasks for sum agents
                async for response in responses:
                    task = asyncio.create_task(self.call_sum_agent(sum_agent_num, response[0]))
                    tasks.append(task)
                    sum_agent_num = sum_agent_num + 1

                # Wait for all sum agent tasks to complete
                responses = await asyncio.gather(*tasks)
                await asyncio.sleep(.25)

                # Process and store sum agent responses
                for response in responses:
                    print(f"{response}")
                    revenue_list.append(f"{response[0]}\n")

            # Write revenue data to file
            with open(f"revenues/{bank_account}_revenue.txt", "w+") as f:
                f.writelines(revenue_list)
            
            end_time = time.time()
            print(f"Time taken for bank account {bank_account}: {end_time - start_time}")
            with open(f"elapsed_time.txt", "a") as f:
                f.write(f"Time taken for bank account {bank_account}: {end_time - start_time}\n")
        
        return overall_responses

    async def run_function(self, retrieved):
        # Process and execute function calls from the LLM
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

            elif elem['function']['name'] == 'end_chat':
                response = self.end_chat(prompt_to_user=arguments['prompt_to_user'])
                print(f"Task Delegator: {response}")
                self.status = "exited"

            elif elem['function']['name'] == 'parse_csv':
                print("Task Delegator: Parsing CSV")
                response = await self.parse_csv(arguments['date_field'], arguments['description_field'], arguments['amount_field'], arguments['bankaccount_field'])
                print(response)

            elif elem['function']['name'] == 'create_run':
                print("Task Delegator: Creating run")
                response = await self.create_run(target=arguments['target'], aggregate_messages=arguments['aggregate_messages'], agents=arguments['agents'])
                print(response)

            elif elem['function']['name'] == 'initiate_connection':
                print("Task Delegator: Initiating connection")
                response = await self.initiate_connection(target=arguments['target'])
                print(response)
            
            elif elem['function']['name'] == 'add_agent_message':
                print("Task Delegator: Adding agent message")
                response = await self.add_agent_message(agent_name=arguments['agent_name'], message=arguments['message'])
                print(response)
            
            elif elem['function']['name'] == 'retrieve_field_names':
                print("Task Delegator: Retrieving field names")
                response = await self.retrieve_field_names()
                print(response)

            else:
                response = 'No response, invalid function'
                print(response)
                
            tool_list.append({'tool_call_id': str(tool_id), 'output': str(response)})
            
        return tool_list, run_id, thread_id