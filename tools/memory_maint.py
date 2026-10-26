#!/usr/bin/env python3
"""POHA — memory maintenance tool (Memory v2: budgets, journal, lens lifecycle).

Stdlib only. Runs from the linked Linux shell (python3 $J/tools/memory_maint.py <sub>)
or Windows Python (py tools\\memory_maint.py <sub>).

Subcommands: check, rotate, journal-diff, index, all, section, lookback, next-id,
run-note, novelty, verify.  Docs: docs/memory-system.md. Contract: tools/memory_contract.json.

Safety: never reads or writes memory/private/; never deletes a file; every rewrite is
atomic (tmp + os.replace) and backed up to logs/maint/backup/<dow>/ first.

Exit codes: 0 clean · 1 warnings · 2 violations · 3 novelty near-duplicate · 4 fatal.
"""
import argparse
import collections
import datetime as dt
import difflib
import glob
import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

# ----------------------------------------------------------------------------- constants
COMMIT_COLS = ["ID", "Slug", "What", "Who", "Due", "State", "Opened", "Touched", "Note"]
COMMIT_SECTIONS = ["Pinned projects", "Open — I Said I Would", "Open — They Said They Would", "Closed (last 7 days)"]
OPEN_STATES = {"PENDING", "CALENDAR NEEDED", "SCHEDULED", "URGENT_SCHEDULED", "PARKED_GSD", "IN PROGRESS", "WAITING", "DELEGATED", "BLOCKED", "CHRONIC"}
CLOSED_STATES = {"DONE", "DROPPED", "MOOT", "ACCEPTED", "SUPERSEDED"}
EVENTS = ["opened", "closed", "state", "decision", "fact", "calendar", "sent", "incident", "evidence", "insight", "review"]
JOURNAL_RE = re.compile(
    r"^- (\d{4}-\d\d-\d\d) (\d\d:\d\d) · ([a-z0-9$-]+) · ([^·]+?) · (" + "|".join(EVENTS) + r") · (.+?) · ((?:#[a-z0-9-]+ ?)+)$")
INSIGHT_HEAD_RE = re.compile(r"^### (I-(\d{4})) · (.{1,200})$")
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
FORBIDDEN = [
    (re.compile(r"^\*\*(Evening|Morning|Commitment-to-Calendar|GSD( Hour)?|Weekly [Rr]eview|Catch-up|Trip-planning)[^*]*(note|run|brief|sweep|pass)[^*]*\*\*"), "run note in curated file"),
    (re.compile(r"^\*Prior — "), "'Prior — Last updated' line"),
    (re.compile(r"STATUS [A-Z][a-z]{2} \d{1,2}"), "dated STATUS line"),
    (re.compile(r"\bDay \d+\b"), "day counter 'Day N'"),
    (re.compile(r"\b\d+ ?d (slipped|overdue|unsent)\b"), "day counter 'Nd slipped'"),
    (re.compile(r"^## Weekly Review — "), "weekly review block in curated file"),
    (re.compile(r"\bnow \d+ days\b"), "day counter 'now N days'"),
]
STOPWORDS = set("""a about above after again against all am an and any are aren as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have having he her here hers
herself him himself his how i if in into is it its itself just let me more most my myself no nor not now of off on once only
or other our ours ourselves out over own same she should so some such than that the their theirs them themselves then there
these they this those through to too under until up very was we were what when where which while who whom why will with would
you your yours yourself yourselves lens one two also still even every never always get got gets thing things
same day days week weeks today tonight""".split())
EXIT_OK, EXIT_WARN, EXIT_VIOL, EXIT_DUP, EXIT_FATAL = 0, 1, 2, 3, 4


class Fatal(Exception):
    pass


