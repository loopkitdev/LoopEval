# PRIVATE.md — local site config (never commit / never publish)

Copy this file to `PRIVATE.md` (`cp PRIVATE.example.md PRIVATE.md`) and fill in the
Nightscout sites you analyze. `PRIVATE.md` is **git-ignored**, and `CLAUDE.md` imports it,
so your LoopEval agent has this context automatically.

This file holds **real Nightscout URLs, tokens, and per-dataset replay config**. Nightscout
data is a real person's medical data. **Nothing in here goes into the repo, a report, a PR,
an issue, a plot, or any other shareable output.** In anything shareable, refer to datasets
by an anonymous alias (`user1`, `user2`, `orefuser`, …) and a placeholder URL
(`https://YOUR-NS.example.com`).

> Tell your LoopEval agent *"add a site"* (or just describe one) and it will record it here
> in this format, capturing the config that faithful replay needs.

## Datasets

One row per site. Record the config needed for **deployment-faithful replay** — see
AGENTS.md → *Deployment-faithful config per dataset*. The example rows below show the
*kind* of facts to capture (replace them with your own):

| Alias | Nightscout | Config that matters for faithful replay |
|---|---|---|
| **user1** | `https://YOUR-NS.example.com` | *(Loop user — Omnipod)* insulin model `--insulin-type rapidActingAdult` (verify IOB vs devicestatus); RC mode + era: `--integral-rc` while IRC was on, standard RC after — **note the switch date**; deployed-Loop emulation `--no-mid-absorption-isf --no-gradual-transitions-gate`; app factor 0.xx (GBAF? y/n); meal-announcement level; any dated settings changes (target band→point, ISF a→b, CR). |
| **user2** | `https://YOUR-NS.example.com` (guest/token `xxxxxxxx` if the site needs one) | *(Loop user)* `--insulin-type fiasp` (peak-55); IRC always on + clamp `--integral-rc --integral-rc-clamp`; Temporary Overrides `--apply-overrides --override-targets-json`; **edits carb entries** → always `--carb-revisions-json` (reconstruct_carb_history); heavy meal announcer. |
| **orefuser** | `https://YOUR-TRIO-NS.example.com` token `xxxxxxxx` | *(Trio / oref user)* dynISF mode + AF, autosens_max, ISF/CR/DIA, UAM/SMB; oref prefs `--candidate-oaps-dia N --candidate-oaps-smooth-glucose`. |

Guest / small Nightscout hosts often **500/502 on parallel cold fetches** — warm one sim
serially per dataset+window first, then parallelize from cache.

## Local infra & conventions

- **Data cache:** `~/.loop-eval/cache/` (populated on first fetch; re-runs read from it).
- **Extra-sensitive creds** can live fully outside the repo in `~/.loop-eval/<alias>/site.json`
  instead of inline above.
- **Experiment outputs:** `runs/YYYY-MM-DD-topic/` (git-ignored scratch; keep the run
  script + scorer next to the traces).
- **Serving reports to another machine (optional):**
  `nohup python3 -m http.server 8790 --bind 0.0.0.0 -d . &`, then share
  `http://<lan-ip>:8790/...` (scope the server to the workspace root).
- Add anything else local and private here (infra, commit identities, etc.).
