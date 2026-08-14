"""Central logging setup, called once at app startup (see app.main).

Configures the root logger so every module's `logging.getLogger(__name__)`
calls end up formatted consistently and printed to stdout - no per-module
setup needed.
"""

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )

    # These libraries log every HTTP call at INFO, which drowns out our own
    # request/AI-call logs; keep them at WARNING unless someone's debugging
    # the libraries themselves.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
