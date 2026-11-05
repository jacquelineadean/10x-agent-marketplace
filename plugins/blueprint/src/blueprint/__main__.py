"""`python -m blueprint`: register blueprint's kinds, blocks and layout, then run the engine CLI."""

from chronicle_engine.entrypoints.cli.main import main

import blueprint.pack  # noqa: F401  (registers blueprint's kinds, blocks, layout, checks and commands)

raise SystemExit(main())
