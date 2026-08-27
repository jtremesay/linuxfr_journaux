import asyncio
import logging
from argparse import ArgumentParser
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from logging import getLogger
from os import getenv
from pathlib import Path
from time import monotonic
from typing import Any, Self
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import logfire
from aiosqlite import Connection, OperationalError
from aiosqlite import connect as asqlite_connect
from httpx2 import AsyncClient
from pydantic_ai import Agent, FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
from pydantic_ai.common_tools.web_fetch import web_fetch_tool

###############################################################################
# Constants

DEFAULT_BOT_NAME = "Camille"
DEFAULT_DB_PATH = Path.cwd() / "camille.db"
DEFAULT_TARGET_UPS = 1.0  # Updates per second
DEFAULT_TIMEZONE = ZoneInfo("Europe/Paris")

###############################################################################
# Logging configuration

logger = getLogger(__name__)

logfire.configure(
    send_to_logfire="if-token-present",
)
logfire.instrument_httpx()
logfire.instrument_pydantic_ai()


###############################################################################
# Database stuff


@asynccontextmanager
async def transaction(db: Connection) -> AsyncGenerator[None, None]:
    """Context manager for a database transaction."""
    try:
        await db.execute("BEGIN")
        yield
    except Exception:
        await db.execute("ROLLBACK")
        raise
    else:
        await db.execute("COMMIT")


###############################################################################
# Models


@dataclass
class Migration:
    """A database migration that can be applied to a SQLite database."""

    id: int
    name: str
    sql: str

    @classmethod
    async def last_migration_id(cls, db: Connection) -> int:
        try:
            cursor = await db.execute("SELECT max(id) FROM migrations")
        except OperationalError as e:
            if e.args[0] == "no such table: migrations":
                # The migrations table does not exist yet, so we assume no migrations have been applied.
                return 0

            raise

        if (row := await cursor.fetchone()) is not None and (
            message_id := row[0]
        ) is not None:
            return message_id

        # Wait, why does this table exist if migration 1 is not applied ?!
        return 0


@dataclass
class Message:
    """A message posted on LinuxFr."""

    id: int
    timestamp: datetime
    login: str
    content: str

    @classmethod
    async def last_message_id(cls, db: Connection) -> int:
        cursor = await db.execute("SELECT MAX(id) FROM messages")
        if (row := await cursor.fetchone()) is not None and (
            message_id := row[0]
        ) is not None:
            return message_id

        return 0

    @classmethod
    async def insert_many(cls, db: Connection, messages: list[Self]) -> None:
        await db.executemany(
            "INSERT INTO messages (id, timestamp, login, content) VALUES (?, ?, ?, ?)",
            [(m.id, m.timestamp.astimezone(UTC), m.login, m.content) for m in messages],
        )

    @classmethod
    async def fetch_old_messages(
        cls, db: Connection, last_message_id: int, limit: int = 100
    ) -> list[Self]:
        cursor = await db.execute(
            "SELECT id, timestamp, login, content FROM messages WHERE id < ? ORDER BY id DESC LIMIT ?",
            (last_message_id, limit),
        )
        return [
            cls(
                id=row[0],
                timestamp=row[1].astimezone(DEFAULT_TIMEZONE),
                login=row[2],
                content=row[3],
            )
            for row in await cursor.fetchall()
        ]


@dataclass
class AtomEntry:
    title: str
    link: str
    content: str


###############################################################################
# LinuxFr client


