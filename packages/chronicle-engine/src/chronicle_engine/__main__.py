"""Entry point: `python -m chronicle_engine`, the engine with no plugin's registrations."""

from chronicle_engine.entrypoints.cli.main import main

raise SystemExit(main())
