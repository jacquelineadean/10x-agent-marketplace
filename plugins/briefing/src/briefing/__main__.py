"""`python -m briefing`: register briefing's layouts and blocks, then run the engine CLI."""

from chronicle_engine.entrypoints.cli.main import main

import briefing.pack  # noqa: F401  (registers briefing's layouts, blocks, checks and commands)

raise SystemExit(main())
