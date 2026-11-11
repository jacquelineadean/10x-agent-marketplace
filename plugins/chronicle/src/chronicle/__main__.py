"""Entry point: `python -m chronicle`, the engine with chronicle's registrations."""

from chronicle_engine.entrypoints.cli.main import main

import chronicle.pack  # noqa: F401  (registers chronicle's blocks, art, kinds and commands)

raise SystemExit(main())
