from pydantic_ai import Agent

agent = Agent("ollama:gemma4:e2b")

# Boucle REPL pour interagir avec l'agent
while True:
    try:
        # Demande à l'utilisateur d'entrer un message
        user_input = input("Vous: ")

        # Vérifie si l'utilisateur veut quitter le REPL
        if user_input.strip().lower() in ["exit", "quit"]:
            raise StopIteration
    except (KeyboardInterrupt, EOFError, StopIteration):
        # Gestion de l'interruption du REPL (Ctrl+C, Ctrl+D ou "exit"/"quit")
        print("\nAu revoir !")
        break

    # Envoie le message de l'utilisateur à l'agent et affiche la réponse
    r = agent.run_sync(user_input)
    print(f"Bot: {r.output}")
