from datetime import UTC, datetime

from pydantic_ai import Agent

agent = Agent(
    system_prompt="Tu es un assistant coréen, tu ne parles que en coréen sous titré bilingue."
)


@agent.system_prompt
def system_prompt_conversation_start() -> str:
    return datetime.now(UTC).strftime(
        "The conversation started the %Y-%m-%d at %H:%M:%S UTC"
    )


# Ce decorateur indique que la fonction suivante est utilisée pour générer un prompt système dynamique
@agent.system_prompt(dynamic=True)
def system_prompt_timestamp() -> str:
    return datetime.now(UTC).strftime("The current time is %Y-%m-%d at %H:%M:%S UTC")
