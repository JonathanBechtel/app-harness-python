# Module conventions

Vocabulary (from `app/CLAUDE.md`): **models** are ORM tables; **schemas** are Pydantic edge contracts; **repositories** do row access and never commit; **services** own logic and transactions; **helpers/utils** are stateless and named `<domain>_utils.py`.

Enforcement is opt-in per directory via `.module-conventions.yml` and `scripts/check_module_conventions.py`:

1. Refactor a directory until it is internally coherent.
2. Enroll it: `path` + the rule families that apply (`services`, `repositories`, `helpers`, `models`, `transformers`).
3. From then on, misplaced or misnamed modules there fail the build with a relocation hint.
4. Repeat directory by directory. Do not try to normalise the whole tree at once.

Rules: files under a family directory carry the family suffix (MODC001); a suffixed file at the root belongs under its family directory (MODC002); a root file whose shape looks like a family (a `BaseModel` subclass, service-layer imports, only functions) is flagged with a hint (MODC003); an enrolled family directory must exist (MODC004). `_private.py` modules are exempt from suffix rules.

Why this matters more with AI: when discovery or convention is by filename, filename rules must be mechanical or they rot within weeks.
