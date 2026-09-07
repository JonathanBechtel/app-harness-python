"""Versioned prompts.

Each prompt family is a package with ``v1.py``, ``v2.py``... modules exposing
``VERSION``, ``TEMPLATE`` and ``render(**kwargs) -> str``. The active version is
chosen by ``PROMPT_<FAMILY>_VERSION`` (see loader.py).
"""
