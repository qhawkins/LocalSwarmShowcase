from exllamav2 import ExLlamaV2, ExLlamaV2Config, ExLlamaV2Cache, ExLlamaV2Tokenizer
from exllamav2.generator import ExLlamaV2StreamingGenerator, ExLlamaV2Sampler
import torch
import sys

class Model:
    _instance = None
    def __new__(cls, model_id, batch_size = 1):
        if not cls._instance:
            cls._instance = super(Model, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_id, batch_size = 1):
        if not hasattr(self, 'initialized'):  # Prevent re-initialization
            self.config = ExLlamaV2Config(model_id)
            self.config.max_seq_len = 5120
            self.model = ExLlamaV2(self.config)
            self.cache = ExLlamaV2Cache(batch_size=batch_size, model=self.model, lazy=True, max_seq_len = self.config.max_seq_len)
            
            self.draft_config = ExLlamaV2Config("/media/qhawkins/SSD3/Llama-3-8B-Instruct-exl2")
            self.draft_config.max_seq_len = 5120
            self.draft_model = ExLlamaV2(self.draft_config)
            self.draft_cache = ExLlamaV2Cache(batch_size=batch_size, model=self.draft_model, lazy=True, max_seq_len = self.draft_config.max_seq_len)

            self.draft_model.load_autosplit(self.draft_cache)
            self.model.load_autosplit(self.cache)
            self.tokenizer = ExLlamaV2Tokenizer(self.config)
            self.initialized = True  # Mark as initialized
            #set stop token to <|eot_id|>
            self.tokenizer.eos_token = "<|eot_id|>"
        
    
    def retrieve_self(self):
        return self

class BaseLLM:
    def __init__(self, model_id, batch_size = 1):
        self.model_class = Model(model_id, batch_size)
        self.generator = ExLlamaV2StreamingGenerator(model=self.model_class.model, cache=self.model_class.cache, 
                                                     tokenizer=self.model_class.tokenizer, draft_cache=self.model_class.draft_cache,
                                                     draft_model=self.model_class.draft_model, num_speculative_tokens=5)

        self.generator.set_stop_conditions([self.model_class.tokenizer.eos_token_id, "<|eot_id|>", "assistant"])
        self.gen_settings = ExLlamaV2Sampler.Settings(temperature=1)
        self.messages = []

    def begin_stream(self, context_ids):
        self.generator.begin_stream_ex(context_ids, self.gen_settings)

    def get_context_ids(self, instruction_ids):
        return instruction_ids if self.generator.sequence_ids is None else torch.cat([self.generator.sequence_ids, instruction_ids], dim = -1)

    def encode(self, text):
        return self.model_class.tokenizer.encode(text)

    def send_message(self):
        instruction_ids = self.encode(str("".join(self.messages)))
        self.begin_stream(instruction_ids)
            
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
        self.send_message()
        
    
    def retrieve(self):
        res_list = ''
        while True:
            res = self.generator.stream_ex()
            res_list += res["chunk"]
            if res["eos"]: 
                break
            print(res["chunk"], end = "")
            sys.stdout.flush()
        self.messages = []
        print("\n"+75*"=+"+"\n")
        return res_list

    def list_messages(self):
        return self.messages
    
    def create_tool_outputs(self):
        return 100

        
