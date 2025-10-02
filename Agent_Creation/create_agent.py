
from pydantic_ai import Agent, RunContext


def agent_maker():
    agent = Agent(
        'openai:gpt-4o',
        deps_type=int,
        output_type=bool,
        system_prompt=(
            'Use the `roulette_wheel` function to see if the '
            'customer has won based on the number they provide.'
        ),
    )



