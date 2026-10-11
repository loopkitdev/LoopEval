# Handoffs

Written findings that one role needs another role to act on.

A handoff lives here, tracked, rather than in `runs/`: `runs/` is a gitignored symlink out of the
repo, so anything in it is invisible to `git status`, to a diff view and to GitHub, and it does not
travel between worktrees. A handoff on `main` reaches every checkout through the mechanism the rest
of the project already uses — the next merge.

- **One file per handoff**, `YYYY-MM-DD-<to-role>-<topic>.md`, naming the roles it is from and to.
- **The argument goes here; the evidence stays in the run directory.** CSVs, traces and scripts are
  bulky and often private — cite the run dir by path, don't copy it in.
- **Aliases only** (`bddp11`, `i001`, `user2`). The privacy rule in `AGENTS.md` applies in full:
  no URL, host, token or identifying detail, here least of all, because this is tracked.
- **A reply is a new file**, not an edit of the original. Roles never rewrite each other's files.
- When the peer's session is live, send a one-line `SendMessage` pointing here; the file is the
  durable copy, the message is the notification.
