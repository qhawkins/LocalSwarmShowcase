# Transaction Classification Agent Swarm

I created this project while completing my internship at Lendica. My task was to create an agent swarm to aid in the loan underwriting process. This swarm helps automate the process of revenue classification by analyzing different transaction items and their descriptions in the context of the company as a whole. We originally used GPT-4 for the entire swarm, but that was incredibly expensive so I decided to make some of the token-intensive agents utilize Llama 3 70B. This led to significant cost savings without sacrificing on accuracy. 

Keep in mind that there are still some bugs with this project and it is far from perfect. There are also some unimplemented features (such as the memory agent) which exist as placeholders. I have added some annotations to the code to help with readability.
  
## Project Description

The agent swarm utilizes the Llama 3 70B model to perform transaction classification. It processes input data and categorizes each transaction based on whether it contributes to revenue or not. It then sums up the revenue by month to give you an accurate estimate of the company's financial health. I have generated fake company data using Claude 3.5 sonnet as a placeholder for real company data.

## Prerequisites

Before running this project, ensure you have the following:
- OpenAI API key
- Git
- Python 3.x
- At least 48GB of VRAM

## Installation

1. Set your OpenAI API key as an environment variable:
   ```
   export OPENAI_API_KEY='your-api-key-here'
   ```

2. Clone the repository:
   ```
   git clone https://github.com/qhawkins/LocalSwarmShowcase.git
   cd LocalSwarmShowcase
   ```

3. Download the quantized Llama 3 70B model:
   
   Download the model from [this Hugging Face repository](https://huggingface.co/qhawk/Llama-3-70B-AWQ-Swarm).

## Running the Project

1. Ensure all prerequisites are met and the model is downloaded.

2. Run the main script:
   ```
   python main.py
   ```

3. When prompted, paste the contents of `beginning_prompt.txt` into the chat to initiate the revenue recognition process.

## Note

This project requires at least 48GB of VRAM to run the local model which is utilized by the revenue agents.
The company data provided in this repo is fake and generated using Claude 3.5 sonnet. You can use your own data, which will be automatically parsed by the task delegator agent.
