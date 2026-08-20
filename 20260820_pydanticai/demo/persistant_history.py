from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessagesTypeAdapter

HISTORY_FILE = Path().cwd() / "history.json"

agent = Agent("ollama:gemma4:e2b")

try:
    # Chargement de l'historique des messages depuis le fichier JSON
    history = ModelMessagesTypeAdapter.validate_json(HISTORY_FILE.read_bytes())
except FileNotFoundError:
    # Pas de fichier d'historique, on commence avec un historique vide
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

    history += r.new_messages()

    # Sauvegarde de l'historique des messages dans le fichier JSON
    HISTORY_FILE.write_bytes(ModelMessagesTypeAdapter.dump_json(history))
