from dataclasses import dataclass

from pydantic_ai import Agent, RunContext


@dataclass
class MyDeps:
    name: str
    location: str


agent = Agent("ollama:qwen3.5:2b", deps_type=MyDeps)


@agent.system_prompt
def system_prompt_with_deps(ctx: RunContext[MyDeps]) -> str:
    return f"Tu es en train de parler avec {ctx.deps.name}."


@agent.tool
def get_current_weather(ctx: RunContext[MyDeps]) -> str:
    # TODO: call a weather API to get the current weather for ctx.deps.location
    return f"Le temps actuel à {ctx.deps.location} est ensoleillé."


deps = MyDeps(name="Jojo", location="Montpellier, France")
r = agent.run_sync("Quelle est la météo actuelle ?", deps=deps)
print(r.output)
