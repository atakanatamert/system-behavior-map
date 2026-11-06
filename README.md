# system-behavior-map

An [Agent Skill](https://agentskills.io) that reads a software project the way Donella Meadows' *Thinking in Systems* reads a system: stocks, flows, feedback loops, delays, system traps, leverage points — and the questions to ask before changing it.

It exists because most engineering fixes are band-aids on events. The skill is built to pull you up the iceberg: from the event ("CI went red again") to the pattern (it goes red every time a burst lands) to the structure (gates run only on files a change touched, and the build loop has no brake at its own speed) to the belief that keeps the structure in place ("surface area is free").

## What it produces

Pointed at a repository, the skill writes, read-only:

| File | What it is |
|---|---|
| `SYSTEM_BEHAVIOR.md` | The full argument: boundary and purpose (stated vs. revealed), stocks and flows, balancing and reinforcing loops, delays, the eight Meadows traps checked one by one, the twelve leverage points ranked, 8–15 questions, one hypothesis. Every claim is tagged `[seen]` (with a path or number) or `[inferred]`. |
| `SYSTEM_BEHAVIOR-stocks-flows.svg` | A stock-and-flow diagram in the book's notation: boxes, pipes with valves, clouds, thin information links to valves, `\|\|` delays, R/B loop labels. |
| `SYSTEM_BEHAVIOR-loops.svg` | A causal-loop diagram of the 2–4 loops that decide behaviour, with the brake's delay visible. |
| `SYSTEM_BEHAVIOR.html` | A self-contained dashboard in four layers — **events → behaviour over time → structure → mental models** — then the questions. Dense, no libraries, dark-mode aware. Hover carries detail; `<details>` carries evidence. |
| `sbm_data.json`, `sbm_config.json`, `sbm_content.json` | The extracted time series, the extraction config, and the curated text, kept beside the output so next month's run refreshes the behaviour layer without redoing the analysis. |

The behaviour layer is reconstructed from git alone, with no checkout: the last commit of each ISO week, `git ls-tree -l` for every tracked file's size (split source / test / docs per component), `git show` + regex for project-specific stock counters (routes, env reads, providers, migrations…), and `git log --numstat` for the flows between snapshots.

## Install

**Claude Code / any Agent Skills host** — copy the skill folder into your skills directory:

```bash
git clone https://github.com/atakanatamert/system-behavior-map
cp -r system-behavior-map/skills/system-behavior-map ~/.claude/skills/
```

or, inside a single project, into `.claude/skills/`.

**As a Claude Code plugin:**

```
/plugin marketplace add atakanatamert/system-behavior-map
/plugin install system-behavior-map@system-behavior-map
```

**claude.ai** — upload `skills/system-behavior-map` as a skill in Settings.

## Use

```
/system-behavior-map            # in a project
/system-behavior-map path/to/repo
```

Then read the questions first. They are the deliverable; everything else is the evidence for them.

## Principles the skill enforces

- **Evidence or inference, never blurred.** Fewer `[seen]` claims beat many `[inferred]` ones; a section with no evidence says so.
- **Questions, not prescriptions.** It names which leverage point a question targets. It does not propose code changes unless asked.
- **Diagrams add no structure the text did not establish.** Drawing comes after the analysis.
- **Read-only.** It never modifies the project.

## Scripts

`skills/system-behavior-map/scripts/`

- `sbm_extract.py <repo> out.json [--config sbm_config.json]` — weekly snapshots → stock levels, flows, candidate events. Python 3.8+, no dependencies.
- `sbm_dashboard.py data.json content.json out.html [stocks.svg loops.svg]` — the four-layer dashboard. Python 3.8+, no dependencies.

Templates for both JSON files are in `templates/`.

## Further reading

Donella H. Meadows, *Thinking in Systems: A Primer* (Chelsea Green, 2008). The skill borrows its vocabulary, notation and the twelve leverage points from it; nothing in the repository reproduces the book's text.

## License

MIT — see [LICENSE](LICENSE).