# ----------------------------------------------------------------------------- context
class Ctx:
    def __init__(self, args):
        self.args = args
        root = getattr(args, "root", None) or os.environ.get("POHA_ROOT") or os.environ.get("EXO_ROOT") or str(Path(__file__).resolve().parent.parent)
        self.root = Path(root).resolve()
        cpath = self.root / "tools" / "memory_contract.json"
        if not cpath.exists() or not (self.root / "memory").is_dir():
            raise Fatal(f"bad root {self.root}: needs tools/memory_contract.json and memory/")
        try:
            self.contract = json.loads(cpath.read_text(encoding="utf-8-sig"))
        except Exception as e:
            raise Fatal(f"contract unreadable: {e}")
        for k in ["version", "never_touch", "files", "logs", "rotation", "tags", "schedule", "read_plan"]:
            if k not in self.contract:
                raise Fatal(f"contract missing key {k}")
        # Timezone: contract "timezone" (IANA name, e.g. "Europe/London"); empty = this machine's local time.
        tzname = (self.contract.get("timezone") or "").strip()
        tz = None
        if tzname and ZoneInfo:
            try:
                tz = ZoneInfo(tzname)
            except Exception:
                raise Fatal(f"unknown timezone in contract: {tzname!r}")
        self.tzl = (dt.datetime.now(tz).strftime("%Z") or tzname) if tz else "local"
        if getattr(args, "now", None):
            self.now = dt.datetime.strptime(args.now, "%Y-%m-%d %H:%M")
        else:
            self.now = dt.datetime.now(tz).replace(tzinfo=None) if tz else dt.datetime.now()
        self.today = self.now.date()
        self.dry = bool(getattr(args, "dry_run", False))
        self.job = getattr(args, "job", None) or "manual"
        self.backed_up = set()
        self.findings = []  # (sev, code, file, line, msg)
        self.rotated = []
        self.auto_journal = []
        self.writes = []

    # ---- paths
    def rel(self, p):
        try:
            return Path(p).resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(p)

    def guard(self, p, write=False):
        r = self.rel(p)
        for pre in self.contract["never_touch"]:
            if r.startswith(pre) or ("/" + pre) in ("/" + r):
                self.findings.append(("V", "P0", r, 0, "private path touched"))
                raise Fatal(f"never-touch path refused: {r}")
        return r

    def path(self, rel):
        p = self.root / rel
        self.guard(p)
        return p

    # ---- io
    def read(self, rel, default=None):
        p = self.path(rel) if not isinstance(rel, Path) else rel
        self.guard(p)
        if not p.exists():
            return default
        return p.read_text(encoding="utf-8-sig")

    def backup(self, p):
        r = self.rel(p)
        if r in self.backed_up or not p.exists() or self.dry:
            return
        dow = self.today.strftime("%a").lower()
        b = self.root / "logs" / "maint" / "backup" / dow / r
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, b)
        self.backed_up.add(r)

    def write(self, rel, text):
        p = self.path(rel) if not isinstance(rel, Path) else rel
        r = self.guard(p, write=True)
        if self.dry:
            self.writes.append(("rewrite", r, len(text.encode())))
            return
        old = p.read_bytes() if p.exists() else None
        crlf = old is not None and b"\r\n" in old[:4000]
        data = text.replace("\r\n", "\n")
        if crlf:
            data = data.replace("\n", "\r\n")
        if old is not None and old == data.encode("utf-8"):
            return
        self.backup(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
        self.writes.append(("rewrite", r, len(data.encode())))

    def append(self, rel, text, header=None):
        p = self.path(rel) if not isinstance(rel, Path) else rel
        r = self.guard(p, write=True)
        if self.dry:
            self.writes.append(("append", r, len(text.encode())))
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        new = not p.exists() or p.stat().st_size == 0
        with open(p, "a", encoding="utf-8", newline="") as f:
            if new and header:
                f.write(header.rstrip("\n") + "\n\n")
            f.write(text if text.endswith("\n") else text + "\n")
        self.writes.append(("append", r, len(text.encode())))

    # ---- state
    def state(self):
        if not hasattr(self, "_state"):
            raw = self.read("logs/maint/state.json")
            try:
                self._state = json.loads(raw) if raw else {}
            except Exception:
                self._state = {}
        return self._state

    def save_state(self):
        self.write("logs/maint/state.json", json.dumps(self.state(), indent=1, sort_keys=True) + "\n")

    def add(self, sev, code, f, line, msg):
        self.findings.append((sev, code, f, line, msg))


# ----------------------------------------------------------------------------- lock
class Lock:
    def __init__(self, ctx):
        self.ctx = ctx
        self.p = ctx.root / "logs" / "maint" / ".lock"

    def __enter__(self):
        if self.ctx.dry:
            return self
        self.p.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + 60
        while True:
            held = None
            if self.p.exists():
                try:
                    held = json.loads(self.p.read_text() or "{}")
                except Exception:
                    held = None
            if held and held.get("pid") and held.get("pid") != os.getpid():
                started = dt.datetime.fromisoformat(held.get("started"))
                age = (dt.datetime.now() - started).total_seconds()
                if age < 600:
                    if time.time() > deadline:
                        raise Fatal(f"lock held by {held.get('job')} since {held.get('started')}")
                    time.sleep(2)
                    continue
            break
        self.p.write_text(json.dumps({"pid": os.getpid(), "job": self.ctx.job, "started": dt.datetime.now().isoformat(timespec="seconds")}))
        return self

    def __exit__(self, *a):
        if not self.ctx.dry:
            self.p.write_text("{}")


# ----------------------------------------------------------------------------- helpers
def norm_heading(s):
    s = re.sub(r"^#+\s*", "", s)
    s = re.sub(r"[^\w\s—–-]", "", s, flags=re.U)
    return re.sub(r"\s+", " ", s).strip().lower()


def comment_mask(lines):
    """Indexes of lines inside <!-- ... --> blocks, so templates' format examples are never parsed as data."""
    masked, inside = set(), False
    for i, line in enumerate(lines):
        if inside or "<!--" in line:
            masked.add(i)
        if "<!--" in line:
            inside = True
        if "-->" in line:
            inside = False
    return masked


def headings(text):
    out = []
    in_code = False
    lines = text.split("\n")
    masked = comment_mask(lines)
    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_code = not in_code
        if in_code or i in masked:
            continue
        m = re.match(r"^(#{1,6}) (.+)$", line)
        if m:
            out.append((len(m.group(1)), i, m.group(2).strip()))
    return out


def section_block(text, heading, level=None):
    """Return (start_line, end_line_exclusive, lines) for the heading block or None."""
    lines = text.split("\n")
    hs = headings(text)
    want = norm_heading(heading)
    cands = [h for h in hs if (level is None or h[0] == level)]
    hit = [h for h in cands if norm_heading(h[2]) == want]
    if not hit:
        pref = [h for h in cands if norm_heading(h[2]).startswith(want)]
        if len(pref) == 1:
            hit = pref
    if not hit:
        return None
    lvl, start, _ = hit[0]
    end = len(lines)
    for l2, i2, _ in hs:
        if i2 > start and l2 <= lvl:
            end = i2
            break
    return start, end, lines[start:end]


def parse_date(s):
    try:
        return dt.date.fromisoformat(s.strip()[:10])
    except Exception:
        return None


def header_date(text):
    """First '*Last updated: YYYY-MM-DD (...)' (or looser) line within the first 15 lines."""
    for i, line in enumerate(text.split("\n")[:15]):
        m = re.match(r"^\*?Last updated:\s*(\d{4}-\d{2}-\d{2})\s*(\(([^)]*)\))?", line.strip())
        if m:
            return parse_date(m.group(1)), (m.group(3) or ""), i, bool(re.match(r"^\*Last updated: \d{4}-\d\d-\d\d \([^)]+\)[^*]*\*", line.strip()))
    return None, "", -1, False


def contract_files(ctx):
    out = []
    for pat, spec in ctx.contract["files"].items():
        if "*" in pat:
            for p in sorted(glob.glob(str(ctx.root / pat))):
                r = ctx.rel(p)
                if any(r.startswith(n) for n in ctx.contract["never_touch"]):
                    continue
                out.append((r, spec, pat))
        else:
            out.append((pat, spec, pat))
    return out


def table_cells(line):
    s = line.strip()
    if not s.startswith("|"):
        return None
    s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def is_sep_row(line):
    return bool(re.match(r"^\|[\s:|-]+\|?\s*$", line.strip()))


def tokens(text):
    t = text.lower()
    t = re.sub(r"\d+", " n ", t)
    t = re.sub(r"[^a-z\s]", " ", t)
    out = []
    for w in t.split():
        if w in STOPWORDS or len(w) < 3:
            continue
        for suf in ("ing", "ed", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


def similarity(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    sa, sb = set(ta), set(tb)
    jac = len(sa & sb) / len(sa | sb)
    ca, cb = collections.Counter(ta), collections.Counter(tb)
    dot = sum(ca[w] * cb[w] for w in sa & sb)
    cos = dot / (math.sqrt(sum(v * v for v in ca.values())) * math.sqrt(sum(v * v for v in cb.values())))
    return 0.5 * jac + 0.5 * cos


def quarter_of(d):
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def prev_quarter(q):
    y, n = int(q[:4]), int(q[-1])
    return f"{y - 1}-Q4" if n == 1 else f"{y}-Q{n - 1}"


# ----------------------------------------------------------------------------- commitments model
class Commitments:
    def __init__(self, text):
        self.text = text
        self.lines = text.split("\n")
        self.sections = {}  # name -> (start, end)
        hs = [(l, i, t) for (l, i, t) in headings(text) if l == 2]
        for idx, (l, i, t) in enumerate(hs):
            end = hs[idx + 1][1] if idx + 1 < len(hs) else len(self.lines)
            self.sections[t.strip()] = (i, end)
        self.order = [t.strip() for (_, _, t) in hs]

    def rows(self, section):
        if section not in self.sections:
            return []
        s, e = self.sections[section]
        out = []
        header_seen = False
        for i in range(s + 1, e):
            line = self.lines[i]
            cells = table_cells(line)
            if cells is None or is_sep_row(line):
                continue
            if not header_seen and cells and cells[0] == "ID":
                header_seen = True
                continue
            row = dict(zip(COMMIT_COLS, cells + [""] * (9 - len(cells))))
            row["_line"] = i
            row["_ncells"] = len(cells)
            row["_section"] = section
            out.append(row)
        return out

    def all_rows(self):
        out = []
        for s in COMMIT_SECTIONS[1:]:
            out += self.rows(s)
        return out

    @staticmethod
    def fmt(row):
        return "| " + " | ".join(row.get(c, "") for c in COMMIT_COLS) + " |"

    def rebuild(self, section_rows):
        """section_rows: dict section-> list of rows. Rewrites the table rows of those sections."""
        lines = self.lines[:]
        # process sections bottom-up so indexes stay valid
        for sec in sorted(section_rows, key=lambda s: -self.sections.get(s, (0, 0))[0]):
            if sec not in self.sections:
                continue
            s, e = self.sections[sec]
            body = lines[s + 1:e]
            # keep everything up to and including the table separator; drop old data rows; keep trailing non-table lines
            keep_head, trail = [], []
            phase = 0
            for ln in body:
                c = table_cells(ln)
                if phase == 0:
                    keep_head.append(ln)
                    if c is not None and is_sep_row(ln):
                        phase = 1
                elif phase == 1:
                    if c is not None:
                        continue
                    phase = 2
                    trail.append(ln)
                else:
                    trail.append(ln)
            if phase == 0:  # no table yet -> add header
                keep_head += ["| " + " | ".join(COMMIT_COLS) + " |", "|" + "|".join(["----"] * 9) + "|"]
            new_body = keep_head + [self.fmt(r) for r in section_rows[sec]] + (trail if trail else [""])
            lines[s + 1:e] = new_body
        return "\n".join(lines)


def commitments_archive_ids(ctx):
    ids = set()
    for p in glob.glob(str(ctx.root / "memory/archive/commitments/*.md")):
        for m in re.finditer(r"^\| (C-\d{4}) \|", Path(p).read_text(encoding="utf-8-sig"), re.M):
            ids.add(m.group(1))
    return ids


# ----------------------------------------------------------------------------- insights model
def parse_meta(line):
    s = line.strip()
    if not (s.startswith("*") and s.endswith("*")):
        return None
    s = s.strip("*").strip()
    parts = [p.strip() for p in s.split(" · ")]
    meta = {"_raw": line}
    m = re.match(r"^Added (\d{4}-\d\d-\d\d)(~?) \(([^)]*)\)$", parts[0])
    if not m:
        return None
    meta["added"] = m.group(1)
    meta["approx"] = bool(m.group(2))
    meta["job"] = m.group(3)
    for p in parts[1:]:
        if ":" not in p:
            return None
        k, v = p.split(":", 1)
        meta[k.strip()] = v.strip()
    if "subject" not in meta or "evidence" not in meta or "aliases" not in meta:
        return None
    meta["subjects"] = [t.strip() for t in meta["subject"].split(",") if t.strip()]
    try:
        meta["evidence_n"] = int(meta["evidence"])
    except ValueError:
        return None
    return meta


def fmt_meta(meta):
    parts = [f"Added {meta['added']}{'~' if meta.get('approx') else ''} ({meta['job']})",
             f"subject: {', '.join(meta['subjects'])}", f"evidence: {meta['evidence_n']}"]
    for k in ("supersedes", "superseded-by", "status"):
        if meta.get(k):
            parts.append(f"{k}: {meta[k]}")
    parts.append(f"aliases: {meta.get('aliases') or '—'}")
    return "*" + " · ".join(parts) + "*"


class Insights:
    def __init__(self, text):
        self.text = text
        self.lines = text.split("\n")
        self.entries = []
        self.active_start = None
        for i, l in enumerate(self.lines):
            if l.strip() == "## Active":
                self.active_start = i
                break
        cur = None
        masked = comment_mask(self.lines)
        for i, l in enumerate(self.lines):
            if i in masked:
                if cur:  # a comment block ends the entry above it
                    cur["end"] = i
                    self.entries.append(cur)
                    cur = None
                continue
            m = INSIGHT_HEAD_RE.match(l)
            if m:
                if cur:
                    cur["end"] = i
                    self.entries.append(cur)
                cur = {"id": m.group(1), "title": m.group(3), "start": i}
            elif cur and re.match(r"^#{1,3} ", l):
                cur["end"] = i
                self.entries.append(cur)
                cur = None
        if cur:
            cur["end"] = len(self.lines)
            self.entries.append(cur)
        for e in self.entries:
            body_lines = self.lines[e["start"] + 1:e["end"]]
            nb = [x for x in body_lines if x.strip()]
            e["meta"] = parse_meta(nb[0]) if nb else None
            e["body"] = "\n".join(nb[1:]).strip() if nb else ""

    def active(self):
        return [e for e in self.entries if e["meta"] and not e["meta"].get("status")]


def archive_insight_entries(ctx, quarters=None):
    out = []
    files = sorted(glob.glob(str(ctx.root / "memory/archive/insights/20*-Q*.md")))
    for p in files:
        q = Path(p).stem
        if quarters and q not in quarters:
            continue
        ins = Insights(Path(p).read_text(encoding="utf-8-sig"))
        for e in ins.entries:
            e["file"] = ctx.rel(p)
            out.append(e)
    return out


# ----------------------------------------------------------------------------- journal
def journal_files(ctx):
    return sorted(glob.glob(str(ctx.root / "memory/journal/20??-??.md")))


def journal_lines(ctx, months=None):
    out = []
    for p in journal_files(ctx):
        mo = Path(p).stem
        if months and mo not in months:
            continue
        for i, l in enumerate(Path(p).read_text(encoding="utf-8-sig").split("\n")):
            m = JOURNAL_RE.match(l)
            if m:
                out.append({"date": m.group(1), "time": m.group(2), "job": m.group(3), "ref": m.group(4).strip(),
                            "event": m.group(5), "text": m.group(6), "tags": m.group(7).split(), "line": l,
                            "file": ctx.rel(p), "n": i + 1})
    return out


def journal_append(ctx, lines_by_date):
    """lines_by_date: list of (date_str, line). Inserts under ## date heading in the month file (append-only within month)."""
    by_month = collections.defaultdict(list)
    for d, l in lines_by_date:
        by_month[d[:7]].append((d, l))
    for mo, items in by_month.items():
        rel = f"memory/journal/{mo}.md"
        p = ctx.root / rel
        text = p.read_text(encoding="utf-8-sig") if p.exists() else (
            f"# Journal — {mo}\n\n> Append-only. One line per event. Format: `- YYYY-MM-DD HH:MM · <job> · <ref> · <event> · <text ≤200 chars> · #tag [#tag]`. Steady state is not an event.\n")
        lines = text.rstrip("\n").split("\n")
        for d, l in sorted(items, key=lambda x: x[1]):
            h = f"## {d}"
            if h not in lines:
                # place heading in chronological position among existing day headings
                idxs = [(i, x[3:]) for i, x in enumerate(lines) if re.match(r"^## \d{4}-\d\d-\d\d$", x)]
                later = [i for i, dd in idxs if dd > d]
                if later:
                    lines[later[0]:later[0]] = [h, l, ""]
                    continue
                lines += ["", h]
                lines.append(l)
                continue
            # insert at end of that day's block
            i = lines.index(h) + 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            j = i
            while j - 1 > lines.index(h) and lines[j - 1].strip() == "":
                j -= 1
            lines.insert(j, l)
        ctx.write(rel, "\n".join(lines) + "\n")


def jline(ctx, job, ref, event, text, tags):
    text = re.sub(r"\s+", " ", text.replace("·", "-")).strip()[:200]
    tags = [t for t in tags if t] or ["#review"]
    return f"- {ctx.now:%Y-%m-%d %H:%M} · {job} · {ref} · {event} · {text} · {' '.join(tags)}"


def infer_tags(ctx, text):
    t = text.lower()
    tags = []
    for tag in ctx.contract["tags"]:
        w = tag[1:]
        if w in ("review", "migrated"):
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", t):
            tags.append(tag)
    # generic defaults; add your own in tools/memory_contract.json > tag_keywords {"#tag": "regex"}
    kw = [(r"\bdad\b|\bmom\b|parents?", "#parents"), (r"invoice|pay |paid|\$\d", "#money"),
          (r"bloodwork|doctor|health", "#health")]
    kw += [(rx, tag) for tag, rx in ctx.contract.get("tag_keywords", {}).items()]
    for rx, tag in kw:
        if re.search(rx, t) and tag not in tags:
            tags.append(tag)
    return tags[:3]


# ----------------------------------------------------------------------------- cron
def cron_slots(expr, start, end):
    """Yield datetimes between start and end matching a 5-field cron (minute hour dom month dow)."""
    def field(f, lo, hi):
        vals = set()
        for part in f.split(","):
            step = 1
            if "/" in part:
                part, s = part.split("/")
                step = int(s)
            if part == "*":
                a, b = lo, hi
            elif "-" in part:
                a, b = map(int, part.split("-"))
            else:
                a = b = int(part)
            vals.update(range(a, b + 1, step))
        return vals
    mi, hr, dom, mon, dow = expr.split()
    M, H, D, MO, W = field(mi, 0, 59), field(hr, 0, 23), field(dom, 1, 31), field(mon, 1, 12), field(dow, 0, 6)
    d = start.date()
    while d <= end.date():
        cw = (d.weekday() + 1) % 7
        if d.day in D and d.month in MO and (cw in W or dow == "*") and (dom == "*" or d.day in D):
            for h in sorted(H):
                for m in sorted(M):
                    t = dt.datetime(d.year, d.month, d.day, h, m)
                    if start <= t <= end:
                        yield t
        d += dt.timedelta(days=1)


# ----------------------------------------------------------------------------- run notes
def run_note_entries(ctx, months=None):
    out = []
    for p in sorted(glob.glob(str(ctx.root / "logs/run-notes/20??-??.md"))):
        mo = Path(p).stem
        if months and mo not in months:
            continue
        text = Path(p).read_text(encoding="utf-8-sig")
        cur = None
        for l in text.split("\n"):
            m = re.match(r"^## (R-(\d{8})-(\d{4})-(.)) · (\d{4}-\d\d-\d\d \d\d:\d\d)(?: [A-Za-z][A-Za-z0-9+:/_-]*)? · ([a-z0-9$-]+)(.*)$", l)
            if m:
                if cur:
                    out.append(cur)
                cur = {"id": m.group(1), "ts": dt.datetime.strptime(m.group(5), "%Y-%m-%d %H:%M"), "job": m.group(6),
                       "head": l, "body": [], "file": ctx.rel(p)}
            elif cur is not None:
                cur["body"].append(l)
        if cur:
            out.append(cur)
    return out


# ============================================================================= CHECK
def do_check(ctx, enforce=False, quiet=False):
    ctx.findings = [f for f in ctx.findings if f[1] == "P0"]
    job = ctx.args.job if getattr(ctx.args, "job", None) else None
    tags = set(ctx.contract["tags"])
    adopted = parse_date(ctx.contract.get("adopted", "2000-01-01"))

    # C1, C2, C3, C7 over curated files
    for rel, spec, pat in contract_files(ctx):
        p = ctx.root / rel
        if not p.exists():
            ctx.add("W", "C0", rel, 0, "contract file missing")
            continue
        text = p.read_text(encoding="utf-8-sig")
        size = len(text.encode("utf-8"))
        bud = spec.get("budget")
        owner_match = job is not None and spec.get("owner") == job
        if bud:
            if size > bud:
                ctx.add("V", "C1", rel, 0, f"over budget {size:,}/{bud:,} bytes")
            elif size > 0.8 * bud:
                ctx.add("V" if (enforce and owner_match) else "W", "C1", rel, 0, f"near budget {size:,}/{bud:,} ({100 * size // bud}%)")
        hd, hjob, hline, strict = header_date(text)
        if spec.get("class") in ("H", "Q", "S"):
            if hd is None:
                ctx.add("W", "C3", rel, 0, "no '*Last updated: YYYY-MM-DD (job)*' header in first 15 lines")
            elif not strict:
                ctx.add("W", "C3", rel, hline + 1, "header not in '*Last updated: YYYY-MM-DD (job)*' form")
        mx = spec.get("max_age_days")
        if mx:
            ref = hd or dt.date.fromtimestamp(p.stat().st_mtime)
            if hd is None:
                ctx.add("W", "C2b", rel, 0, "header unparseable — freshness from mtime")
            age = (ctx.today - ref).days
            if age > mx:
                ctx.add("V" if (enforce and owner_match) else "W", "C2", rel, 0, f"🔴 stale {age}d > {mx}d (owner {spec.get('owner')})")
            elif age >= 0.75 * mx:
                ctx.add("W", "C2", rel, 0, f"🟠 aging {age}/{mx}d (owner {spec.get('owner')})")
        if spec.get("class") in ("H", "Q", "S"):
            hot = spec.get("schema") in ("commitments", "insights")
            for i, line in enumerate(text.split("\n")):
                for rx, msg in FORBIDDEN:
                    if msg.startswith("day counter") and not hot:
                        continue
                    if rx.search(line):
                        ctx.add("V", "C7", rel, i + 1, f"forbidden: {msg}: {line[:80]}")
                        break

    check_commitments(ctx)
    check_insights(ctx, tags)
    check_journal(ctx, tags)
    check_runs(ctx, adopted)
    check_private_refs(ctx)
    check_index_hash(ctx)
    check_schemas(ctx)
    return finish_report(ctx, "check", quiet=quiet)


def check_commitments(ctx):
    rel = "memory/commitments.md"
    text = ctx.read(rel)
    if text is None:
        ctx.add("V", "C4", rel, 0, "missing")
        return
    c = Commitments(text)
    present = [s for s in c.order if s in COMMIT_SECTIONS]
    if present != COMMIT_SECTIONS:
        ctx.add("V", "C4", rel, 0, f"sections must be {COMMIT_SECTIONS} in order; found {c.order}")
    arch = commitments_archive_ids(ctx)
    seen, slugs = {}, {}
    for r in c.all_rows():
        ln = r["_line"] + 1
        if r["_ncells"] != 9:
            ctx.add("V", "C4", rel, ln, f"row has {r['_ncells']} cells, need 9")
            continue
        if not re.match(r"^C-\d{4}$", r["ID"]):
            ctx.add("V", "C4", rel, ln, f"bad ID {r['ID']}")
        if r["ID"] in seen:
            ctx.add("V", "C4", rel, ln, f"duplicate ID {r['ID']} (also line {seen[r['ID']]})")
        if r["ID"] in arch:
            ctx.add("V", "C4", rel, ln, f"ID {r['ID']} also in archive/commitments")
        seen[r["ID"]] = ln
        if not re.match(r"^[a-z0-9-]{1,40}$", r["Slug"]):
            ctx.add("V", "C4", rel, ln, f"bad slug '{r['Slug']}'")
        closed = r["_section"] == "Closed (last 7 days)"
        if not closed:
            if r["Slug"] in slugs:
                ctx.add("V", "C4", rel, ln, f"duplicate open slug {r['Slug']}")
            slugs[r["Slug"]] = ln
        if not (r["Due"] == "—" or parse_date(r["Due"])):
            ctx.add("V", "C4", rel, ln, f"bad Due '{r['Due']}'")
        o, t = parse_date(r["Opened"]), parse_date(r["Touched"])
        if not o or not t:
            ctx.add("V", "C4", rel, ln, "Opened/Touched must be YYYY-MM-DD")
        elif not (o <= t <= ctx.today):
            ctx.add("V", "C4", rel, ln, f"need Opened ≤ Touched ≤ today ({o} {t})")
        valid = CLOSED_STATES if closed else OPEN_STATES
        if r["State"] not in valid:
            ctx.add("V", "C4", rel, ln, f"state '{r['State']}' not allowed in {r['_section']}")
        if len(r["Note"]) > 160:
            ctx.add("V", "C4", rel, ln, f"Note {len(r['Note'])} chars > 160")
        if len(r["What"]) > 120:
            ctx.add("V", "C4", rel, ln, f"What {len(r['What'])} chars > 120")
    # pinned blocks
    if "Pinned projects" in c.sections:
        s, e = c.sections["Pinned projects"]
        blocks, cur = [], None
        for i in range(s + 1, e):
            if c.lines[i].startswith("### "):
                cur = [i, []]
                blocks.append(cur)
            elif cur:
                cur[1].append(c.lines[i])
        if len(blocks) > 3:
            ctx.add("V", "C4", rel, s + 1, f"{len(blocks)} pinned projects > 3")
        for i, body in blocks:
            b = "\n".join(body)
            if len(b) > 1500:
                ctx.add("V", "C4", rel, i + 1, f"pinned block {len(b)} chars > 1500")
            if "STATUS " in b:
                ctx.add("V", "C4", rel, i + 1, "pinned block contains STATUS line")
    # C14 orphan table rows
    table_secs = [c.sections[s] for s in COMMIT_SECTIONS[1:] if s in c.sections]
    for i, line in enumerate(c.lines):
        if line.strip().startswith("|") and not any(a < i < b for a, b in table_secs):
            ctx.add("V", "C14", rel, i + 1, "table row outside the worklist tables")


def check_insights(ctx, tags):
    rel = "memory/insights.md"
    spec = ctx.contract["files"][rel]
    text = ctx.read(rel)
    if text is None:
        ctx.add("V", "C5", rel, 0, "missing")
        return
    ins = Insights(text)
    if sum(1 for l in ins.lines if l.strip() == "## Active") != 1:
        ctx.add("V", "C5", rel, 0, "need exactly one '## Active'")
    ids = {}
    for e in archive_insight_entries(ctx):
        ids[e["id"]] = e["file"]
    prev = None
    subj = collections.Counter()
    nactive = 0
    for e in ins.entries:
        ln = e["start"] + 1
        if e["id"] in ids:
            ctx.add("V", "C5", rel, ln, f"{e['id']} also in {ids[e['id']]}")
        ids[e["id"]] = rel
        if len(e["title"]) > 110:
            ctx.add("V", "C5", rel, ln, f"title {len(e['title'])} chars > 110")
        m = e["meta"]
        if not m:
            ctx.add("V", "C5", rel, ln + 1, f"{e['id']}: metadata line missing/invalid")
            continue
        for t in m["subjects"]:
            if t not in tags:
                ctx.add("W", "C5", rel, ln + 1, f"{e['id']}: unknown tag {t}")
        if m.get("status") and m["status"] not in ("retired", "superseded"):
            ctx.add("V", "C5", rel, ln + 1, f"{e['id']}: bad status {m['status']}")
        if not m.get("status"):
            nactive += 1
            subj[m["subjects"][0]] += 1
            if len(e["body"]) > spec.get("max_body_chars", 600):
                ctx.add("V", "C5", rel, ln, f"{e['id']}: body {len(e['body'])} chars > {spec.get('max_body_chars', 600)}")
            if "Lens:" not in e["body"].split("\n")[-1]:
                ctx.add("V", "C5", rel, ln, f"{e['id']}: body must end with 'Lens: …'")
        if prev and m["added"] > prev:
            ctx.add("V", "C5", rel, ln, f"{e['id']}: not newest-first ({m['added']} after {prev})")
        prev = m["added"]
    if nactive > spec.get("max_active", 25):
        ctx.add("V", "C5", rel, 0, f"{nactive} active lenses > {spec.get('max_active', 25)}")
    for s, n in subj.items():
        if n > spec.get("max_per_subject", 3):
            ctx.add("V", "C5", rel, 0, f"subject {s} has {n} active > {spec.get('max_per_subject', 3)}")


def check_journal(ctx, tags):
    lc = ctx.contract["logs"]["memory/journal/"]
    exempt = set(ctx.contract.get("journal_backfill_months", []))
    for p in journal_files(ctx):
        rel = ctx.rel(p)
        mo = Path(p).stem
        text = Path(p).read_text(encoding="utf-8-sig")
        size = len(text.encode())
        if size > lc["hard"]:
            ctx.add("V", "C6", rel, 0, f"journal {size:,} > hard {lc['hard']:,}")
        elif size > lc["soft"] and mo not in exempt:
            ctx.add("W", "C6", rel, 0, f"journal {size:,} > soft {lc['soft']:,}")
        day = None
        in_review = False
        for i, l in enumerate(text.split("\n")):
            if not l.strip() or l.startswith("# ") or l.startswith("> "):
                continue
            m = re.match(r"^## (\d{4}-\d\d-\d\d)$", l)
            if m:
                day = m.group(1)
                in_review = False
                continue
            if l.startswith("  ") and in_review:
                continue
            jm = JOURNAL_RE.match(l)
            if not jm:
                ctx.add("V", "C6", rel, i + 1, f"bad journal line: {l[:80]}")
                continue
            in_review = jm.group(5) == "review"
            if jm.group(1) != day or not jm.group(1).startswith(mo):
                ctx.add("V", "C6", rel, i + 1, f"line date {jm.group(1)} ≠ heading {day} / month {mo}")
            if len(jm.group(6)) > 200 and not in_review:
                ctx.add("W", "C6", rel, i + 1, f"text {len(jm.group(6))} chars > 200")
            for t in jm.group(7).split():
                if t not in tags:
                    ctx.add("W", "C6", rel, i + 1, f"unknown tag {t}")


def check_runs(ctx, adopted):
    start = max(dt.datetime.combine(adopted, dt.time(0, 0)), ctx.now - dt.timedelta(days=7)) if adopted else ctx.now - dt.timedelta(days=7)
    end = ctx.now - dt.timedelta(hours=3)
    files = sorted(glob.glob(str(ctx.root / "logs/run-notes/20??-??.md")))
    if not files:
        # fresh install: missed-run checks start with the first run note, whatever 'adopted' says
        ctx.missed = []
        return
    first = run_note_entries(ctx, {Path(files[0]).stem})
    if first:
        start = max(start, min(e["ts"] for e in first) - dt.timedelta(hours=3))
    entries = run_note_entries(ctx, {start.strftime("%Y-%m"), ctx.now.strftime("%Y-%m")})
    by_job = collections.defaultdict(list)
    for e in entries:
        by_job[e["job"]].append(e["ts"])
    missed_all = []
    for job, sch in ctx.contract["schedule"].items():
        if sch.get("run_note") is False:
            continue
        consecutive = 0
        for slot in cron_slots(sch["cron"], start, end):
            ok = any(abs((t - slot).total_seconds()) <= 3 * 3600 for t in by_job.get(job, []))
            if not ok:
                consecutive += 1
                missed_all.append((job, slot))
                ctx.add("V" if consecutive >= 3 else "W", "C8", "logs/run-notes", 0, f"missed run {job} {slot:%Y-%m-%d %H:%M}")
            else:
                consecutive = 0
    ctx.missed = missed_all
    # C11 / C12
    for e in entries:
        body = "\n".join(e["body"])
        if e["job"] in ("morning", "evening", "weekly") and "- insight:" not in body:
            ctx.add("V", "C12", e["file"], 0, f"{e['id']} missing insight: line")
        if len(e["head"] + body) > 1600 and "migrated from" not in e["head"]:
            ctx.add("W", "C12", e["file"], 0, f"{e['id']} entry > 1,500 chars")
        if "NO BRIEFING FILE" in body:
            ctx.add("W", "C11", e["file"], 0, f"{e['id']} sent without briefing file")


def check_private_refs(ctx):
    pats = re.compile(r"memory/private/|carry-on")
    # mentions of the privacy gate itself are fine ("privacy gate re-verified: nothing from memory/private/")
    ok = re.compile(r"(?i)privacy[ -]gate|gate re-verified|nothing from memory/private|excluded|never read|not indexed|STRICTLY PRIVATE")
    roots = ["memory/journal", "logs/run-notes", "memory/archive"] + ([ctx.contract["briefing_archive"]] if ctx.contract.get("briefing_archive") else [])
    files = [ctx.root / "memory/INDEX.md"]
    for r in roots:
        files += [Path(p) for p in glob.glob(str(ctx.root / r / "**/*.md"), recursive=True)]
    for p in files:
        if not p.exists():
            continue
        rel = ctx.rel(p)
        if rel.startswith("memory/archive/migration-"):
            continue  # originals are verbatim copies; reconcile checks them separately
        for i, l in enumerate(p.read_text(encoding="utf-8-sig", errors="replace").split("\n")):
            if pats.search(l) and not ok.search(l):
                ctx.add("V", "C10", rel, i + 1, "P1 private reference")


def check_index_hash(ctx):
    p = ctx.root / "memory/INDEX.md"
    if not p.exists():
        ctx.add("W", "C9", "memory/INDEX.md", 0, "INDEX missing (run index)")
        return
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if ctx.state().get("index_sha256") and h != ctx.state().get("index_sha256"):
        ctx.add("W", "C9", "memory/INDEX.md", 0, "INDEX hand-edited (regenerated by index)")


def check_schemas(ctx):
    rot = ctx.contract["rotation"]
    t = ctx.read("memory/delegations.md")
    if t is not None:
        for h in ("Open", "Closed (last 14 days)", "Activity log", "Texts"):
            if not section_block(t, h, 2):
                ctx.add("V", "C13", "memory/delegations.md", 0, f"missing section ## {h}")
    w = ctx.read("memory/weekend-prefs.md")
    if w is not None:
        n = len(re.findall(r"^### Venues & Events Discovered \(", w, re.M))
        if n > rot["weekend_discovered_keep_runs"]:
            ctx.add("W", "C13", "memory/weekend-prefs.md", 0, f"{n} Discovered sections > {rot['weekend_discovered_keep_runs']} (rotate pending)")


# ============================================================================= ROTATE
def do_rotate(ctx, only=None):
    rules = set(only.split(",")) if only else None

    def on(r):
        return rules is None or r in rules
    if on("R1") or on("R2") or on("R3"):
        rotate_commitments(ctx, on)
    if on("R4"):
        rotate_insights(ctx)
    if on("R5"):
        rotate_delegations(ctx)
    if on("R6"):
        rotate_weekend(ctx)
    if on("R7"):
        rotate_trends(ctx)
    if on("R8"):
        rotate_health_events(ctx)
    if on("R9"):
        rotate_miss_log(ctx)


def rotate_commitments(ctx, on):
    rel = "memory/commitments.md"
    text = ctx.read(rel)
    if text is None:
        return
    c = Commitments(text)
    rot = ctx.contract["rotation"]
    secs = {s: c.rows(s) for s in COMMIT_SECTIONS[1:] if s in c.sections}
    if not secs:
        return
    changed = False
    jl = []
    closed = secs.get("Closed (last 7 days)", [])
    for s in ("Open — I Said I Would", "Open — They Said They Would"):
        keep = []
        for r in secs.get(s, []):
            o = parse_date(r["Opened"])
            due = parse_date(r["Due"])
            if on("R1") and r["State"] in ("PENDING", "WAITING", "BLOCKED") and o and (ctx.today - o).days >= rot["chronic_after_days"]:
                jl.append((ctx.today.isoformat(), jline(ctx, "maint", f"{r['ID']} (auto)", "state", f"{r['State']}→CHRONIC: {r['What'][:120]}", infer_tags(ctx, r["What"] + " " + r["Note"]))))
                r["State"] = "CHRONIC"
                changed = True
                ctx.rotated.append(("R1 chronic", r["ID"], rel))
            if on("R2") and r["State"] in ("SCHEDULED", "URGENT_SCHEDULED") and due and due < ctx.today - dt.timedelta(days=1):
                r["State"] = "DONE"
                r["Note"] = ("auto: date passed · " + r["Note"])[:160]
                r["Touched"] = ctx.today.isoformat()
                closed.append(r)
                jl.append((ctx.today.isoformat(), jline(ctx, "maint", f"{r['ID']} (auto)", "closed", f"DONE (date passed): {r['What'][:120]}", infer_tags(ctx, r["What"]))))
                changed = True
                ctx.rotated.append(("R2 scheduled-passed", r["ID"], rel))
                continue
            keep.append(r)
        secs[s] = keep
    if on("R3"):
        keepc = []
        for r in closed:
            t = parse_date(r["Touched"])
            if t and t < ctx.today - dt.timedelta(days=rot["commitments_closed_days"]):
                mo = t.strftime("%Y-%m")
                arel = f"memory/archive/commitments/{mo}.md"
                existing = ctx.read(arel, "") or ""
                if f"| {r['ID']} |" not in existing:
                    hdr = f"# Commitments archive — {mo}\n\n| " + " | ".join(COMMIT_COLS) + " |\n|" + "|".join(["----"] * 9) + "|"
                    ctx.append(arel, Commitments.fmt(r), header=hdr)
                ctx.rotated.append(("R3 closed-archive", r["ID"], arel))
                changed = True
            else:
                keepc.append(r)
        closed = keepc
    secs["Closed (last 7 days)"] = closed
    if changed:
        ctx.write(rel, Commitments(text).rebuild(secs))
        if jl:
            journal_append(ctx, jl)
            ctx.auto_journal += [l for _, l in jl]


def rotate_insights(ctx):
    rel = "memory/insights.md"
    text = ctx.read(rel)
    if text is None:
        return
    ins = Insights(text)
    moving = [e for e in ins.entries if e["meta"] and e["meta"].get("status")]
    if not moving:
        return
    lines = ins.lines[:]
    act = {e["id"]: e for e in ins.active()}
    alias_rel = "memory/archive/insights/ALIASES.md"
    aliases = ctx.read(alias_rel, "") or ""
    alines = aliases.split("\n") if aliases else ["# Insight aliases — old heading → Memory v2 ID (appended by memory_maint.py rotate)"]
    for e in moving:
        m = e["meta"]
        q = quarter_of(parse_date(m["added"]))
        arel = f"memory/archive/insights/{q}.md"
        existing = ctx.read(arel, "") or ""
        reason = m["status"] + (f" superseded-by {m['superseded-by']}" if m.get("superseded-by") else "")
        if f"### {e['id']} · " not in existing:
            block = [f"### {e['id']} · {e['title']}", fmt_meta(m), f"*Archived {ctx.today} · reason: {reason}*", e["body"], ""]
            ctx.append(arel, "\n".join(block), header=f"# Insights archive — {q}")
        tgt = m.get("superseded-by", "").strip()
        if tgt in act:
            tm = act[tgt]["meta"]
            tm["evidence_n"] += m["evidence_n"]
            lines[act[tgt]["start"] + 1 + next(i for i, x in enumerate(lines[act[tgt]["start"] + 1:]) if x.strip())] = fmt_meta(tm)
        al = m.get("aliases", "—")
        if al and al != "—":
            for a in [x.strip() for x in al.split(",")]:
                tag = f"{a} → {e['id']}"
                status = f"archived {q} ({reason})"
                found = False
                for i, x in enumerate(alines):
                    if x.startswith(tag + " ") or x == tag:
                        alines[i] = re.sub(r" · (archived .*|active)$", "", x) + " · " + status
                        found = True
                if not found:
                    alines.append(f"{tag} · {m['added']} · \"{e['title'][:60]}\" · {status}")
        ctx.rotated.append(("R4 insights-archive", e["id"], arel))
    # remove moving entries from source
    drop = set()
    for e in moving:
        drop.update(range(e["start"], e["end"]))
    new = [l for i, l in enumerate(lines) if i not in drop]
    ctx.write(rel, re.sub(r"\n{3,}", "\n\n", "\n".join(new)))
    ctx.write(alias_rel, "\n".join(alines).rstrip("\n") + "\n")


def _md_date(s):
    m = re.search(r"(\d{4}-\d\d-\d\d)", s)
    if m:
        return parse_date(m.group(1))
    m = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{1,2})(?:, (\d{4}))?", s)
    if m:
        try:
            return dt.date(int(m.group(3) or 2026), MONTHS[m.group(1).lower()], int(m.group(2)))
        except ValueError:
            return None
    return None


def rotate_delegations(ctx):
    rel = "memory/delegations.md"
    text = ctx.read(rel)
    if text is None:
        return
    days = ctx.contract["rotation"]["delegations_closed_days"]
    cutoff = ctx.today - dt.timedelta(days=days)
    lines = text.split("\n")
    moved_refs, moved_lines = set(), []
    out_closed, out_log = [], []
    sb = section_block(text, "Closed (last 14 days)", 2)
    drop = set()
    if sb:
        s, e, blk = sb
        for i in range(s + 1, e):
            l = lines[i]
            c = table_cells(l)
            if c is None or is_sep_row(l) or c[0] in ("Ref", "ID"):
                continue
            ds = [d for d in (_md_date(x) for x in c) if d]
            if ds and max(ds) < cutoff:
                m = re.search(r"JD-\d{8}-\d{2}", l)
                if m:
                    moved_refs.add(m.group(0))
                out_closed.append(l)
                drop.add(i)
    sb = section_block(text, "Activity log", 2)
    if sb:
        s, e, blk = sb
        for i in range(s + 1, e):
            l = lines[i]
            if not l.strip().startswith(("-", "|")) or is_sep_row(l):
                continue
            d = _md_date(l)
            if d and d < cutoff:
                out_log.append(l)
                drop.add(i)
    # Texts blocks for moved refs, plus any Texts block whose Ref date is older than the window (R5b)
    out_texts = []
    sbt = section_block(text, "Texts", 2)
    if sbt:
        for i in range(sbt[0] + 1, sbt[1]):
            m = re.match(r"^### (JD-(\d{8})-\d{2})", lines[i])
            if m and dt.datetime.strptime(m.group(2), "%Y%m%d").date() < cutoff:
                moved_refs.add(m.group(1))
    pointer = []
    if moved_refs:
        sb = section_block(text, "Texts", 2)
        if sb:
            s, e, blk = sb
            cur = None
            for i in range(s + 1, e):
                m = re.match(r"^### (JD-\d{8}-\d{2})", lines[i])
                if m:
                    cur = m.group(1) if m.group(1) in moved_refs else None
                if cur:
                    out_texts.append(lines[i])
                    drop.add(i)
            pointer = [f"- Texts for {r} → memory/archive/delegations/{ctx.today:%Y-%m}.md (rotated {ctx.today})" for r in sorted(moved_refs)]
    if not drop:
        return
    mo = ctx.today.strftime("%Y-%m")
    arel = f"memory/archive/delegations/{mo}.md"
    chunk = [f"## Rotated {ctx.today}"]
    if out_closed:
        chunk += ["### Closed", *out_closed]
    if out_log:
        chunk += ["### Activity log", *out_log]
    if out_texts:
        chunk += ["### Texts", *out_texts]
    ctx.append(arel, "\n".join(chunk) + "\n", header=f"# Delegations archive — {mo}")
    kept = [l for i, l in enumerate(lines) if i not in drop]
    if pointer:
        sb2 = section_block("\n".join(kept), "Texts", 2)
        if sb2:
            existing = set(kept)
            kept[sb2[0] + 1:sb2[0] + 1] = [p for p in pointer if p not in existing]
    ctx.write(rel, "\n".join(kept))
    ctx.rotated.append(("R5 delegations", f"{len(drop)} lines", arel))


def rotate_weekend(ctx):
    rel = "memory/weekend-prefs.md"
    text = ctx.read(rel)
    if text is None:
        return
    keep = ctx.contract["rotation"]["weekend_discovered_keep_runs"]
    lines = text.split("\n")
    hs = headings(text)
    disc = []
    for idx, (lvl, i, t) in enumerate(hs):
        m = re.match(r"^Venues & Events Discovered \((\w{3})\w* (\d{1,2}), (\d{4}) run", t)
        if lvl == 3 and m:
            end = next((i2 for l2, i2, _ in hs[idx + 1:] if l2 <= 3), len(lines))
            disc.append((dt.date(int(m.group(3)), MONTHS[m.group(1).lower()[:3]], int(m.group(2))), i, end))
    disc.sort(reverse=True)
    old = disc[keep:]
    drop = set()
    for d, s, e in sorted(old):
        arel = f"memory/archive/weekend/{d:%Y-%m}.md"
        ctx.append(arel, "\n".join(lines[s:e]).rstrip() + "\n", header=f"# Weekend discoveries archive — {d:%Y-%m}")
        drop.update(range(s, e))
        ctx.rotated.append(("R6 weekend", str(d), arel))
    # feedback rows older than N weeks
    sb = section_block(text, "Feedback Log", 2)
    if sb:
        cutoff = ctx.today - dt.timedelta(weeks=ctx.contract["rotation"]["weekend_feedback_keep_weeks"])
        s, e, _ = sb
        fb = []
        for i in range(s + 1, e):
            l = lines[i]
            if table_cells(l) is not None and not is_sep_row(l):
                d = _md_date(l)
                if d and d < cutoff:
                    fb.append(l)
                    drop.add(i)
        if fb:
            ctx.append(f"memory/archive/weekend/{ctx.today:%Y-%m}.md", "## Feedback Log (rotated)\n" + "\n".join(fb) + "\n", header=f"# Weekend discoveries archive — {ctx.today:%Y-%m}")
            ctx.rotated.append(("R6 weekend-feedback", f"{len(fb)} rows", "archive/weekend"))
    if drop:
        ctx.write(rel, "\n".join(l for i, l in enumerate(lines) if i not in drop))


def rotate_trends(ctx):
    rel = "memory/project_health_weekly_trends.md"
    text = ctx.read(rel)
    if text is None:
        return
    sb = section_block(text, "Weekly Log", 2)
    if not sb:
        return
    cutoff = ctx.today - dt.timedelta(weeks=ctx.contract["rotation"]["weekly_trends_keep_weeks"])
    lines = text.split("\n")
    s, e, _ = sb
    drop, moved = set(), []
    for i in range(s + 1, e):
        l = lines[i]
        c = table_cells(l)
        if c is None or is_sep_row(l):
            continue
        d = _md_date(c[0])
        if d and d < cutoff:
            moved.append(l)
            drop.add(i)
    if moved:
        ctx.append(f"memory/archive/health/weekly-trends-{ctx.today.year}.md", "## Weekly Log rows (rotated %s)\n" % ctx.today + "\n".join(moved) + "\n", header=f"# Weekly health trends archive — {ctx.today.year}")
        ctx.write(rel, "\n".join(l for i, l in enumerate(lines) if i not in drop))
        ctx.rotated.append(("R7 trends", f"{len(moved)} rows", "archive/health"))


def rotate_health_events(ctx):
    rel = "memory/health.md"
    text = ctx.read(rel)
    if text is None:
        return
    sb = section_block(text, "Significant Events — Wearable Record", 2)
    if not sb:
        return
    cutoff = ctx.today - dt.timedelta(days=ctx.contract["rotation"]["health_events_keep_days"])
    lines = text.split("\n")
    s, e, _ = sb
    hs = [(lvl, i, t) for lvl, i, t in headings(text) if s < i < e and lvl == 3]
    drop = set()
    for idx, (lvl, i, t) in enumerate(hs):
        if re.search(r"(?i)reference|what works", t):
            continue  # reference blocks are not events
        end = hs[idx + 1][1] if idx + 1 < len(hs) else e
        m = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{1,2})[^,]*, (\d{4})", t)
        if m:
            d = dt.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
            if d < cutoff:
                ctx.append("memory/archive/health/events.md", "\n".join(lines[i:end]).rstrip() + "\n", header="# Health wearable events archive")
                drop.update(range(i, end))
                ctx.rotated.append(("R8 health-events", t[:40], "archive/health/events.md"))
    if drop:
        ctx.write(rel, "\n".join(l for i, l in enumerate(lines) if i not in drop))


def rotate_miss_log(ctx):
    rel = "memory/qmd-miss-log.md"
    text = ctx.read(rel)
    if text is None:
        return
    cutoff = ctx.today - dt.timedelta(days=ctx.contract["rotation"]["miss_log_keep_days"])
    lines = text.split("\n")
    moved = collections.defaultdict(list)
    drop = set()
    for i, l in enumerate(lines):
        if not l.strip() or l.startswith(("#", ">", "*Last updated")):
            continue
        d = _md_date(l[:60])
        if d:
            if d < cutoff:
                moved[d.strftime("%Y-%m")].append(l)
                drop.add(i)
    for mo, ls in moved.items():
        ctx.append(f"memory/archive/qmd-miss-log/{mo}.md", "\n".join(ls) + "\n", header=f"# qmd miss log archive — {mo}")
    if drop:
        ctx.write(rel, "\n".join(l for i, l in enumerate(lines) if i not in drop))
        ctx.rotated.append(("R9 miss-log", f"{len(drop)} lines", "archive/qmd-miss-log"))


# ============================================================================= JOURNAL-DIFF
def do_journal_diff(ctx):
    st = ctx.state()
    text = ctx.read("memory/commitments.md")
    if text is None:
        return
    c = Commitments(text)
    cur = {}
    for r in c.all_rows():
        if not re.match(r"^C-\d{4}$", r.get("ID", "")):
            continue
        cur[r["ID"]] = {"state": r["State"], "due": r["Due"], "section": r["_section"],
                        "note_sha1": hashlib.sha1(r["Note"].encode()).hexdigest()[:10], "what": r["What"][:120], "note": r["Note"][:80]}
    snap = st.get("commitments")
    since = st.get("snapshot_ts", ctx.now.strftime("%Y-%m-%d %H:%M"))
    jl = []
    if snap is not None:
        since_d = since[:10]
        months = sorted({since[:7], ctx.now.strftime("%Y-%m")})
        logged = collections.defaultdict(set)
        for j in journal_lines(ctx, set(months)):
            if f"{j['date']} {j['time']}" >= since:
                ref = j["ref"].split()[0]
                logged[ref].add(j["event"])
        arch = commitments_archive_ids(ctx)
        for cid, r in cur.items():
            old = snap.get(cid)
            tags = infer_tags(ctx, r["what"] + " " + r["note"])
            if old is None:
                if "opened" not in logged[cid]:
                    jl.append(jline(ctx, "maint", f"{cid} (auto)", "opened", f"opened: {r['what']}", tags))
            elif old["state"] != r["state"]:
                if r["section"] == "Closed (last 7 days)" and old["section"] != r["section"]:
                    if "closed" not in logged[cid]:
                        jl.append(jline(ctx, "maint", f"{cid} (auto)", "closed", f"closed: {r['state']} · {r['what'][:120]}", tags))
                elif not (logged[cid] & {"state", "closed", "opened"}):
                    jl.append(jline(ctx, "maint", f"{cid} (auto)", "state", f"{old['state']}→{r['state']}: {r['what'][:120]}", tags))
        for cid, old in snap.items():
            if cid not in cur and cid not in arch:
                ctx.add("V", "C4x", "memory/commitments.md", 0, f"row vanished: {cid}")
                jl.append(jline(ctx, "maint", f"{cid} (auto)", "incident", f"row vanished from commitments.md without archive: {old.get('what', '')[:100]}", ["#exo-infra"]))
    # insights snapshot
    itext = ctx.read("memory/insights.md")
    isnap = {}
    if itext:
        for e in Insights(itext).entries:
            if e["meta"]:
                isnap[e["id"]] = {"status": e["meta"].get("status", ""), "evidence": e["meta"]["evidence_n"], "title": e["title"][:100],
                                  "tag": e["meta"]["subjects"][0]}
        old_i = st.get("insights")
        if old_i is not None:
            logged_i = collections.defaultdict(set)
            for j in journal_lines(ctx, {since[:7], ctx.now.strftime("%Y-%m")}):
                if f"{j['date']} {j['time']}" >= since:
                    logged_i[j["ref"].split()[0]].add(j["event"])
            for iid, v in isnap.items():
                o = old_i.get(iid)
                if o is None and "insight" not in logged_i[iid]:
                    jl.append(jline(ctx, "maint", f"{iid} (auto)", "insight", v["title"], [v["tag"]]))
                elif o and v["evidence"] > o["evidence"] and "evidence" not in logged_i[iid]:
                    jl.append(jline(ctx, "maint", f"{iid} (auto)", "evidence", f"now {v['evidence']}: (instance not logged by the run)", [v["tag"]]))
    if jl:
        journal_append(ctx, [(ctx.today.isoformat(), l) for l in jl])
        ctx.auto_journal += jl
    st["commitments"] = cur
    st["insights"] = isnap or st.get("insights", {})
    st["snapshot_ts"] = ctx.now.strftime("%Y-%m-%d %H:%M")
    ctx.save_state()


# ============================================================================= INDEX
def do_index(ctx):
    rows = []
    worst = {}
    for f in ctx.findings:
        worst.setdefault(f[2], []).append(f)
    for rel, spec, pat in contract_files(ctx):
        p = ctx.root / rel
        if not p.exists():
            rows.append((rel, spec, "missing", "—", "🔴 missing"))
            continue
        text = p.read_text(encoding="utf-8-sig")
        size = len(text.encode())
        hd, hjob, _, _ = header_date(text)
        ref = hd or dt.date.fromtimestamp(p.stat().st_mtime)
        status = "✅"
        mx = spec.get("max_age_days")
        if mx:
            age = (ctx.today - ref).days
            if age > mx:
                status = f"🔴 {age}d"
            elif age >= 0.75 * mx:
                status = f"🟠 {age}d"
        bud = spec.get("budget") or 0
        if bud and size > bud:
            status += " · 🔴 size"
        elif bud and size > 0.8 * bud:
            status += " · 🟠 size"
        extra = ""
        if rel == "memory/insights.md":
            extra = f" · {len(Insights(text).active())}/{spec.get('max_active', 25)} active"
        rows.append((rel, spec, f"{size:,} / {bud:,} ({100 * size // bud if bud else 0}%){extra}", str(ref) + ("" if hd else " (mtime)"), status))
    # collapse circles
    circ = [r for r in rows if r[0].startswith("memory/circles/")]
    rows = [r for r in rows if not r[0].startswith("memory/circles/")]
    out = [f"# Memory INDEX (generated {ctx.now:%Y-%m-%d %H:%M} {ctx.tzl} by memory_maint.py — do not edit)", "",
           "> Read this first. Day counts below are computed — use them, never write your own. Policy: CLAUDE.md > Memory System.", "",
           "## Files", "| File | Class | Bytes / Budget | Last updated | Max age | Owner | Status |", "|---|---|---|---|---|---|---|"]
    for rel, spec, sz, upd, status in rows:
        out.append(f"| {rel.replace('memory/', '')} | {spec.get('class')} | {sz} | {upd} | {str(spec.get('max_age_days') or '—') + ('d' if spec.get('max_age_days') else '')} | {spec.get('owner')} | {status} |")
    if circ:
        stalest = min(circ, key=lambda r: r[3])
        bad = sum(1 for r in circ if r[4].startswith("🔴"))
        out.append(f"| circles/*.md ({len(circ)}) | Q | ≤12,288 each | stalest: {stalest[0].split('/')[-1]} {stalest[3]} | 90d | weekly | {'🔴 ' + str(bad) + ' stale' if bad else '✅'} |")
    for p in journal_files(ctx)[-1:]:
        sz = Path(p).stat().st_size
        out.append(f"| journal/{Path(p).name} | L | {sz:,} / {ctx.contract['logs']['memory/journal/']['soft']:,} soft | — | — | all | {'✅' if sz <= ctx.contract['logs']['memory/journal/']['soft'] else '🟠'} |")
    out.append("| private/ | P | excluded | — | — | — | not indexed |")
    # read plan
    rp = ctx.contract["read_plan"]
    out += ["", "## Read plan per job  (full = whole file · § = `memory_maint.py section <file> \"<heading>\"` · q = grep/lookback first, search index second · — = don't)",
            "| Job | " + " | ".join(rp["columns"]) + " |", "|" + "---|" * (len(rp["columns"]) + 1)]
    for job, cells in rp["jobs"].items():
        out.append(f"| {job} | " + " | ".join(cells) + " |")
    # commitments aging
    ct = ctx.read("memory/commitments.md")
    out += ["", "## Commitments aging (computed)"]
    if ct:
        c = Commitments(ct)
        opens = c.rows("Open — I Said I Would") + c.rows("Open — They Said They Would")
        closed = c.rows("Closed (last 7 days)")
        cnt = collections.Counter(r["State"] for r in opens)
        out.append(f"- Open {len(opens)} · chronic {cnt['CHRONIC']} · calendar-needed {cnt['CALENDAR NEEDED']} · delegated {cnt['DELEGATED']} · waiting {cnt['WAITING']} · closed last 7d {len(closed)}")
        chron = sorted([r for r in opens if r["State"] == "CHRONIC"], key=lambda r: r["Opened"])
        items = [f"{r['ID']} {r['Slug']} {(ctx.today - parse_date(r['Opened'])).days}d" for r in chron if parse_date(r["Opened"])]
        if len(items) > 10:
            items = items[:10] + [f"… +{len(items) - 10} more"]
        out.append("- Chronic (oldest first): " + (" · ".join(items) if items else "none"))
        soon = [f"{r['ID']} {r['Slug']} ({r['Due']})" for r in opens if parse_date(r["Due"]) and 0 <= (parse_date(r["Due"]) - ctx.today).days <= 2]
        over = [f"{r['ID']} {r['Slug']} ({(ctx.today - parse_date(r['Due'])).days}d)" for r in opens if parse_date(r["Due"]) and parse_date(r["Due"]) < ctx.today and r["State"] != "CHRONIC"]
        out.append("- Due ≤48h: " + (" · ".join(soon) if soon else "none"))
        out.append("- Overdue (not chronic): " + (" · ".join(over[:10]) if over else "none"))
    # insights
    it = ctx.read("memory/insights.md")
    out += ["", "## Insights"]
    if it:
        ins = Insights(it)
        act = ins.active()
        subj = collections.Counter(e["meta"]["subjects"][0] for e in act)
        cap = ctx.contract["files"]["memory/insights.md"].get("max_per_subject", 3)
        parts = [f"{s} {n}/{cap}" for s, n in sorted(subj.items(), key=lambda x: (-x[1], x[0]))]
        out.append(f"- Active {len(act)}/{ctx.contract['files']['memory/insights.md'].get('max_active', 25)} · by subject: " + " · ".join(parts))
        atcap = [s for s, n in subj.items() if n >= cap]
        out.append("- Subjects at cap (a new lens there must supersede one): " + (", ".join(sorted(atcap)) if atcap else "none"))
        if act:
            newest = max(act, key=lambda e: e["meta"]["added"])
            out.append(f"- Newest lens: {newest['id']} ({newest['meta']['added']})")
    # last runs
    st = ctx.state()
    out += ["", "## Last runs (from run-notes)"]
    lr = st.get("last_run", {})
    cells = []
    for job in ctx.contract["schedule"]:
        if ctx.contract["schedule"][job].get("run_note") is False:
            continue
        v = lr.get(job)
        if v:
            ok = "✅" if re.match(r"^(sent|ok|skipped|draft)", v.get("result", "")) else "⚠️"
            cells.append(f"{job} {v['ts']} {ok}")
        else:
            cells.append(f"{job} —")
    out.append("- " + " · ".join(cells))
    missed = getattr(ctx, "missed", None)
    if missed is None:
        check_runs(ctx, parse_date(ctx.contract.get("adopted", "2000-01-01")))
        missed = ctx.missed
    out.append("- Missed (expected slot, no run note, last 7d): " + (" · ".join(f"{j} {s:%m-%d %H:%M}" for j, s in missed[-12:]) if missed else "none"))
    # maintenance
    out += ["", "## Maintenance"]
    lrp = st.get("last_report")
    if lrp:
        out.append(f"- Last memory_maint: {lrp}")
    q = qmd_age()
    if q:
        out.append(f"- search index (qmd): {q}")
    jf = journal_files(ctx)
    if jf:
        lines = journal_lines(ctx, {Path(jf[-1]).stem})
        tc = collections.Counter(t for j in lines for t in j["tags"] if t not in ("#migrated", "#review"))
        out.append(f"- Journal {Path(jf[-1]).stem}: {len(lines)} lines · top tags: " + " ".join(f"{t} {n}" for t, n in tc.most_common(3)))
    text = "\n".join(out) + "\n"
    if len(text.encode()) > 6144:
        text = text.replace("| Job | ", "| Job | ", 1)  # keep — truncation handled by limits above
    ctx.write("memory/INDEX.md", text)
    if not ctx.dry:
        st["index_sha256"] = hashlib.sha256((ctx.root / "memory/INDEX.md").read_bytes()).hexdigest()
        ctx.save_state()


def qmd_age():
    exe = shutil.which("qmd")
    if not exe:
        return None  # optional: only reported when a qmd-style search index CLI is installed
    try:
        import subprocess
        out = subprocess.run([exe, "status"], capture_output=True, text=True, timeout=20).stdout
        return re.sub(r"\s+", " ", out)[:160]
    except Exception as e:
        return f"unknown ({e})"


# ============================================================================= REPORT
def finish_report(ctx, sub, quiet=False):
    v = [f for f in ctx.findings if f[0] == "V"]
    w = [f for f in ctx.findings if f[0] == "W"]
    code = EXIT_VIOL if v else (EXIT_WARN if w else EXIT_OK)
    ctx.last_exit = code
    if quiet:
        return code
    md = [f"# memory_maint report — {ctx.now:%Y-%m-%d %H:%M} {ctx.tzl} · {sub} · job {ctx.job} · exit {code} · {len(v)} violations · {len(w)} warnings · dry_run {'yes' if ctx.dry else 'no'}",
          "## Violations", "| code | file:line | message |", "|---|---|---|"]
    md += [f"| {c} | {f}:{l} | {m.replace('|', '/')} |" for _, c, f, l, m in v] or ["| — | — | none |"]
    md += ["## Warnings", "| code | file:line | message |", "|---|---|---|"]
    md += [f"| {c} | {f}:{l} | {m.replace('|', '/')} |" for _, c, f, l, m in w] or ["| — | — | none |"]
    md += ["## Rotation"] + ([f"- {a}: {b} → {c}" for a, b, c in ctx.rotated] or ["- none"])
    md += ["## Journal auto lines"] + (ctx.auto_journal or ["- none"])
    report = "\n".join(md) + "\n"
    js = {"ts": ctx.now.strftime("%Y-%m-%d %H:%M"), "sub": sub, "job": ctx.job, "exit": code, "dry_run": ctx.dry,
          "violations": [dict(code=c, file=f, line=l, msg=m) for _, c, f, l, m in v],
          "warnings": [dict(code=c, file=f, line=l, msg=m) for _, c, f, l, m in w],
          "rotated": [dict(rule=a, item=b, target=c) for a, b, c in ctx.rotated], "auto_journal": ctx.auto_journal,
          "writes": ctx.writes if ctx.dry else len(ctx.writes)}
    dry = ctx.dry
    ctx.dry = False  # report files are always written (spec: dry-run writes only last-report)
    ctx.write("logs/maint/last-report.md", report)
    ctx.write("logs/maint/last-report.json", json.dumps(js, indent=1, ensure_ascii=False) + "\n")
    ctx.dry = dry
    if not dry:
        ctx.state()["last_report"] = f"{js['ts']} · {sub} · job {ctx.job} · exit {code} · {len(v)} violations · {len(w)} warnings · report: logs/maint/last-report.md"
    if getattr(ctx.args, "json", False):
        print(json.dumps(js, ensure_ascii=False, indent=1))
    else:
        print(report, file=sys.stderr if getattr(ctx.args, "json", False) else sys.stdout)
    return code


def log_run(ctx, sub, code, t0):
    if ctx.dry:
        return
    line = {"ts": ctx.now.strftime("%Y-%m-%d %H:%M"), "sub": sub, "job": ctx.job, "exit": code,
            "violations": sum(1 for f in ctx.findings if f[0] == "V"), "warnings": sum(1 for f in ctx.findings if f[0] == "W"),
            "rotated": len(ctx.rotated), "auto_journal": len(ctx.auto_journal), "dry_run": ctx.dry, "ms": int((time.time() - t0) * 1000)}
    ctx.append(f"logs/maint/{ctx.today:%Y-%m}.jsonl", json.dumps(line))


# ============================================================================= SUBCOMMANDS
def cmd_check(ctx):
    return do_check(ctx, enforce=ctx.args.enforce)


def cmd_rotate(ctx):
    with Lock(ctx):
        do_rotate(ctx, ctx.args.only)
        if ctx.auto_journal and not ctx.dry:
            ctx.save_state()
    return finish_report(ctx, "rotate")


def cmd_journal_diff(ctx):
    with Lock(ctx):
        do_journal_diff(ctx)
    return finish_report(ctx, "journal-diff")


def cmd_index(ctx):
    with Lock(ctx):
        do_check(ctx, quiet=True)
        do_index(ctx)
    print(f"INDEX written ({(ctx.root / 'memory/INDEX.md').stat().st_size:,} bytes)" if not ctx.dry else "INDEX (dry-run)")
    return EXIT_OK


def cmd_all(ctx):
    if not ctx.args.job:
        raise Fatal("all requires --job")
    with Lock(ctx):
        do_check(ctx, quiet=True)
        ctx.findings = []
        do_rotate(ctx)
        do_journal_diff(ctx)
        rotated, auto = ctx.rotated, ctx.auto_journal
        ctx.findings = []
        do_check(ctx, enforce=ctx.args.enforce, quiet=True)
        do_index(ctx)
        ctx.findings = [f for f in ctx.findings if f[1] != "C9"]  # INDEX was just regenerated
        ctx.rotated, ctx.auto_journal = rotated, auto
        code = finish_report(ctx, "all")
        if not ctx.dry:
            ctx.save_state()
            write_manifest(ctx)
    return code


def write_manifest(ctx):
    dow = ctx.today.strftime("%a").lower()
    b = ctx.root / "logs" / "maint" / "backup" / dow
    if not b.exists():
        return
    lines = []
    for p in sorted(b.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.txt":
            lines.append(f"{p.relative_to(b).as_posix()}\t{p.stat().st_size}\t{hashlib.sha256(p.read_bytes()).hexdigest()}")
    (b / "MANIFEST.txt").write_text("\n".join(lines) + "\n")


def cmd_section(ctx):
    f = ctx.args.file
    p = (ctx.root / f) if not os.path.isabs(f) else Path(f)
    ctx.guard(p)
    if not p.exists():
        raise Fatal(f"no such file {f}")
    text = p.read_text(encoding="utf-8-sig")
    if ctx.args.list or not ctx.args.heading:
        for lvl, i, t in headings(text):
            print(f"{lvl}\t{i + 1}\t{t}")
        return EXIT_OK
    sb = section_block(text, ctx.args.heading, ctx.args.level)
    if not sb:
        for lvl, i, t in headings(text):
            print(f"{lvl}\t{i + 1}\t{t}", file=sys.stderr)
        print(f"heading not found: {ctx.args.heading}", file=sys.stderr)
        return EXIT_FATAL
    print("\n".join(sb[2]).rstrip())
    return EXIT_OK


def cmd_next_id(ctx):
    kind = ctx.args.kind.upper()
    with Lock(ctx):
        st = ctx.state()
        res = [r for r in st.get("reserved_ids", []) if (ctx.now - dt.datetime.strptime(r["ts"], "%Y-%m-%d %H:%M")).total_seconds() < 6 * 3600]
        nums = [int(r["id"][2:]) for r in res if r["id"].startswith(kind + "-")]
        if kind == "C":
            srcs = [ctx.root / "memory/commitments.md"] + [Path(p) for p in glob.glob(str(ctx.root / "memory/archive/commitments/*.md"))]
        elif kind == "I":
            srcs = [ctx.root / "memory/insights.md"] + [Path(p) for p in glob.glob(str(ctx.root / "memory/archive/insights/*.md"))]
        else:
            raise Fatal("kind must be C or I")
        for p in srcs:
            if p.exists():
                lines = p.read_text(encoding="utf-8-sig").split("\n")
                masked = comment_mask(lines)
                live = "\n".join(l for i, l in enumerate(lines) if i not in masked)
                nums += [int(m) for m in re.findall(r"\b" + kind + r"-(\d{4})\b", live)]
        nid = f"{kind}-{(max(nums) if nums else 0) + 1:04d}"
        if not ctx.args.no_reserve and not ctx.dry:
            res.append({"id": nid, "ts": ctx.now.strftime("%Y-%m-%d %H:%M"), "job": ctx.job})
            st["reserved_ids"] = res
            ctx.save_state()
    print(nid)
    return EXIT_OK


def cmd_run_note(ctx):
    a = ctx.args
    job = a.job
    sched = ctx.contract["schedule"]
    if job not in sched and job not in ("manual", "migration"):
        raise Fatal(f"unknown job {job}")
    code = sched.get(job, {}).get("code", "T")
    rid = f"R-{ctx.now:%Y%m%d-%H%M}-{code}"
    ts = f"{ctx.now:%Y-%m-%d %H:%M}"
    mo = f"{ctx.now:%Y-%m}"
    rel = f"logs/run-notes/{mo}.md"
    if a.oneline:
        entry = f"## {rid} · {ts} {ctx.tzl} · {job} · {a.oneline.strip()[:400]}\n"
        result = a.oneline[:80]
    else:
        if job in ("morning", "evening", "weekly"):
            if not a.insight or not re.match(r"^(new I-\d{4}|evidence I-\d{4}|none — .{1,120})$", a.insight.strip()):
                raise Fatal("--insight must be 'new I-NNNN', 'evidence I-NNNN' or 'none — <reason ≤120>'")
        result = (a.result or "").strip()
        arch = ctx.contract.get("briefing_archive")
        if result.startswith("sent") and arch:
            b = ctx.root / arch / f"{ctx.now:%Y-%m-%d}-{job}.md"
            if not b.exists():
                result = "sent (NO BRIEFING FILE) " + result[4:].strip()
        parts = [f"## {rid} · {ts} {ctx.tzl} · {job}", f"- result: {result}", f"- health: {a.health or '—'}", f"- read: {a.read or '—'}",
                 f"- wrote: {a.wrote or '—'}", f"- insight: {a.insight or '—'}", f"- maint: {a.maint or 'see logs/maint/last-report.md'}"]
        head = "\n".join(parts)
        room = 1500 - len(head) - 10
        note = (a.note or "—").strip()
        if len(note) > room:
            note = note[:max(0, room - 14)] + "…[truncated]"
        entry = head + f"\n- note: {note}\n"
    with Lock(ctx):
        ctx.append(rel, "\n" + entry, header=f"# Run notes — {mo}\n\n> One entry per job run (Memory v2). Not memory: life facts go to memory/journal/.")
        st = ctx.state()
        st.setdefault("last_run", {})[job] = {"ts": ts, "run_id": rid, "result": result[:120]}
        if not ctx.dry:
            ctx.save_state()
    print(rid)
    return EXIT_OK


def cmd_novelty(ctx):
    a = ctx.args
    thr = a.threshold if a.threshold is not None else ctx.contract.get("novelty_threshold", 0.42)
    text = ctx.read("memory/insights.md", "") or ""
    ins = Insights(text)
    cands = [e for e in ins.active()]
    q = quarter_of(ctx.today)
    quarters = None if a.include_archive else {q, prev_quarter(q)}
    subj = a.subject if a.subject.startswith("#") else "#" + a.subject
    for e in archive_insight_entries(ctx, quarters):
        if a.include_archive or (e["meta"] and subj in e["meta"]["subjects"][:1]):
            cands.append(e)
    scored = sorted(((similarity(a.text, e["title"] + ". " + e["body"]), e) for e in cands), key=lambda x: -x[0])
    best = [{"id": e["id"], "sim": round(s, 3), "title": e["title"][:90], "where": e.get("file", "memory/insights.md")} for s, e in scored[:3]]
    sa = sum(1 for e in ins.active() if e["meta"]["subjects"][0] == subj)
    cap = ctx.contract["files"]["memory/insights.md"].get("max_per_subject", 3)
    verdict = "near-duplicate" if best and best[0]["sim"] >= thr else "novel"
    out = {"best": best, "subject": subj, "subject_active": sa, "subject_cap": cap, "threshold": thr, "verdict": verdict}
    if verdict == "novel" and sa >= cap:
        out["note"] = "SUBJECT AT CAP — supersede one of: " + ", ".join(e["id"] for e in ins.active() if e["meta"]["subjects"][0] == subj)
    if a.json:
        print(json.dumps(out, indent=1, ensure_ascii=False))
    else:
        print(f"verdict: {verdict} (threshold {thr})")
        for b in best:
            print(f"  {b['id']}  sim {b['sim']}  {b['title']}  [{b['where']}]")
        print(f"subject {subj}: {sa}/{cap} active")
        if out.get("note"):
            print(out["note"])
    return EXIT_DUP if verdict == "near-duplicate" else EXIT_OK


def cmd_lookback(ctx):
    a = ctx.args
    if a.month:
        frm = dt.date.fromisoformat(a.month + "-01")
        to = (frm.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    elif a.frm:
        frm = parse_date(a.frm)
        to = parse_date(a.to) if a.to else ctx.today
    else:
        frm = ctx.today - dt.timedelta(days=a.days or (3650 if a.id else 30))
        to = ctx.today
    months = set()
    d = frm.replace(day=1)
    while d <= to:
        months.add(d.strftime("%Y-%m"))
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    ids = set()
    if a.id:
        ids.add(a.id)
        al = ctx.read("memory/archive/insights/ALIASES.md", "") or ""
        key = a.id if a.id.startswith("#") else None
        for l in al.split("\n"):
            m = re.match(r"^(\S+)(?: \(\w+\))? → (I-\d{4})", l)
            if m and (m.group(1) == key or m.group(2) == a.id):
                ids.add(m.group(2))
                ids.add(m.group(1))
    tags = set(t if t.startswith("#") else "#" + t for t in (a.tag or []))
    events = set(a.event.split(",")) if a.event else None
    rx = re.compile(a.grep, re.I) if a.grep else None
    res = []
    for j in journal_lines(ctx, months):
        dd = parse_date(j["date"])
        if not (frm <= dd <= to):
            continue
        if tags and not (tags & set(j["tags"])):
            continue
        if events and j["event"] not in events:
            continue
        if a.job and j["job"] != a.job:
            continue
        if ids and j["ref"].split()[0] not in ids:
            continue
        if rx and not rx.search(j["line"]):
            continue
        res.append(j)
    if a.count:
        ec = collections.Counter(j["event"] for j in res)
        tc = collections.Counter(t for j in res for t in j["tags"])
        print(" · ".join(f"{k}: {v}" for k, v in sorted(ec.items())) or "no journal lines matched")
        print(" · ".join(f"{k}: {v}" for k, v in tc.most_common(12)))
        return EXIT_OK
    if a.json:
        print(json.dumps([{k: v for k, v in j.items() if k != "n"} for j in res[:a.limit]], ensure_ascii=False, indent=1))
    else:
        multi = len({j["file"] for j in res}) > 1
        for j in res[:a.limit]:
            print((f"[{Path(j['file']).stem}] " if multi else "") + j["line"])
        if len(res) > a.limit:
            print(f"… {len(res) - a.limit} more")
        if not res:
            print("no journal lines matched")
    pat = rx or (re.compile("|".join(re.escape(i) for i in ids)) if ids else (re.compile("|".join(re.escape(t) for t in tags)) if tags else None))
    if a.archive and pat:
        print("\n# archive")
        n = 0
        for p in sorted(glob.glob(str(ctx.root / "memory/archive/**/*.md"), recursive=True)):
            for i, l in enumerate(Path(p).read_text(encoding="utf-8-sig", errors="replace").split("\n")):
                if pat.search(l):
                    print(f"{ctx.rel(p)}:{i + 1}: {l[:300]}")
                    n += 1
                    if n >= a.limit:
                        print("… (limit)")
                        break
            if n >= a.limit:
                break
    if a.run_notes:
        print("\n# run-notes")
        for e in run_note_entries(ctx):
            if not (frm <= e["ts"].date() <= to):
                continue
            if a.job and e["job"] != a.job:
                continue
            body = "\n".join(e["body"])
            if pat and not pat.search(e["head"] + body):
                continue
            print(e["head"])
            for l in e["body"]:
                if (pat is None or pat.search(l)) and l.strip():
                    print(l[:400])
        for p in sorted(glob.glob(str(ctx.root / "logs/run-notes/archive/*.md"))):
            if pat is None:
                continue
            for i, l in enumerate(Path(p).read_text(encoding="utf-8-sig").split("\n")):
                m = re.match(r"^## R-(\d{8})", l)
                if m:
                    cur_d = dt.datetime.strptime(m.group(1), "%Y%m%d").date()
                elif pat.search(l) and 'cur_d' in locals() and frm <= cur_d <= to:
                    print(f"{ctx.rel(p)}:{i + 1}: {l[:300]}")
    return EXIT_OK


def cmd_verify(ctx):
    a = ctx.args
    src = Path(a.source if os.path.isabs(a.source) else ctx.root / a.source)
    outs = []
    for o in a.outputs.split(","):
        o = o.strip()
        base = o if os.path.isabs(o) else str(ctx.root / o)
        g = sorted(glob.glob(base))
        outs += [Path(x) for x in g] if g else [Path(base)]
    ctx.guard(src)
    st = src.read_text(encoding="utf-8-sig")
    ign = re.compile(a.ignore_regex) if a.ignore_regex else None
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    pool = set()
    ob = ol = 0
    for o in outs:
        if Path(o).exists():
            t = Path(o).read_text(encoding="utf-8-sig")
            ob += len(t.encode())
            ol += t.count("\n")
            pool.update(norm(x) for x in t.split("\n"))
    print(f"source: {st.count(chr(10))} lines / {len(st.encode()):,} bytes · outputs: {ol} lines / {ob:,} bytes")
    missing = []
    if a.content:
        for i, l in enumerate(st.split("\n")):
            if not l.strip() or (ign and ign.search(l)):
                continue
            if norm(l) not in pool:
                missing.append((i + 1, l))
        print(f"missing lines: {len(missing)}")
        for n, l in missing[:20]:
            print(f"  {n}: {l[:160]}")
    return EXIT_VIOL if missing else EXIT_OK


def cmd_journal(ctx):
    a = ctx.args
    if a.event not in EVENTS:
        raise Fatal(f"event must be one of {EVENTS}")
    tags = [t if t.startswith("#") else "#" + t for t in (a.tags or "").replace(",", " ").split()]
    bad = [t for t in tags if t not in ctx.contract["tags"]]
    if not tags:
        raise Fatal("at least one --tags value from tools/memory_contract.json > tags")
    if bad:
        raise Fatal(f"unknown tags {bad}; allowed: {' '.join(ctx.contract['tags'])}")
    text = re.sub(r"\s+", " ", a.text.replace("·", "-")).strip()
    if len(text) > 200:
        raise Fatal(f"text is {len(text)} chars; max 200")
    ref = (a.ref or "—").strip()
    line = f"- {ctx.now:%Y-%m-%d %H:%M} · {ctx.job} · {ref} · {a.event} · {text} · {' '.join(tags)}"
    if a.block:
        if a.event != "review":
            raise Fatal("--block only with --event review")
        blk = [l.strip() for l in re.split(r"\\n|\n", a.block) if l.strip()]
        body = "\n".join("  - " + l.lstrip("- ") for l in blk)
        if len(body) > ctx.contract["logs"]["memory/journal/"]["review_block_chars"]:
            raise Fatal("review block > 1,500 chars")
        line = line + "\n" + body
    if not JOURNAL_RE.match(line.split("\n")[0]):
        raise Fatal("line failed the journal format check")
    with Lock(ctx):
        journal_append(ctx, [(ctx.today.isoformat(), line)])
    print(line)
    return EXIT_OK


# ============================================================================= CLI
def main(argv=None):
    ap = argparse.ArgumentParser(prog="memory_maint.py", description="POHA memory maintenance")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root")
    common.add_argument("--now")
    common.add_argument("--json", action="store_true")
    common.add_argument("--quiet", action="store_true")
    common.add_argument("--dry-run", action="store_true")
    common.add_argument("--job")
    sub = ap.add_subparsers(dest="sub", required=True)
    p = sub.add_parser("check", parents=[common]); p.add_argument("--enforce", action="store_true")
    p = sub.add_parser("rotate", parents=[common]); p.add_argument("--only")
    sub.add_parser("journal-diff", parents=[common])
    sub.add_parser("index", parents=[common])
    p = sub.add_parser("all", parents=[common]); p.add_argument("--enforce", action="store_true")
    p = sub.add_parser("section", parents=[common]); p.add_argument("file"); p.add_argument("heading", nargs="?"); p.add_argument("--level", type=int); p.add_argument("--list", action="store_true")
    p = sub.add_parser("lookback", parents=[common])
    p.add_argument("--tag", nargs="*"); p.add_argument("--id"); p.add_argument("--event"); p.add_argument("--grep")
    p.add_argument("--days", type=int); p.add_argument("--from", dest="frm"); p.add_argument("--to"); p.add_argument("--month")
    p.add_argument("--archive", action="store_true"); p.add_argument("--run-notes", action="store_true"); p.add_argument("--count", action="store_true"); p.add_argument("--limit", type=int, default=400)
    p = sub.add_parser("next-id", parents=[common]); p.add_argument("kind"); p.add_argument("--no-reserve", action="store_true")
    p = sub.add_parser("run-note", parents=[common])
    for k in ("result", "health", "read", "wrote", "insight", "note", "maint", "oneline"):
        p.add_argument("--" + k)
    p = sub.add_parser("novelty", parents=[common]); p.add_argument("--subject", required=True); p.add_argument("--text", required=True); p.add_argument("--threshold", type=float); p.add_argument("--include-archive", action="store_true")
    p = sub.add_parser("journal", parents=[common]); p.add_argument("--event", required=True); p.add_argument("--text", required=True); p.add_argument("--ref"); p.add_argument("--tags"); p.add_argument("--block")
    p = sub.add_parser("verify", parents=[common]); p.add_argument("--source", required=True); p.add_argument("--outputs", required=True); p.add_argument("--content", action="store_true"); p.add_argument("--ignore-regex")
    args = ap.parse_args(argv)
    t0 = time.time()
    try:
        ctx = Ctx(args)
        fn = {"check": cmd_check, "rotate": cmd_rotate, "journal-diff": cmd_journal_diff, "index": cmd_index, "all": cmd_all,
              "section": cmd_section, "lookback": cmd_lookback, "next-id": cmd_next_id, "run-note": cmd_run_note,
              "novelty": cmd_novelty, "verify": cmd_verify, "journal": cmd_journal}[args.sub]
        code = fn(ctx)
        if args.sub in ("rotate", "journal-diff", "index", "all", "run-note", "journal"):
            log_run(ctx, args.sub, code, t0)
        return code
    except Fatal as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return EXIT_FATAL
    except Exception as e:  # never crash silently
        import traceback
        traceback.print_exc()
        print(f"FATAL: {type(e).__name__}: {e}", file=sys.stderr)
        return EXIT_FATAL


if __name__ == "__main__":
    sys.exit(main())
