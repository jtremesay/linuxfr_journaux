from pydantic_ai import Agent

agent = Agent("ollama:gemma4:e2b")

# Historique de la conversation pour maintenir le contexte
history = []

while True:
    try:
        user_input = input("Vous: ")
        if user_input.strip().lower() in ["exit", "quit"]:
            raise KeyboardInterrupt
    except (KeyboardInterrupt, EOFError):
        print("\nAu revoir !")
        break

    r = agent.run_sync(user_input, message_history=history)
    print(f"Bot: {r.output}")

    # Mise à jour de l'historique avec les nouveaux messages
    history += r.new_messages()
