---
name: system-behavior-map
description: "Analyze any software project as a system (Meadows' Thinking in Systems): stocks, flows, feedback loops, delays, traps, leverage points, Meadows-style diagrams, behaviour-over-time charts from git history, and an iceberg dashboard (events, behaviour, structure, mental models) with the questions to ask before changing it."
---

# System Behavior Map

Produce a systems-thinking description of a software project in the vocabulary of Donella Meadows' *Thinking in Systems*. The goal is not to list bugs or propose fixes. The goal is to show the reader the structure that *produces* the project's recurring behavior, so they can ask questions that change the structure instead of patching symptoms.

Two rules that override everything else:

1. **Evidence or inference, never both blurred.** Every claim is tagged `[seen]` (a file, config, commit pattern, or metric you actually observed, with its path) or `[inferred]` (a reasoned guess). Prefer fewer `[seen]` claims to many `[inferred]` ones. If the repo offers no evidence for a section, say so instead of inventing content.
2. **Questions, not prescriptions.** The deliverable ends in questions the owner should investigate. You may note which leverage point a question targets, but you do not recommend specific code changes unless asked.

Work read-only. Do not modify the project.

## Step 1 — Survey the evidence (cheap, broad, before any interpretation)

Gather raw material first; interpretation comes later. Use the shell or an Explore subagent for the broad sweeps so file dumps stay out of the main context. Collect:

