from pydantic_ai import Agent

agent = Agent("ollama:gemma4:e2b")

# Lancer le REPL de l'agent
agent.to_cli_sync()