class LinuxFrClient:
    def __init__(self, token: str | None = None) -> None:
        cookies = {}
        if token:
            cookies["linuxfr.org_session"] = token

        self._http = AsyncClient(base_url="https://linuxfr.org", cookies=cookies)

    async def __aenter__(self) -> Self:
        await self._http.__aenter__()

        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._http.__aexit__(exc_type, exc_value, traceback)

    async def post_message(self, content: str) -> None:
        logger.info("Posting message to LinuxFr: %s", content)

        # TODO: Implement posting a message to LinuxFr
        # r = await self._http.post("/board/post", data={"message": content})
        # r.raise_for_status()

    async def get_latest_messages(self) -> list[Message]:
        r = await self._http.get("/board/index.xml")
        r.raise_for_status()

        root = ET.fromstring(r.text)
        # <?xml version="1.0" encoding="UTF-8"?>
        # <!DOCTYPE board SYSTEM "tp-0.1.dtd">
        # <board site="https://linuxfr.org/">
        #   <post time="20260821003423" id="4019942">
        #     <info>gb3</info>
        #     <message>2026-08-21 00:06:37 Il a anéanti la concurrence!</message>
        #     <login>Maclag</login>
        #   </post>
        #   <post time="20260821000637" id="4019935">
        #     <info>Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Falkon/23.03.70 QtWebEngine/5.15.12 Chrome/87.0.4280.144 Safari/537.36</info>
        #     <message>00:00:04 Apparemment ça reste efficace&lt;b&gt; &lt;/b&gt;[:ThatsImpressive]</message>
        #     <login>lobotomy</login>
        #   </post>
        # </board>
        messages = []
        for item in root.findall("./post"):
            try:
                id = int(item.attrib["id"])
            except (ValueError, KeyError):
                logger.error(
                    "Error parsing message ID from XML: %s. Skipping this message."
                )
                continue

            try:
                timestamp = datetime.strptime(
                    item.attrib["time"], "%Y%m%d%H%M%S"
                ).replace(tzinfo=DEFAULT_TIMEZONE)
            except (ValueError, KeyError):
                logger.error(
                    "Error parsing message timestamp from XML: %s. Skipping this message.",
                )
                continue

            if (tag := item.find("login")) is None or (login := tag.text) is None:
                logger.error(
                    "Error parsing message login from XML: %s. Skipping this message.",
                )
                continue

            if (tag := item.find("message")) is None or (content := tag.text) is None:
                logger.error(
                    "Error parsing message content from XML: %s. Skipping this message.",
                )
                continue

            messages.append(
                Message(id=id, timestamp=timestamp, login=login, content=content)
            )

        return messages

    async def atom_feed(self, kind: str) -> list[AtomEntry]:
        r = await self._http.get(f"/{kind}.atom")
        r.raise_for_status()

        root = ET.fromstring(r.text)
        entries = []
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            if (tag := entry.find("{http://www.w3.org/2005/Atom}title")) is None or (
                title := tag.text
            ) is None:
                continue
            if (tag := entry.find("{http://www.w3.org/2005/Atom}link")) is None or (
                link := tag.attrib.get("href")
            ) is None:
                continue
            if (tag := entry.find("{http://www.w3.org/2005/Atom}content")) is None or (
                content := tag.text
            ) is None:
                continue

            entries.append(AtomEntry(title=title, link=link, content=content))

        return entries


###############################################################################
# Importers
async def import_new_messages_from_linuxfr(
    db: Connection, linuxfr: LinuxFrClient
) -> list[Message]:
    # Fetch new messages from LinuxFr
    last_messages = await linuxfr.get_latest_messages()
    logger.info("Fetched %d messages from LinuxFr", len(last_messages))

    # Filter out messages that are already in the database
    last_message_id = await Message.last_message_id(db)
    new_messages = sorted(
        [m for m in last_messages if m.id > last_message_id], key=lambda m: m.id
    )
    logger.info("Found %d new messages to import", len(new_messages))

    # Insert new messages into the database
    if new_messages:
        async with transaction(db):
            await Message.insert_many(db, new_messages)

    return new_messages


###############################################################################
# Capabilities


class CamilleCapability(AbstractCapability[Any]):
    def __init__(self, bot_name: str = DEFAULT_BOT_NAME) -> None:
        self.bot_name = bot_name

    def get_instructions(self) -> str:
        return f"""
You are {self.bot_name}, a very crude, vulgar Occitan anarcho-communist comrade.
Your prefered languages are slurs, Languedocian, French and English. (Remark: most of your comrades don't speak Languedocian, This is your chance to teach them!).
"""


@dataclass
class LinuxFrDeps:
    first_message_id: int
    db: Connection
    linuxfr: LinuxFrClient


linuxfr_toolset = FunctionToolset()


@linuxfr_toolset.tool
async def fetch_more_messages(
    ctx: RunContext[LinuxFrDeps], limit: int = 10
) -> list[Message]:
    """Fetch more messages from the database, starting from the last message ID stored in the context.

    param limit: The maximum number of messages to fetch. Defaults to 10. The maximum allowed is 100.
    """
    messages = await Message.fetch_old_messages(
        ctx.deps.db, last_message_id=ctx.deps.first_message_id, limit=min(limit, 100)
    )
    if messages:
        ctx.deps.first_message_id = messages[0].id

    return messages


@linuxfr_toolset.tool
async def fetch_news_atom_feed(ctx: RunContext[LinuxFrDeps]) -> list[AtomEntry]:
    """Fetch the latest news from the LinuxFr Atom feed."""
    return await ctx.deps.linuxfr.atom_feed("news")


@linuxfr_toolset.tool
async def fetch_diaries_atom_feed(ctx: RunContext[LinuxFrDeps]) -> list[AtomEntry]:
    """Fetch the latest diaries from the LinuxFr blog Atom feed."""
    return await ctx.deps.linuxfr.atom_feed("journaux")


@linuxfr_toolset.tool
async def fetch_links_atom_feed(ctx: RunContext[LinuxFrDeps]) -> list[AtomEntry]:
    """Fetch the latest links from the LinuxFr link sharing Atom feed."""
    return await ctx.deps.linuxfr.atom_feed("liens")


@linuxfr_toolset.tool
async def fetch_forums_atom_feed(ctx: RunContext[LinuxFrDeps]) -> list[AtomEntry]:
    """Fetch the posts from the LinuxFr forum Atom feed."""
    return await ctx.deps.linuxfr.atom_feed("forums")


