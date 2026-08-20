from dataclasses import dataclass
from enum import StrEnum

from pydantic_ai import Agent


class Gender(StrEnum):
    # Vanilla genders
    FEMALE = "female"
    MALE = "male"

    # Spicy genders
    # TODO:


class Race(StrEnum):
    HUMAN = "human"
    ELF = "elf"
    DWARF = "dwarf"
    ORC = "orc"
    TROLL = "troll"
    GOBLIN = "goblin"
    HALFLING = "halfling"
    GNOME = "gnome"
    DRAGONBORN = "dragonborn"
    TIEFLING = "tiefling"


@dataclass
class Character:
    name: str
    age: int
    gender: Gender
    race: Race
    description: str


agent = Agent("ollama:qwen3.5:2b")

# Demande à l'agent de générer un personnage pour un jeu de rôle
r = agent.run_sync(
    "Génère un personnage pour un jeu de role",
    output_type=Character,
)

# Affiche le type de l'objet retourné et ses attributs
assert isinstance(r.output, Character)
print(r.output)
print(r.output.name, r.output.age, r.output.gender, r.output.race)
