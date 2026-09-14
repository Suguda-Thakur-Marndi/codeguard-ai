#!/usr/bin/env python
"""CodeGuard AI Empirical Benchmarking CLI entrypoint."""

import os
import sys

# Ensure packages and apps are on path
_root = os.path.abspath(os.path.dirname(__file__))
_pkg_path = os.path.join(_root, "packages", "code-intelligence")
_api_path = os.path.join(_root, "apps", "api")
for p in [_root, _pkg_path, _api_path]:
    if p not in sys.path:
        sys.path.insert(0, p)

from evaluation.cli import main

if __name__ == "__main__":
    main()