- **Shape:** top-level tree, languages, package/dependency manifests, build and CI config, deployment config, infra-as-code, Dockerfiles, env/config files, feature-flag definitions.
- **Rules (the system's formal constraints):** linters, formatters, type-check strictness, test commands, coverage thresholds, branch protection or CODEOWNERS, PR templates, commit hooks, ADRs, CONTRIBUTING docs.
- **Information flows (what the system can see about itself):** logging, metrics, tracing, health checks, alerting config, dashboards, error reporting, analytics.
- **Symptom markers (grep across the codebase and count):** `TODO|FIXME|HACK|XXX|WORKAROUND`, lint-disable / `eslint-disable` / `noqa` / `#pragma` suppressions, test skips (`@skip`, `xit`, `.skip(`, `@Ignore`), broad exception swallowing (`except:`/`catch (e) {}`), retry wrappers, `sleep`/hard-coded timeouts, `any`/`unknown` casts, `@ts-ignore`, `unsafe`, deprecated-API usage, duplicated utilities.
- **History (if git is available):** `git log --format='%ad' --date=short | cut -c1-7 | sort | uniq -c` (commit cadence), churn per file (`git log --name-only --format='' | sort | uniq -c | sort -rn | head -40`), files that change together, revert commits, hotfix-labelled commits, bus factor (`git shortlog -sn`), age of oldest open TODOs via blame.
- **Size stocks:** LOC per module, number of dependencies (direct vs transitive), number of DB migrations, number of config options/flags, number of endpoints or commands, test count, open issues if an issue tracker is reachable.

Write the raw counts down. Numbers are what make the later sections `[seen]` rather than `[inferred]`.

## Step 2 — Define the system and its purpose

- **Boundary:** what is inside (this repo) and what is outside but coupled (external APIs, databases, queues, third-party services, the team, users). Note where the boundary is drawn arbitrarily by the repo layout versus where the real behavioral boundary lies.
- **Stated purpose:** what README/docs say the system is for.
- **Revealed purpose:** what the system's behavior shows it is actually optimizing for (Meadows: purposes are deduced from behavior, not rhetoric). Evidence: what gets measured, what gates a merge, what the commit history spends effort on, what has alerting and what does not. Where stated and revealed purposes diverge, say so plainly; that gap is usually the most important finding.

## Step 3 — Stocks and flows

List the stocks (things that accumulate and can be measured at an instant) and the inflows/outflows that change them. Typical software stocks, pick the ones the evidence supports:

| Stock | Inflows | Outflows |
|---|---|---|
| Codebase size / complexity | features, copy-paste, generated code | refactors, deletions |
| Known debt (TODOs, suppressions, skipped tests) | shortcuts under deadline | debt paydown |
| Unknown debt (untyped, untested, unobserved regions) | code added without tests/types/logging | coverage added |
| Dependencies | adding libraries | removal, consolidation |
| Open bugs / issues | user reports, regressions | fixes, closures, wontfix |
| Runtime state (DB rows, queues, caches, files) | writes, ingestion | deletion, TTL, archival |
| Team knowledge of the system | docs, onboarding, pairing | turnover, undocumented change |
| Trust in the test suite / CI | reliable green builds | flaky failures, ignored reds |

For each stock: current level if measurable `[seen]`, direction of trend if history shows it, and which flows dominate. Mark stocks that only have inflows: those grow without bound by construction.

## Step 4 — Feedback loops

Identify loops and classify each as **balancing** (goal-seeking, stabilizing) or **reinforcing** (compounding, runaway). For each loop name the stock it acts on, the links in the loop, and the evidence.

Common balancing loops to look for: tests gate merges; type checker rejects bad changes; monitoring → alert → fix; code review; rate limiting / backpressure; dependency bots; linters. For each: is the loop actually closed? A test suite that exists but is skipped, or an alert nobody routes, is an *open* loop, i.e. not a loop.

Common reinforcing loops: complexity → slower change → pressure → shortcuts → complexity; flaky tests → skipped tests → less trust → more skips; one module attracts code because it already has everything (success to the successful); missing types → casts → more missing types; slow CI → batching → bigger risky merges → more CI failures.

State which loops are currently dominant. Dominance shifts, so note what would flip it.

## Step 5 — Delays

Delays are where oscillation and overshoot come from. Record, with evidence: time from bug introduced to detected (where does detection happen: compile, test, CI, staging, production, user report?); CI duration; release cadence; dependency update lag; cache TTLs and eventual-consistency windows; time for a new contributor to make a safe change; time between "we should fix this" (TODO blame date) and now.

Long delays in a balancing loop make the system correct late and over-correct. Flag any balancing loop whose delay is longer than the inflow it is supposed to regulate.

## Step 6 — System traps

For each of Meadows' traps, state **present / not evidenced / unclear**, with evidence. Do not force a match.

- **Policy resistance:** repeated attempts to fix the same thing (same files in many "fix" commits, several competing abstractions for one concern) with the problem persisting.
- **Tragedy of the commons:** a shared resource everyone draws on and nobody owns (shared `utils`, global config, a hot DB table, CI minutes, the main branch's build time).
- **Drift to low performance:** standards relaxed to match current behavior (coverage threshold lowered, lint rules disabled project-wide, tests marked skip "temporarily" long ago, warnings treated as noise).
- **Escalation:** two parts of the system each compensating for the other (retries in caller and callee, defensive validation on both sides, timeouts stacked on timeouts).
- **Success to the successful:** the module/person/service that already has the most keeps getting more, starving alternatives (god module, single maintainer with most commits).
- **Shifting the burden to the intervenor (addiction):** symptom relief that weakens the system's own corrective capacity (catch-all exception handlers, auto-restart instead of fixing crashes, manual hotfix process replacing CI, scheduled cache clears, cron jobs that clean up what the code should not produce).
- **Rule beating:** following the letter of a rule while defeating its purpose (tests that assert nothing, lint-disable comments, coverage padded by trivial tests, PR approval rubber-stamps).
- **Seeking the wrong goal:** optimizing the measurable proxy (coverage %, velocity, LOC, number of tickets closed) instead of the real goal.

## Step 7 — Leverage points (ranked)

Map findings onto Meadows' leverage points, weakest to strongest, and note which the evidence suggests are available. Most engineering fixes land in the first three; the reader's education comes from seeing the rest.

12. Numbers (constants, timeouts, thresholds, pool sizes)
11. Buffers (queue sizes, cache sizes, slack in schedules)
10. Stock-and-flow structure (physical architecture: module boundaries, data model, service split)
9. Delays (CI speed, release cadence, detection latency)
8. Balancing loops (strength of tests, types, review, monitoring)
7. Reinforcing loops (slowing the compounding ones: complexity, flakiness, knowledge loss)
6. Information flows (who can see what: observability, docs, making debt visible)
5. Rules (merge gates, ownership, definition of done)
4. Self-organization (ability of the system to change its own structure: refactor budget, plugin architecture, team autonomy)
3. Goals (what the system is actually for, see Step 2)
2. Paradigm (the unexamined beliefs the codebase embodies: "tests slow us down", "we'll clean it up later", "this is a prototype")
1. Transcending paradigms

For each point 12 to 2, one line: what the evidence says, or "no evidence".

## Step 8 — Draw the system (two diagrams, Meadows notation)

Drawing comes after the analysis, never before: a diagram drawn first invents structure to fill the page. Produce two SVG files beside the document and embed both in it. Author the SVG by hand (no library needed, works in any project); render it to PNG and look at it if a converter exists.

### 8a. Stock-and-flow diagram → `SYSTEM_BEHAVIOR-stocks-flows.svg`

Show the 4 to 7 stocks that matter from Step 3, their flows, and the information links that regulate the valves. Notation, exactly as in the book:

- **Stock**: rectangle, name in bold, one line of `[seen]` numbers under it.
- **Flow**: a thick double-line pipe into or out of a stock with a **valve** (bow-tie) on it; the valve carries the rate's name and a number if known. A flow nobody can turn on is drawn with a red X over the valve (e.g. "deletion — closed by rule"). A flow at ≈0 is still drawn, labelled ≈0: an absent outflow is a finding.
- **Cloud**: source or sink outside the boundary, at the open end of a flow.
- **Information link**: thin curved arrow from a stock (or outside variable) to a *valve*, never to a stock directly. Mark it **+** (same direction) or **−** (opposite). Draw `||` across it for a delay and write the delay's length beside the marks.
- **Loop label**: filled circle with **R** (reinforcing, red) or **B** (balancing, blue) and its number from Step 4, placed inside the loop with a one-line caption.
- A legend row at the bottom and one line stating which numbers are `[seen]` and which are not in the repo.

Symbol library to paste into `<defs>` so every run looks the same:

```svg
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#333"/></marker>
<g id="valve"><path d="M-11,-10 L11,10 L11,-10 L-11,10 Z" fill="#fff" stroke="#333" stroke-width="1.6"/></g>
<g id="cloud"><path d="M-26,8 c-10,0 -14,-12 -4,-16 c-2,-12 14,-16 20,-8 c6,-10 24,-6 22,6 c10,2 10,16 -2,18 c-4,10 -20,10 -24,2 c-6,6 -16,2 -12,-2 z" fill="#fff" stroke="#777" stroke-width="1.4"/></g>
```
```css
.stock{fill:#f4f1e8;stroke:#222;stroke-width:2} .pipe{stroke:#555;stroke-width:7;fill:none} .pipe-in{stroke:#fff;stroke-width:3.5;fill:none}
.info{stroke:#333;stroke-width:1.3;fill:none;marker-end:url(#arrow)} .loop{font-weight:bold;fill:#fff;text-anchor:middle}
```
A pipe is two overlaid lines (`.pipe` then `.pipe-in`) with `<use href="#valve">` at its midpoint; a cloud is `<use href="#cloud">` at the open end. Canvas about 1280×820, stocks 200×70 on a loose grid of two or three rows, flows horizontal or vertical, information links as cubic Béziers that end at the valve. Put the binding stock (usually people's attention) at the left edge so every drain on it is visible.

### 8b. Causal-loop diagram → `SYSTEM_BEHAVIOR-loops.svg`

Show the 2 to 4 loops that decide behaviour (Step 4 "Dominance"), without the plumbing. Variables are plain text with a one-line `[seen]` number beneath; arrows mean "a change here causes a change there", each marked **+** or **−**, `||` for a delay; **R**/**B** circles inside each loop. Draw an `[inferred]` loop dashed and say so in its caption. The reader should be able to see, without the prose, which loops compound, which one brakes, and where the brake's delay sits. End with a two-line "Reading it" box stating the dominant loop and the brake.

### 8c. Check the drawings

If `rsvg-convert`, `cairosvg`, `inkscape` or `magick` is available, render each SVG to PNG at ~1600 px wide and look at the image. Fix overlapping labels, arrows that end in text, and marks that sit off their arrow; re-render. Two passes at most, then stop. If no converter exists, say so and leave the SVG unchecked rather than guessing. Save the PNGs beside the SVGs when they were produced; they are what the person previews on a phone.

Every stock, flow and link drawn must appear in Steps 3 to 4 with the same name and loop number; the diagram adds no structure the text did not establish.

### 8d. Behaviour over time → `sbm_data.json` + small-multiple charts

Meadows' second layer: patterns, not snapshots. Reconstruct them from git with no checkout using `scripts/sbm_extract.py` (in this skill's folder; copy it beside the output and run it with `python3 -I`):

```
python3 -I scripts/sbm_extract.py <repo> sbm_data.json --config sbm_config.json
```

Write `sbm_config.json` from the stocks chosen in Step 3 (start from `templates/sbm_config.example.json`): `components` (top-level dirs; auto-detected if omitted), `counters` (regex hits in one file, e.g. routes in the hub file, env reads in config), `file_counters` (files under a prefix by name, e.g. distinct AI providers), `line_files` and `line_groups` (line counts of the largest files or a content group), `events` (path → label, dated by first add), `event_grep`, `agent_authors`. What the script does:

- **Snapshots**: the last commit of each ISO week (`git log --format='%H %ad' --date=short --reverse`, keep the last hash per week). Weekly, not monthly: bursts live inside months.
- **Stock levels per snapshot**: `git ls-tree -r -l --full-tree <commit>` lists every tracked file with its byte size. Sum bytes per top-level component, split into source / test / markdown by path pattern. Count the project-specific stock counters chosen in Step 3 with `git show <commit>:<path> | grep -c` (routes in the hub file, env reads in config, migrations, pages, providers, services, workflows, lines of the largest files).
- **Flows between snapshots**: `git log --numstat --format= A..B` for lines added and deleted; subjects for fix vs feat counts; authors for agent-authored commits.
- **Derived**: test share = test bytes / (source + test), docs KB, instrument-of-measurement size (eval or harness code) and its own test count.

Then `scripts/sbm_dashboard.py` draws 8 to 12 small multiples on one shared time axis, each tile: title, unit, a headline (latest value and its change since the reference date you pick, usually the first structural event), the mark, and a reading of at most 15 words. The same 3 to 5 structural events (from 8e) appear as vertical hairlines on every chart so the reader can see what changed after each. One axis per chart, never two scales; two measures of different scale go in two charts or are indexed to a common base. Bars for rates (commits per week), 2 px lines with an end dot for levels, hover tooltip on every point, a legend only when a chart has two series. If a `dataviz` skill is listed, load it before drawing and use its palette and validator.

### 8e. The iceberg dashboard → `SYSTEM_BEHAVIOR.html`

One self-contained HTML file, no libraries, inline SVG, CSS variables with a dark-mode block. Four layers in the book's order, each explaining the one above, each readable at a glance and rewarding inspection:

1. **Events** (what happened): a timeline with numbered marks, ◆ for a rule, loop or boundary change, ● for something that happened; a compact 4-column numbered list beneath; the evidence table collapsed in `<details>`. 10 to 18 events, each dated from `git log --diff-filter=A` on a file or from a dated document.
2. **Behaviour over time** (what patterns): the 8d grid.
3. **Structure** (why): the two 8a/8b diagrams, tabbed and full width, then the loop list with R/B chips: id, name, path, status.
4. **Mental models** (what holds it in place): a three-column table, belief or rule | where it is written | what it does, mixing stated rules with unstated beliefs the charts expose; then the leverage ladder 12 → 2 as a strip with the two or three decisive rungs outlined.

Close with the Step 9 questions in two columns and the hypothesis in a callout. Density rules: every number is `[seen]` or labelled `[inferred]`; readings ≤ 15 words; no paragraph over three lines; hover carries detail, `<details>` carries evidence, nothing is explained twice. Build it with the shipped script, copied beside the output so it can be re-run next month and the behaviour layer updates itself:

```
python3 -I scripts/sbm_dashboard.py sbm_data.json sbm_content.json SYSTEM_BEHAVIOR.html SYSTEM_BEHAVIOR-stocks-flows.svg SYSTEM_BEHAVIOR-loops.svg
```

`sbm_content.json` is the curated layer (start from `templates/sbm_content.example.json`): title, `reference_date` for the "since" deltas, `structural_markers` (3 to 5 dates drawn on every chart), `events`, `charts` (each names a series key from `sbm_data.json` or a derived one: `src_kb:<component>`, `test_kb:<component>`, `md_kb:<component>`, `test_share:<component>`, `code_kb`, `docs_kb`), `loops`, `mental_models`, `leverage`, `questions`, `hypothesis`. Every reading in it must trace to Steps 2 to 7.

### 8f. Check the dashboard

Screenshot it with headless Chrome if present (`google-chrome --headless=new --no-sandbox --window-size=1240,3000 --screenshot=out.png file:///path`) and look at the crops: label pile-ups on the timeline, wrapped headlines, unreadable diagrams. Two passes, then stop. If the session has an artifact tool, publish the HTML so the person can open it in place; always also leave the file in the project.

## Step 9 — Questions to carry forward

End with 8 to 15 questions, each tied to a finding and tagged with the leverage point it targets. Good questions are ones the repo alone cannot answer and that, if answered, would change what to build next. Examples of the form (adapt to the evidence, do not copy):

- "The suite has N skipped tests, the oldest skipped 14 months ago `[seen]`. What does the team believe the test suite is for, and does its current state match that belief?" (goal / drift to low performance)
- "Bugs are detected mostly in production `[inferred from absence of integration tests and presence of error-reporting SDK]`. What would it take to move detection one stage earlier, and what delay would that remove?" (delays)
- "`core/utils` changed in 38% of commits `[seen]`. Who owns it, and what would happen if nobody were allowed to add to it for a quarter?" (tragedy of the commons / structure)

Close with one paragraph on which single structural change would most alter the dominant loop, framed as a hypothesis to test, not a recommendation.

## Output

Write the result as `SYSTEM_BEHAVIOR.md` in the project's `docs/` folder if one exists, otherwise at the project root, unless the user asks for another location or format, with the two SVGs (and PNGs when rendered), `SYSTEM_BEHAVIOR.html`, and the generator files (`sbm_extract.py`, `sbm_dashboard.py`, `sbm_data.json`, `sbm_content.json`) beside it. Structure the markdown with the section headings from Steps 2 to 9; the dashboard is the glance view, the markdown is the full argument. Embed the stock-and-flow diagram at the end of the Stocks section and the causal-loop diagram at the start of the Feedback loops section, each with two or three sentences saying what is visible at a glance that the table only states. Check the project's `.gitignore` and tell the person if the output files would be ignored. Keep it readable in one sitting: aim for 2 to 5 pages; put long raw counts in an appendix. Include a one-line legend for `[seen]` / `[inferred]` at the top and a short "Evidence gathered" appendix listing the commands run and files examined so the reader can reproduce or challenge the analysis.

After writing, publish or send the dashboard, send the PNG renders (or the SVGs if no converter existed) together with the document, and give the user a 3 to 5 sentence summary: the revealed purpose, the dominant loop, the most clearly evidenced trap, and the first question worth asking. Offer to go deeper on any one loop or to re-run after they supply runtime data (metrics, issue tracker export, incident history), which upgrades many `[inferred]` claims to `[seen]`.