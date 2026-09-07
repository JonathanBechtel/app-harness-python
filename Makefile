# Thin shim: every task is defined ONCE in tasks.py (cross-platform, no shell).
#   make <task> [KEY=VALUE ...]      on macOS / Linux / WSL
#   python tasks.py <task> [...]     anywhere, including native Windows
# Run `make help` for the task list.
PYTHON ?= python
# Parameters forwarded to tasks.py when set on the make command line.
PARAMS := $(foreach v,BASE TESTS SUITE IMAGE DEPLOY_URL ROUNDTRIP_DATABASE_URL DIFF_COVER_FAIL_UNDER HOST PORT m,$(if $($(v)),$(v)=$($(v)),))

.DEFAULT_GOAL := help
.PHONY: help FORCE

help:
	@$(PYTHON) tasks.py help

FORCE:

%: FORCE
	@$(PYTHON) tasks.py $@ $(PARAMS) $(ARGS)

# make always tries to remake its own makefile; keep the catch-all rule off it.
Makefile: ;
