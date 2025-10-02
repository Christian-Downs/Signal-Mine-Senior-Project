from pydantic_ai import Agent, RunContext


class CustomAgent(Agent):

    def read_prompt(self, file_name):
        with open(file_name) as file:
            prompt = file.read()
            return prompt

    def __init__(self, model, prompt_file_name):
        self.system_prompt = self.read_prompt(prompt_file_name)
        self.agent = Agent(
            model,
            system_prompt= self.system_prompt
        )

    async def run(self, user_prompt):
        return self.agent.run(user_prompt)
