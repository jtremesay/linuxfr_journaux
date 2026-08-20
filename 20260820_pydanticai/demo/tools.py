from dataclasses import dataclass
from xml.etree import ElementTree as ET

import httpx2
import logfire
from pydantic_ai import Agent
from pydantic_ai.common_tools.web_fetch import web_fetch_tool

logfire.configure(send_to_logfire="if-token-present")

agent = Agent(
    "ollama:gemma4:e2b",
    tools=[
        web_fetch_tool()  # Donne accès à l'outil web_fetch_tool pour récupérer des informations depuis le web
    ],
)
agent.instrument_all()


@dataclass
class AtomEntry:
    title: str
    link: str
    content: str


# Ce decorateur indique que la fonction suivante est un outil utilisable par l'agent
@agent.tool_plain
def get_linuxfr_atom_feed() -> list[AtomEntry]:
    feed_url = "https://linuxfr.org/news.atom"
    r = httpx2.get(feed_url)
    r.raise_for_status()

    root = ET.fromstring(r.text)

    entries = []
    for entry_elem in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = entry_elem.find("{http://www.w3.org/2005/Atom}title").text
        link = entry_elem.find("{http://www.w3.org/2005/Atom}link").attrib["href"]
        content = entry_elem.find("{http://www.w3.org/2005/Atom}content").text
        entries.append(AtomEntry(title=title, link=link, content=content))

    return entries
