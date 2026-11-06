#!/usr/bin/env python3
"""Behaviour-over-time extraction for the system-behavior-map skill.

Reconstructs weekly stock levels and flows from git history with no checkout.

Usage:
    python3 -I sbm_extract.py <repo> <out.json> [--config sbm_config.json]

Snapshots are the last commit of each ISO week. For each snapshot:
  * `git ls-tree -r -l --full-tree` gives every tracked file and its size, summed per
    top-level component and split into src / test / md by path pattern;
  * project-specific counters (routes, env reads, ...) come from `git show` + regex;
  * flows since the previous snapshot come from `git log --numstat` and commit subjects.

Config (all keys optional):
{
  "components": ["backend", "frontend"],           # default: top-level dirs holding code
  "code_ext": [".go", ".ts", ".tsx", ".py"],         # default: common languages
  "counters": {                                      # name -> {path, regex}; count of regex matches
    "routes": {"path": "backend/cmd/api/main.go", "regex": "\\\\.(Get|Post|Put|Delete|Patch)\\\\("}
  },
  "file_counters": {                                 # name -> count files under prefix whose basename matches
    "providers": {"prefix": "backend/internal/infrastructure/ai/", "name_regex": "^(openai|gemini|anthropic)", "distinct": true}
  },                                                 # distinct: count distinct regex matches instead of files
  "line_files": {"hub_lines": "backend/cmd/api/main.go"},        # name -> path, line count
  "line_groups": {"content_lines": ["a.ts", "b.ts"]},            # name -> paths, summed line count
  "events": {"ops/postmortems/first.md": "First postmortem"},    # path -> label; dated by first add
  "event_grep": ["revert", "hotfix", "rollback"],                # commit subjects worth listing
  "agent_authors": ["Claude", "github-actions[bot]"]             # authors counted as agents
}
"""
import collections, datetime as dt, json, re, subprocess, sys

args = sys.argv[1:]
cfg = {}
if "--config" in args:
    i = args.index("--config"); cfg = json.load(open(args[i + 1])); del args[i:i + 2]
repo, out = args[0], args[1]

def git(*a, check=True):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, errors="replace")
    return r.stdout if (r.returncode == 0 or not check) else ""

CODE = tuple(cfg.get("code_ext", [".go", ".ts", ".tsx", ".js", ".mjs", ".py", ".rb", ".rs", ".java", ".kt", ".cs", ".php", ".sh"]))
TESTPAT = re.compile(r"(_test\.go$|\.test\.[jt]sx?$|\.spec\.[jt]sx?$|/__tests__/|/tests?/|(^|/)test_[^/]*\.py$|_spec\.rb$|Tests?\.(java|kt|cs)$)")
AGENTS = set(cfg.get("agent_authors", ["Claude"]))

# ---- snapshots: last commit per ISO week
weeks = collections.OrderedDict()
for line in git("log", "--format=%H %ad", "--date=short", "--reverse").splitlines():
    if not line.strip(): continue
    h, d = line.split()
    y, w, _ = dt.date.fromisoformat(d).isocalendar()
    weeks[(y, w)] = (h, d)
snaps = list(weeks.values())
if not snaps: sys.exit("no commits found")

# ---- components: configured, else top-level dirs that hold code at HEAD
head_tree = git("ls-tree", "-r", "--name-only", "--full-tree", snaps[-1][0]).splitlines()
components = cfg.get("components") or sorted({p.split("/")[0] for p in head_tree if "/" in p and p.endswith(CODE)})

def count_lines(commit, path):
    s = git("show", f"{commit}:{path}", check=False)
    return s.count("\n") if s else 0

