from agents.main_agent import MainAgent
from agents.memory_agent import MemoryAgent
from agents.base_agent import BaseAgent
from agents.task_delegator import TaskDelegatorAgent
import asyncio

class Swarm:
    def __init__(self, config):
        # Initialize the swarm with configuration
        self.openai_key = config['openai_key']
        self.engine = config['engine']
        
        # Create memory and main agents
        self.memoryAgent = MemoryAgent("memory_agent", self.engine, "memory_agent", self.openai_key)
        self.main_agent = MainAgent("main_agent", self.engine, "main_agent", self.openai_key, self.memoryAgent, "Main agent for the swarm")
        
        # Set up task delegator with company data
        path = r'company_data.csv'
        self.task_delegator = TaskDelegatorAgent("task_delegator", self.engine, "task_delegator", self.openai_key, self.memoryAgent, "the task delegator agent", path)
        
    async def main_agent_lifetime(self, agent: BaseAgent):
        # Register agents in the memory
        await self.memoryAgent.ledger_add_agent("main_agent", {"agent_info": {"description": "no description", "status": "create_agent"}, "agent_class": self.main_agent}, self.main_agent)
        await self.memoryAgent.ledger_add_agent("memory_agent", {"agent_info": {"description": "no description", "status": "create_agent"}, "agent_class": self.memoryAgent}, self.memoryAgent)
        await self.memoryAgent.ledger_add_agent("task_delegator", {"agent_info": {"description": "no description", "status": "create_agent"}, "agent_class": self.task_delegator}, self.task_delegator)
        
        print("prompting agent from user")

        # Wait for the agent to be ready
        while agent.status != "ready":
            await asyncio.sleep(1)

        # Prompt the user for instructions
        await agent.add_agent_message("main_agent", "Prompt the user for instructions.")
        
        print("running agent")
        await asyncio.gather(agent.create_run(target="main_agent", aggregate_messages=True, agents=[]))

        print("getting response")
        response, status = await agent.get_response()
        status = "active"
        
        # Main loop for agent interaction
        while status != "exited":
            await asyncio.sleep(1)
            response, status = await agent.get_response()
            if status == "completed":
                print(response)
                print(100*'=')
                await agent.add_agent_message("main_agent", "prompt the user for further instructions and clarification on your task")
                await agent.create_run(target="main_agent", aggregate_messages=True, agents=[])
                response, status = await agent.get_response()

    async def main(self):
        # Run the main agent's lifetime
        await asyncio.gather(
            self.main_agent_lifetime(self.main_agent),
        )
        print(f"Finished main agent lifetime")
        print(f"Memory agent: {await self.memoryAgent.ledger_get_agent()}")
        
        return 0

    async def run(self):
        # Entry point for running the swarm
        await self.main()