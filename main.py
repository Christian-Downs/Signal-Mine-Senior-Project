# This is a sample Python script.
import asyncio
import ollama


# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


async def print_hi(name):
    print(ollama.list())
    # desginer = CustomAgent('openai:gpt-4o', 'prompts/prompt_generator.txt')
    #
    # output = await desginer.run(input("PROMPT: "))




asyncio.run(print_hi(''))