series, prev = [], None
for h, d in snaps:
    comp = collections.defaultdict(lambda: {"src": 0, "test": 0, "md": 0})
    migrations = workflows = pages = 0
    fc = {name: set() if spec.get("distinct") else 0 for name, spec in cfg.get("file_counters", {}).items()}
    for row in git("ls-tree", "-r", "-l", "--full-tree", h).splitlines():
        if not row.strip(): continue
        meta, path = row.split("\t", 1)
        parts = meta.split(); size = int(parts[3]) if parts[3] != "-" else 0
        top = path.split("/")[0] if "/" in path else "root"
        if path.endswith(".sql") and "migration" in path.lower(): migrations += 1
        if path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml")): workflows += 1
        if re.search(r"/page\.(tsx|jsx|vue|svelte)$", path): pages += 1
        for name, spec in cfg.get("file_counters", {}).items():
            if path.startswith(spec["prefix"]):
                m = re.search(spec["name_regex"], path.rsplit("/", 1)[-1])
                if m:
                    if spec.get("distinct"): fc[name].add(m.group(0))
                    else: fc[name] += 1
        if path.endswith(".md"): comp[top]["md"] += size
        elif path.endswith(CODE) and top in components:
            comp[top]["test" if TESTPAT.search(path) else "src"] += size
    row = {"date": d, "commit": h[:7], "migrations": migrations, "workflows": workflows, "pages": pages}
    row.update({name: (len(v) if isinstance(v, set) else v) for name, v in fc.items()})
    for name, spec in cfg.get("counters", {}).items():
        row[name] = len(re.findall(spec["regex"], git("show", f"{h}:{spec['path']}", check=False), re.M))
    for name, path in cfg.get("line_files", {}).items():
        row[name] = count_lines(h, path)
    for name, paths in cfg.get("line_groups", {}).items():
        row[name] = sum(count_lines(h, p) for p in paths)
    compose = git("show", f"{h}:docker-compose.yml", check=False) or git("show", f"{h}:compose.yml", check=False)
    row["compose_services"] = len(re.findall(r"^  [a-z0-9_-]+:\s*$", compose, re.M))
    # flows since previous snapshot
    rng = [f"{prev}..{h}"] if prev else ["-1", h]
    add = dele = 0
    for line in git("log", "--numstat", "--format=", *rng).splitlines():
        p = line.split("\t")
        if len(p) == 3 and p[0].isdigit() and p[1].isdigit(): add += int(p[0]); dele += int(p[1])
    subjects = [s for s in git("log", "--format=%s", *rng).splitlines() if s.strip()]
    authors = git("log", "--format=%an", *rng).splitlines()
    row.update({"commits": len(subjects), "added": add, "deleted": dele,
                "fix": sum(1 for s in subjects if re.search(r"\bfix", s, re.I)),
                "feat": sum(1 for s in subjects if re.search(r"^feat|\badd\b", s, re.I)),
                "agent_commits": sum(1 for a in authors if a.strip() in AGENTS),
                "components": dict(comp)})
    series.append(row); prev = h

# ---- events
def first_added(path):
    s = git("log", "--diff-filter=A", "--format=%ad", "--date=short", "--", path).strip().splitlines()
    return s[-1] if s else None
events = []
for path, label in cfg.get("events", {}).items():
    d = first_added(path)
    if d: events.append({"date": d, "label": label, "kind": "structure", "evidence": path})
greps = cfg.get("event_grep", ["revert", "hotfix", "rollback"])
if greps:
    gargs = [x for g in greps for x in ("--grep", g)]
    for line in git("log", "--format=%h %ad %s", "--date=short", "-i", *gargs).splitlines():
        if line.strip():
            h7, d, s = line.split(" ", 2)
            events.append({"date": d, "label": s[:90], "kind": "event", "evidence": h7})
events.sort(key=lambda e: e["date"])

json.dump({"generated": dt.date.today().isoformat(), "head": snaps[-1][0][:7], "components": components,
           "series": series, "events": events}, open(out, "w"), indent=1)
print(f"{len(series)} snapshots, {len(events)} candidate events, components: {', '.join(components)}")
