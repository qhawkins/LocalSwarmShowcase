from vllm import SamplingParams, AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
import sys
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("/media/qhawkins/SSD3/llama-3-70b-instruct-awq")

class Model:
    _instance = None

    def __new__(cls, engine):
        if not cls._instance:
            cls._instance = super(Model, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self, engine):
        if not self.initialized:
            engine_args = AsyncEngineArgs(
                swap_space=2,
                model=engine,
                quantization="awq",
                dtype="half",
                gpu_memory_utilization=.9,
                kv_cache_dtype="fp8_e5m2",
                tensor_parallel_size=2,
                max_num_seqs=8,
                #enforce_eager=True,
                worker_use_ray=True,
                max_model_len=4096,
                use_v2_block_manager=True,
                #enable_prefix_caching=True,
                tokenizer_pool_size=8,
                #enable_chunked_prefill=True,
                #max_num_batched_tokens=4096,
            )
            self.engine = AsyncLLMEngine.from_engine_args(engine_args, start_engine_loop=True)
            self.initialized = True

    def retrieve_self(self):
        return self
    

class BaseVLLM:
    def __init__(self, request_id, engine):
        self.model_class = Model(engine)
        self.messages = []
        self.gen_settings = SamplingParams(temperature=1, top_p=0.95, max_tokens=4096, 
                                           stop={"assistant", "<|eot_id|>"})
        self.request_id = request_id

    async def send_message(self):
        #print("Sending message...")
        #print(str("".join(self.messages)))
        #instruction_ids = self.encode(str("".join(self.messages)))
        #context_ids = self.get_context_ids(instruction_ids)
        
        self.generator = self.model_class.engine.generate("".join(self.messages), self.gen_settings, request_id=self.request_id)


    def create_message(self, message, system = False):
        #mixtral
        '''
        if system:
            self.messages.append(f"[INST]\nsystem:\n{message}[/INST]")
        else:
            self.messages.append(f"[INST]\nuser:\n{message}[/INST]")

        '''
        #dolphin mixtral
        '''
        if system:
            self.messages.append(f"<|im_start|>system:\n{message}<|im_end|>\n")
        else:
            self.messages.append(f"<|im_start|>user:\n{message}<|im_end|>\n<|im_start|>assistant:\n")

        '''
        if system:
            self.messages.append(f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{message}<|eot_id|>")
        else:
            self.messages.append(f"<|start_header_id|>user<|end_header_id|>\n\n{message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n")
        
    
    def remove_message(self):
        self.messages = []
    
    def create_run(self):
        return 0
        
    
    async def retrieve(self):
        async for result in self.generator:
            #print(result)
            #res_list += result
            input_prompt = result.prompt
            output = result.outputs[0].text

        input_tokens = tokenizer(input_prompt, return_tensors="pt")
        input_token_length = input_tokens['input_ids'].shape[-1]
        
        with open("input_tokens.txt", "a") as f:
            f.write(str(input_token_length)+"\n")
        
        print(f"Input token length: {input_token_length}")


        output_tokens = tokenizer(output, return_tensors="pt")
        output_token_length = output_tokens['input_ids'].shape[-1]
        
        with open("output_tokens.txt", "a") as f:
            f.write(str(output_token_length)+"\n")
        
        print(f"Output token length: {output_token_length}")
        print("\n"+75*"=+"+"\n")
        return output

    def list_messages(self):
        return self.messages
    
    def create_tool_outputs(self):
        return 100
