# Pydantic AI - faire des agents en python

[Pydantic AI](https://pydantic.dev/docs/ai/overview/) est une bibliothèque Python permettant de créer facilement des agents. En gros, c'est la glue entre un LLM, des outils, des MCP, l'IHM, ...

Dans ce journal, nous allons voir comment l'utiliser.

## Pré-requis

Pré-requis plus ou moins optionnels. Vous pouvez faire sans, mais ça peut être mieux avec.

### UV

[UV](https://docs.astral.sh/uv/) est un questionnaire de python, de virtual env, de dépendences, … On déclare l'env qu'on veut (tel version de python et tel version de dépendences), et il s'occupe de vous fournir un environnement fonctionnel et synchronisé.


Guide d'installation : [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

Exemple :

```shell
$ uv init demo
Initialized project `demo` at `/home/jtremesay/projects/linuxfr_journaux/demo`
$ cd demo
$ uv add pydantic-ai-slim
Using CPython 3.14.7 interpreter at: /usr/bin/python3.14
Creating virtual environment at: .venv
Resolved 19 packages in 5ms
      Built demo @ file:///home/jtremesay/projects/linuxfr_journaux/demo                                                                                                                                                                                                                                          
Prepared 1 package in 4ms
Installed 18 packages in 3ms
 + annotated-types==0.8.0
 + anyio==4.14.2
 + demo==0.1.0 (from file:///home/jtremesay/projects/linuxfr_journaux/demo)
 + genai-prices==0.1.4
 + griffelib==2.2.0
 + h11==0.16.0
 + httpcore2==2.12.0
 + httpx2==2.12.0
 + idna==3.19
 + logfire-api==4.41.0
 + opentelemetry-api==1.44.0
 + pydantic==2.13.4
 + pydantic-ai-slim==2.32.1
 + pydantic-core==2.46.4
 + pydantic-graph==2.32.1
 + truststore==0.10.4
 + typing-extensions==4.16.0
 + typing-inspection==0.4.4
$ uv run python -c 'import pydantic_ai; print("Hello World")'
Hello World
$ rm -rf .venv
$ uv run python -c 'import pydantic_ai; print("Hello World")'
Using CPython 3.14.7 interpreter at: /usr/bin/python3.14
Creating virtual environment at: .venv
Installed 18 packages in 8ms
Hello World
```

On a crée un nouveau projet `demo`, on a ajouté la dépendence `pydantic-ai-slim`, et fait un petit test que tout fonctionne automatiquement. puis on a fucké l'environement virtuel. `uv` a automatiquement recréé l'environnement virtuel et réinstallé les dépendences.

Vous n'avez pas spécifiquement de `uv` pour ce journal, mais c'est vraiment un outil que je recommande pour les projets python. [jojo seal of approval®](https://linuxfr.org/users/killruana/journaux/nixos-et-colmena-la-prod-declarative-du-pauvre#comment-2027131).

### Ollama

Allez voir la  [présentation](https://linuxfr.org/users/jflesch/journaux/auto-heberger-ses-ia#toc-ollama) de [Ollama](https://ollama.com/) par Jérôme Flesch<.

Mais en gros, c'est un serveur de LLM, qui permet d'utiliser des modèles locaux et propose l'accélération CUDA (nVidia)/ROCm (AMD)/Vulkan (GPU)/CPU (ne pas être pressé…).

Si vous avez une bonne config, vous avez un accès facile à plein de [modèles](https://ollama.com/search) sans vous prendre la tête.

```shell
$ ollama run gemma4:e4b
>>> Bonjour !
Thinking...
Here's a thinking process for generating the response:

1.  **Analyze the input:** The user said "Bonjour !" (Hello!).
2.  **Determine the appropriate tone and language:** Since the user used French, the response must be in French. The tone should be friendly, welcoming, and engaging.
3.  **Formulate a standard greeting:** A simple reciprocal greeting is necessary ("Bonjour !").
4.  **Encourage further interaction (The goal of an AI assistant):** A good greeting doesn't just stop; it prompts the user to state their need. I need to ask them how I can help.
5.  **Draft options (Internal Monologue/Drafting):**
    *   *Option 1 (Too short):* Bonjour.
    *   *Option 2 (Slightly better):* Bonjour ! Comment vas-tu ?
    *   *Option 3 (Professional and helpful):* Bonjour ! Comment puis-je vous aider aujourd'hui ? (This is the most appropriate for a general AI assistant.)
6.  **Select the best option:** Option 3 combines warmth ("Bonjour!") with immediate functionality ("Comment puis-je vous aider...?"). I will ensure I use the formal address ("vous") unless the context suggests otherwise, as it's safer and more respectful.
7.  **Final Polish:** "Bonjour ! Comment puis-je vous aider aujourd'hui ?" (Hello! How can I help you today?)

*(Self-Correction Check: Is this polite? Yes. Is it helpful? Yes. Is it in the correct language? Yes.)*
...done thinking.

Bonjour ! 👋

Comment puis-je vous aider aujourd'hui ? N'hésitez pas si vous avez des questions, besoin d'informations, ou si vous voulez qu'on discute d'un sujet précis ! 😊
```

Vous avez aussi accès à une API REST, qui sera utilisé par Pydantic AI pour communiquer avec le LLM :

```shell
$ http POST http://localhost:11434/api/generate \
                                        model="gemma4:e4b" \
                                        prompt="Bonjour !" \
                                        stream:=false
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
Date: Thu, 20 Aug 2026 18:24:16 GMT
Transfer-Encoding: chunked

{
    "created_at": "2026-08-20T18:24:16.979920468Z",
    "done": true,
    "done_reason": "stop",
    "model": "gemma4:e4b",
    "response": "Bonjour ! 😊\n\nComment puis-je vous aider aujourd'hui ? Avez-vous une question, avez-vous besoin d'aide avec quelque chose, ou voulez-vous simplement discuter ?",
}
```

Si vous n'avez pas de gros GPU, vous pouvez utiliser [Ollama Cloud](https://ollama.com/cloud) qui offre pour le moment un free tier plus que suffisant pour nos tests. Ça s'intègre très facilement avec le Ollama local. Un petit coup de `ollama signin`, et il proxiefiera pour vous automatiquement les requetes des modèles tagués `cloud` vers le cloud :

```shell
$ ollama signin
...
$ echo 'bonjour' | ollama run gemma4:cloud
Thinking...
"bonjour" (French for "Hello").
French.
Greeting.

    *   Acknowledge the greeting.
    *   Respond in French (matching the user's language).
    *   Offer assistance.

    *   *Option 1 (Simple):* Bonjour ! (Too short)
    *   *Option 2 (Polite/Standard):* Bonjour ! Comment puis-je vous aider aujourd'hui ? (Good, standard)
    *   *Option 3 (Warm/Friendly):* Bonjour ! Je suis ravi de vous parler. Que puis-je faire pour vous ? (A bit more personal)
    *   *Option 4 (Multilingual context):* Bonjour ! Hello! How can I help you? (Only if I'm not sure they only speak French, but usually, it's better to stick to the language used).

    *   "Bonjour ! Comment puis-je vous aider aujourd'hui ?" (Hello! How can I help you today?)
...done thinking.

Bonjour ! Comment puis-je vous aider aujourd'hui ?
```

## Modèles supportés

Pydantic AI supporte à peu près tous les fourniseurs de LLM. Voir la [documentation](https://pydantic.dev/docs/ai/models/overview/) pour voir comment supporter votre fournisseur préféré.

Moi je vais utiliser Ollama qui est compatible OpenAI API, il me faut ajouter la dépendance `pydantic-ai-slim[openai]` :

```shell
$ uv add pydantic-ai-slim[openai]
```

## Votre premier chatbot

