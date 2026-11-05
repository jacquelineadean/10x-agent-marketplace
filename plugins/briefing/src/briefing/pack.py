"""briefing's registrations with the engine: the deck and dashboard layouts, the kpi,
filters and animation blocks, their page parts, the checks and the commands.

Importing this module registers everything once; `python -m briefing` imports it before
running the engine's command line.
"""

from __future__ import annotations

from importlib import resources

from chronicle_engine import registry
from sources.entrypoints.cli import linked

from briefing.core import animation, dashboard, deck, kpi, slices
from briefing.entrypoints.cli import commands

registry.LAYOUTS["deck"] = registry.Layout(deck.render, tuple(deck.SKELETON))
registry.LAYOUTS["dashboard"] = registry.Layout(dashboard.render, tuple(dashboard.SKELETON))
registry.add_block("kpi", kpi.REQUIRED, kpi.OPTIONAL, kpi.kpi, after="stats")
registry.add_block("filters", slices.REQUIRED, slices.OPTIONAL, slices.filters, after="kpi")
registry.add_block(
    "animation", animation.REQUIRED, animation.OPTIONAL, animation.animation, after="diagram"
)
registry.BLOCK_KEYS.update({"build", "span", "slice"})
registry.FILES["animation"] = ("svg",)
registry.add_parts(
    by_type={
        "layout:deck": ("css/50-deck.css", "js/70-deck.js"),
        "layout:dashboard": ("css/52-dashboard.css",),
        "kpi": ("js/10-charts.js", "js/20-figures.js", "js/71-kpi.js", "css/51-blocks.css"),
        "filters": ("js/72-filters.js", "css/51-blocks.css"),
        "animation": ("css/53-animation.css", "js/73-animation.js"),
    }
)
registry.CHECKS["briefing"] = commands.check
registry.COMMANDS["export"] = registry.Command(commands.export_parser, commands.export_run)
registry.COMMANDS["slides"] = registry.Command(commands.slides_parser, commands.slides_run)
registry.COMMANDS["refresh"] = registry.Command(commands.refresh_parser, commands.refresh_run)
registry.COMMANDS["sources"] = registry.Command(linked.add_parser, linked.run)
registry.add_asset_root(resources.files("briefing.assets"))
registry.DEFAULTS.prog = "briefing"
registry.DEFAULTS.layout = "dashboard"
registry.DEFAULTS.new_folders = ("widgets",)
registry.DEFAULTS.new_next = "gather facts with sources:gatherer, then write the story"
