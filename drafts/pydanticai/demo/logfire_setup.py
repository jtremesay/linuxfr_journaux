import logfire
from pydantic_ai import Agent

# Configuration de logfire pour instrumenter Pydantic AI globalement
logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()

agent = Agent("ollama:gemma4:e2b")
r = agent.run_sync("Bonjour")
print(r.output)

# Peut sinon s'activer par agent :
agent = Agent("ollama:gemma4:e2b")
agent.instrument_all()
