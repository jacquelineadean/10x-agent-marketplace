"""blueprint's registrations with the engine: the tad, sequence and erd kinds, the
architecture, cards and list blocks, the prototype layout, their page parts, the checks and
the commands.

Importing this module registers everything once; `python -m blueprint` imports it before
running the engine's command line.
"""

from __future__ import annotations

from importlib import resources

from chronicle_engine import registry
from sources.entrypoints.cli import linked

from blueprint.core import architecture, erd, prototype, sequence
from blueprint.core.tad import kind as tad
from blueprint.entrypoints.cli import commands

registry.add_kind("tad", tad.TAD, first=True)
registry.add_kind("sequence", sequence.SEQUENCE)
registry.add_kind("erd", erd.ERD)
registry.add_block(
    "architecture",
    architecture.REQUIRED,
    architecture.OPTIONAL,
    architecture.architecture,
    after="diagram",
)
registry.add_block("cards", *prototype.CARDS, prototype.cards, after="stats")
registry.add_block("list", *prototype.LIST, prototype.plist, after="table")
registry.LAYOUTS["prototype"] = registry.Layout(prototype.render, tuple(prototype.SKELETON))
registry.BLOCK_KEYS.add("span")
registry.FILES["architecture"] = ("svg",)
registry.add_parts(
    by_type={
        "architecture": ("css/60-architecture.css", "js/80-architecture.js"),
        "cards": ("css/61-blocks.css", "js/82-prototype.js"),
        "list": ("css/61-blocks.css", "js/82-prototype.js"),
        "layout:prototype": ("css/61-blocks.css", "css/62-prototype.css", "js/82-prototype.js"),
    }
)
registry.CHECKS["blueprint"] = commands.check
registry.COMMANDS["schema"] = registry.Command(commands.schema_parser, commands.schema_run)
registry.COMMANDS["lineage"] = registry.Command(commands.lineage_parser, commands.lineage_run)
registry.COMMANDS["sources"] = registry.Command(linked.add_parser, linked.run)
registry.add_asset_root(resources.files("blueprint.assets"))
# Engineering pages number their chapters with a step pill.
registry.CHROME.mark_default = "step"
registry.DEFAULTS.prog = "blueprint"
registry.DEFAULTS.kind = "tad"
registry.DEFAULTS.new_next = "write the story; build each animation it plays first"
