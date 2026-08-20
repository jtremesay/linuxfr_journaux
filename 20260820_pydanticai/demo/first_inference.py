from pydantic_ai import Agent

# Création de notre agent
agent = Agent("ollama:gemma4:e2b")

# Requête simple à l'agent
r = agent.run_sync("Bonjour")

# Affichage de la réponse
print(r.output)
