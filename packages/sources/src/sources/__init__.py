"""sources: read-only access to company systems for the plugins that present data.

Detection, the source picker, the facts contract (`facts.json`, `queries.json`,
`digest.md`) and named connections. The package imports neither the chronicle engine
nor any plugin; each plugin that needs it links it into its own `src/` folder.
"""

__version__ = "0.1.0"
