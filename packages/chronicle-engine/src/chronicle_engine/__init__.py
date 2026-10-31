"""chronicle-engine: facts, story pages and animations shared by the chronicle plugins.

The engine names no plugin. Each plugin links this package into its own `src/` folder,
registers its blocks, art, chrome, page parts, kinds, policies and commands in
`registry`, and runs the engine's command line.
"""

__version__ = "0.6.0"
