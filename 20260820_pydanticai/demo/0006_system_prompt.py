from pydantic_ai import Agent

# Définition d'un prompt système pour notre agent
system_prompt = """
Tu es un assistant coréen, tu ne parles que en coréen sous titré bilingue.
"""

# Création de notre agent avec le prompt système défini ci-dessus
agent = Agent(system_prompt=system_prompt)
