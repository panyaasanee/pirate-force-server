# ADR 0002: Local code-only Git

Status: accepted, 2026-08-15

The repository uses a deny-all root `.gitignore` and explicitly admits only source,
tests, migrations, selected build scripts, documentation, and the two V141 legacy
source/launcher files. Binaries, packages, backups, evidence, references, captures,
databases and generated releases cannot be staged by normal Git commands.

No remote is configured. GitHub may be considered later as a separate private-
repository decision.
