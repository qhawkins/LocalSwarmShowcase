from agents.base_agent import BaseAgent
import time
import json
import pandas as pd

class ParserAgent(BaseAgent):
    def __init__(self, name: str, engine: str, agent_type: str, api_key: str, memory):
        super().__init__(name, engine, agent_type, api_key, memory)
    
    async def read_and_parse_csv(self, file_path, idx_start, idx_end, columns):
        df = pd.read_csv(file_path)
        selected_idx = df.iloc[idx_start:idx_end]
        selected_slice: pd.DataFrame = selected_idx[columns]
        return selected_slice.to_string()

    async def get_df_columns_and_length(self, file_path):
        df = pd.read_csv(file_path)
        columns = df.columns
        length = len(df)
        return columns, length

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
                
            if elem['function']['name'] == 'add_chat_to_conversation':
                response = self.add_chat_to_conversation(conversation_id=arguments['conversation_id'], agent_name=arguments['agent_name'], chat=arguments['chat'])
                print(response)

            elif elem['function']['name'] == 'read_and_parse_csv':
                response = self.read_and_parse_csv(file_path=arguments['file_path'], idx_start=arguments['idx_start'], idx_end=arguments['idx_end'], columns=arguments['columns'])
                print(response)

            elif elem['function']['name'] == 'get_df_columns_and_length':
                response = self.get_df_columns_and_length(file_path=arguments['file_path'])
                print(response)

            else:
                response = 'No response, invalid function'
                print(response)
                exit()
                
            tool_list.append({'tool_call_id': str(tool_id), 'output': str(response)})
            
        return tool_list, run_id, thread_id