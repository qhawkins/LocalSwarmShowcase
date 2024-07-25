from agents.main_agent import MainAgent
from agents.memory_agent import MemoryAgent
from agents.base_agent import BaseAgent
from agents.task_delegator import TaskDelegatorAgent
import asyncio


class Swarm:
    def __init__(self, config):
        self.openai_key = config['openai_key']
        self.engine = config['engine']
        #creating main and memory agent classes for the swarm, since they are the two main agents that orchestrate the rest of the swarm
        self.memoryAgent = MemoryAgent("memory_agent", self.engine, "memory_agent", self.openai_key)
        self.main_agent = MainAgent("main_agent", self.engine, "main_agent", self.openai_key, self.memoryAgent, "Main agent for the swarm")
        path = r'company_data.csv'
        
        self.task_delegator = TaskDelegatorAgent("task_delegator", self.engine, "task_delegator", self.openai_key, self.memoryAgent, "the task delegator agent", path)
        #self.mainAgent = MainAgent("main_agent", self.engine, "main_agent", openai_key, self.memoryAgent)
        
    async def main_agent_lifetime(self, agent: BaseAgent):
        await self.memoryAgent.ledger_add_agent("main_agent", {"agent_info": {"description": "no description", "status": "create_agent"}, "agent_class": self.main_agent}, self.main_agent)
        await self.memoryAgent.ledger_add_agent("memory_agent", {"agent_info": {"description": "no description", "status": "create_agent"}, "agent_class": self.memoryAgent}, self.memoryAgent)
        await self.memoryAgent.ledger_add_agent("task_delegator", {"agent_info": {"description": "no description", "status": "create_agent"}, "agent_class": self.task_delegator}, self.task_delegator)
        print("prompting agent from user")

        while agent.status != "ready":
            await asyncio.sleep(1)

        await agent.add_agent_message("main_agent", "Prompt the user for instructions.")

        print("running agent")
        await asyncio.gather(agent.create_run(target="main_agent", aggregate_messages=True, agents=[]))

        print("getting response")
        response, status = await agent.get_response()
        status = "active"
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
        #wait for the main agent to finish its lifetime
        await asyncio.gather(
            self.main_agent_lifetime(self.main_agent),
        )
        print(f"Finished main agent lifetime")
        print(f"Memory agent: {await self.memoryAgent.ledger_get_agent()}")
        
        return 0

    async def run(self):
        await self.main()