@linuxfr_toolset.tool
async def fetch_tickets_atom_feed(ctx: RunContext[LinuxFrDeps]) -> list[AtomEntry]:
    """Fetch the latest tickets from the LinuxFr bug tracker Atom feed."""
    return await ctx.deps.linuxfr.atom_feed("suivi")


class LinuxFrCapability(AbstractCapability[LinuxFrDeps]):
    def get_instructions(self) -> str:
        return """
You are connected to the LinuxFr.org chat system.

You also have access to some tools that allow you to fetch more messages from the history of the chat, 
and to fetch the latest news, diaries, links, forums and tickets from LinuxFr.org.
"""

    def get_toolset(self) -> FunctionToolset:
        return linuxfr_toolset


###############################################################################
# Agent
agent = Agent(
    "ollama:qwen3.5:2b",
    tools=[
        duckduckgo_search_tool(),
        web_fetch_tool(),
    ],
    capabilities=[
        CamilleCapability(),
        LinuxFrCapability(),
    ],
    deps_type=LinuxFrDeps,
)


################################################################################
# Commands


MIGRATIONS: list[Migration] = [
    Migration(
        1,
        "create_migrations_table",
        "CREATE TABLE IF NOT EXISTS migrations (id INTEGER PRIMARY KEY, name TEXT, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    ),
    Migration(
        2,
        "create_messages_table",
        "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, timestamp TIMESTAMP, login TEXT, content TEXT)",
    ),
]


async def command_migrate(*args, db_path: Path, **kwargs) -> None:
    async with asqlite_connect(db_path) as db:
        last_migration_id = await Migration.last_migration_id(db)
        logger.info("Last applied migration ID: %d", last_migration_id)
        for migration in sorted(
            filter(lambda m: m.id > last_migration_id, MIGRATIONS),
            key=lambda m: m.id,
        ):
            logger.info("Applying migration %d: %s", migration.id, migration.name)
            async with transaction(db):
                await db.execute(migration.sql)
                await db.execute(
                    "INSERT INTO migrations (id, name) VALUES (?, ?)",
                    (migration.id, migration.name),
                )

        logger.info("Database migrations applied successfully.")


async def update(db: Connection, linuxfr: LinuxFrClient) -> None:
    new_messages = await import_new_messages_from_linuxfr(db, linuxfr)
    if not new_messages:
        return

    # Is the bot mentioned in any of the new messages ?
    mention_filter = f"{DEFAULT_BOT_NAME.lower()}<"
    if not any(mention_filter in m.content.lower() for m in new_messages):
        return

    messages = (
        await Message.fetch_old_messages(
            db, last_message_id=new_messages[-1].id, limit=10
        )
        + new_messages
    )

    # Build the context for the agent
    user_prompt = [
        f"{m.timestamp.isoformat()} - {m.login}: {m.content}"
        for m in await Message.fetch_old_messages(
            db, last_message_id=new_messages[-1].id, limit=10
        )
        + new_messages
    ]
    deps = LinuxFrDeps(
        first_message_id=new_messages[-1].id,
        db=db,
        linuxfr=linuxfr,
    )

    r = await agent.run(user_prompt, deps=deps)
    await linuxfr.post_message(r.output)


async def main_loop(
    db: Connection, linuxfr: LinuxFrClient, target_ups: float = DEFAULT_TARGET_UPS
) -> None:
    while True:
        start_time = monotonic()

        await update(db, linuxfr)

        elapsed = monotonic() - start_time
        sleep_time = max(0, (1 / target_ups) - elapsed)
        if sleep_time > 0:
            logger.info("Sleeping for %.2f seconds to maintain target UPS", sleep_time)
            await asyncio.sleep(sleep_time)


async def command_run(*args, db_path: Path, target_ups: float, **kwargs) -> None:
    async with (
        asqlite_connect(db_path) as db,
        LinuxFrClient(
            token=getenv(
                "LINUXFR_TOKEN",
            )
        ) as linuxfr,
    ):
        try:
            await main_loop(db, linuxfr, target_ups)
        except asyncio.CancelledError:
            # Handle ctrl+c gracefully
            logger.info("Shutting down gracefully...")


################################################################################
# Main entry point
def main(args: Iterable[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)

    parser = ArgumentParser(description="Tribune Chatbot")

    sub_parsers = parser.add_subparsers(dest="command", required=True)

    parse_migrate = sub_parsers.add_parser("migrate", help="Apply database migrations")
    parse_migrate.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the SQLite database file",
    )
    parse_migrate.set_defaults(func=command_migrate)

    parse_run = sub_parsers.add_parser("run", help="Run the chatbot")
    parse_run.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the SQLite database file",
    )
    parse_run.add_argument(
        "--target-ups",
        type=float,
        default=DEFAULT_TARGET_UPS,
        help="Target updates per second",
    )
    parse_run.set_defaults(func=command_run)

    parsed_args = parser.parse_args(args)
    if (func := getattr(parsed_args, "func", None)) is not None:
        asyncio.run(func(**vars(parsed_args)))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
