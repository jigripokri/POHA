"""Unit tests for tools/memory_maint.py — run: python3 -m unittest discover tools/tests"""
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import memory_maint as mm  # noqa: E402

HDR = "| ID | Slug | What | Who | Due | State | Opened | Touched | Note |\n|----|----|----|----|----|----|----|----|----|"


def commit_file(open_rows="", closed_rows=""):
    return f"""# Commitments — Memory

*Last updated: 2026-10-23 (evening)*

## Pinned projects
### 🟢 Tracked project (P-TP)
- **State:** testing.

## Open — I Said I Would
{HDR}
{open_rows}

## Open — They Said They Would
{HDR}

## Closed (last 7 days)
{HDR}
{closed_rows}
"""


def lens(i, added, subj, title="A lens", body="Some body text.\nLens: look at it this way.", extra=""):
    return f"### I-{i:04d} · {title}\n*Added {added} (evening) · subject: {subj} · evidence: 1{extra} · aliases: —*\n{body}\n"


def insights_file(entries):
    return "# Insights — Memory\n\n*Last updated: 2026-10-23 (weekly)*\n\n## Active\n\n" + "\n".join(entries)


class Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "tools").mkdir()
        shutil.copy(HERE.parent / "memory_contract.json", self.d / "tools/memory_contract.json")
        (self.d / "memory/private").mkdir(parents=True)
        (self.d / "memory/private/carry-on.md").write_text("secret")
        (self.d / "memory/journal").mkdir()
        (self.d / "memory/commitments.md").write_text(commit_file())
        (self.d / "memory/insights.md").write_text(insights_file([lens(1, "2026-10-20", "#freeze")]))

    def tearDown(self):
        shutil.rmtree(self.d)

    def run_mm(self, *args, now="2026-10-23 17:00"):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = mm.main(list(args) + ["--root", str(self.d), "--now", now])
        return code, out.getvalue() + err.getvalue()

    def report(self):
        return json.loads((self.d / "logs/maint/last-report.json").read_text())

    def codes(self):
        r = self.report()
        return [v["code"] for v in r["violations"]], [w["code"] for w in r["warnings"]]


class TestChecks(Base):
    def test_dup_id(self):
        row = "| C-0001 | a | Do a | Self | — | PENDING | 2026-10-20 | 2026-10-20 | |"
        (self.d / "memory/commitments.md").write_text(commit_file(row + "\n" + row.replace("| a |", "| b |")))
        self.run_mm("check")
        self.assertIn("C4", self.codes()[0])

    def test_clean_commitments(self):
        row = "| C-0001 | a | Do a | Self | — | PENDING | 2026-10-20 | 2026-10-20 | fine |"
        (self.d / "memory/commitments.md").write_text(commit_file(row))
        self.run_mm("check")
        self.assertNotIn("C4", self.codes()[0])

    def test_subject_cap_and_order(self):
        es = [lens(i, f"2026-10-{20 - i:02d}", "#freeze") for i in range(1, 5)]
        (self.d / "memory/insights.md").write_text(insights_file(es))
        self.run_mm("check")
        msgs = [v["msg"] for v in self.report()["violations"] if v["code"] == "C5"]
        self.assertTrue(any("subject #freeze has 4" in m for m in msgs))
        es = [lens(1, "2026-10-01", "#freeze"), lens(2, "2026-10-05", "#partner")]
        (self.d / "memory/insights.md").write_text(insights_file(es))
        self.run_mm("check")
        self.assertTrue(any("not newest-first" in v["msg"] for v in self.report()["violations"]))

    def test_forbidden_patterns(self):
        row = "| C-0001 | a | Do a | Self | — | PENDING | 2026-10-20 | 2026-10-20 | still unsent, Day 46 |"
        (self.d / "memory/commitments.md").write_text(commit_file(row))
        self.run_mm("check")
        self.assertIn("C7", self.codes()[0])
        row = "| C-0001 | a | Call on Monday | Self | — | PENDING | 2026-10-20 | 2026-10-20 | Monday works |"
        (self.d / "memory/commitments.md").write_text(commit_file(row))
        self.run_mm("check")
        self.assertNotIn("C7", self.codes()[0])
        (self.d / "memory/commitments.md").write_text(commit_file() + "\n**Evening note (Oct 21, Wed — automated):** blah\n")
        self.run_mm("check")
        self.assertIn("C7", self.codes()[0])


class TestRotate(Base):
    def test_chronic_flip_at_21_days(self):
        rows = ("| C-0001 | a | Old | Self | — | PENDING | 2026-10-02 | 2026-10-02 | |\n"
                "| C-0002 | b | Young | Self | — | PENDING | 2026-10-03 | 2026-10-03 | |")
        (self.d / "memory/commitments.md").write_text(commit_file(rows))
        self.run_mm("rotate", now="2026-10-23 17:00")
        t = (self.d / "memory/commitments.md").read_text()
        self.assertIn("| C-0001 | a | Old | Self | — | CHRONIC |", t)
        self.assertIn("| C-0002 | b | Young | Self | — | PENDING |", t)
        j = (self.d / "memory/journal/2026-10.md").read_text()
        self.assertIn("C-0001 (auto) · state · PENDING→CHRONIC", j)

    def test_closed_archive_bucket(self):
        closed = ("| C-0003 | c | Done thing | Self | — | DONE | 2026-09-01 | 2026-09-30 | |\n"
                  "| C-0004 | d | Recent | Self | — | DONE | 2026-10-20 | 2026-10-21 | |")
        (self.d / "memory/commitments.md").write_text(commit_file(closed_rows=closed))
        self.run_mm("rotate")
        self.assertIn("C-0003", (self.d / "memory/archive/commitments/2026-09.md").read_text())
        t = (self.d / "memory/commitments.md").read_text()
        self.assertNotIn("C-0003", t)
        self.assertIn("C-0004", t)
        self.run_mm("rotate")  # idempotent
        self.assertEqual((self.d / "memory/archive/commitments/2026-09.md").read_text().count("C-0003"), 1)

    def test_insight_archive_and_evidence_merge(self):
        es = [lens(2, "2026-10-20", "#freeze", title="Survivor"),
              lens(1, "2026-08-01", "#freeze", title="Old one", extra=" · superseded-by: I-0002 · status: superseded")]
        (self.d / "memory/insights.md").write_text(insights_file(es))
        self.run_mm("rotate")
        t = (self.d / "memory/insights.md").read_text()
        self.assertNotIn("Old one", t)
        self.assertIn("evidence: 2", t)
        self.assertIn("Old one", (self.d / "memory/archive/insights/2026-Q3.md").read_text())


class TestJournalDiff(Base):
    def test_auto_close_and_vanish(self):
        rows = ("| C-0001 | a | First | Self | — | PENDING | 2026-10-20 | 2026-10-20 | |\n"
                "| C-0002 | b | Second | Self | — | PENDING | 2026-10-20 | 2026-10-20 | |")
        (self.d / "memory/commitments.md").write_text(commit_file(rows))
        self.run_mm("journal-diff", now="2026-10-23 10:00")
        closed = "| C-0001 | a | First | Self | — | DONE | 2026-10-20 | 2026-10-23 | |"
        (self.d / "memory/commitments.md").write_text(commit_file("", closed))
        code, _ = self.run_mm("journal-diff", now="2026-10-23 11:00")
        j = (self.d / "memory/journal/2026-10.md").read_text()
        self.assertIn("C-0001 (auto) · closed", j)
        self.assertIn("C-0002 (auto) · incident", j)
        self.assertEqual(code, 2)


class TestTools(Base):
    def test_section_emoji_heading(self):
        code, out = self.run_mm("section", "memory/commitments.md", "Tracked project (P-TP)")
        self.assertEqual(code, 0)
        self.assertIn("testing", out)

    def test_novelty(self):
        body = ("The lawyer email and the parent call both stay frozen through every reminder lever; "
                "everything with a named person waiting closed the same day.\nLens: attach a waiting human.")
        (self.d / "memory/insights.md").write_text(insights_file([lens(1, "2026-10-02", "#freeze", title="The chronic freezes share a missing ingredient", body=body)]))
        code, _ = self.run_mm("novelty", "--subject", "#freeze", "--text",
                              "The lawyer email and the call to the parents stayed frozen again despite reminders; items with a person waiting closed same day")
        self.assertEqual(code, 3)
        code, _ = self.run_mm("novelty", "--subject", "#money", "--text", "Spending on groceries dropped while restaurant spend rose in October")
        self.assertEqual(code, 0)

    def test_next_id_scans_archive(self):
        (self.d / "memory/archive/commitments").mkdir(parents=True)
        (self.d / "memory/archive/commitments/2026-09.md").write_text("| C-0042 | x | y | z | — | DONE | 2026-09-01 | 2026-09-02 | |\n")
        code, out = self.run_mm("next-id", "C")
        self.assertIn("C-0043", out)
        code, out = self.run_mm("next-id", "C")
        self.assertIn("C-0044", out)  # reservation

    def test_dry_run_writes_nothing(self):
        rows = "| C-0001 | a | Old | Self | — | PENDING | 2026-09-01 | 2026-09-01 | |"
        (self.d / "memory/commitments.md").write_text(commit_file(rows))

        def snap():
            return {p.relative_to(self.d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.d.rglob("*") if p.is_file() and "logs/maint/last-report" not in p.as_posix()}
        before = snap()
        self.run_mm("all", "--job", "evening", "--dry-run")
        self.assertEqual(before, snap())

    def test_never_touch(self):
        code, out = self.run_mm("section", "memory/private/carry-on.md", "x")
        self.assertEqual(code, 4)
        self.assertNotIn("secret", out)

    def test_crlf_preserved(self):
        rows = "| C-0001 | a | Old | Self | — | PENDING | 2026-09-01 | 2026-09-01 | |"
        (self.d / "memory/commitments.md").write_bytes(commit_file(rows).replace("\n", "\r\n").encode())
        self.run_mm("rotate")
        b = (self.d / "memory/commitments.md").read_bytes()
        self.assertIn(b"CHRONIC", b)
        self.assertNotIn(b"\n", b.replace(b"\r\n", b""))

    def test_run_note_requires_insight(self):
        code, _ = self.run_mm("run-note", "--job", "evening", "--result", "sent (x)")
        self.assertEqual(code, 4)
        code, out = self.run_mm("run-note", "--job", "evening", "--result", "draft (x)", "--insight", "none — quiet day")
        self.assertEqual(code, 0)
        self.assertIn("- insight: none — quiet day", (self.d / "logs/run-notes/2026-10.md").read_text())


class TestFreshFork(unittest.TestCase):
    """The shipped templates, copied as-is, must pass a first `all` with exit 0."""

    def test_templates_clean_first_run(self):
        repo = HERE.parent.parent
        d = Path(tempfile.mkdtemp())
        try:
            (d / "tools").mkdir()
            shutil.copy(HERE.parent / "memory_contract.json", d / "tools/memory_contract.json")
            (d / "memory").mkdir()
            for tpl in (repo / "memory").glob("*.md.template"):
                if tpl.name == "journal.md.template":
                    continue
                txt = tpl.read_text(encoding="utf-8").replace("{{YYYY-MM-DD}}", "2026-10-25")
                (d / "memory" / tpl.name[:-len(".template")]).write_text(txt, encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(out):
                code = mm.main(["all", "--job", "manual", "--root", str(d), "--now", "2026-10-25 10:00", "--quiet"])
            self.assertEqual(code, 0, (d / "logs/maint/last-report.md").read_text())
            # examples inside <!-- --> are format docs, not data
            out = io.StringIO()
            with redirect_stdout(out):
                mm.main(["next-id", "C", "--root", str(d), "--now", "2026-10-25 10:00"])
                mm.main(["next-id", "I", "--root", str(d), "--now", "2026-10-25 10:00"])
            self.assertIn("C-0001", out.getvalue())
            self.assertIn("I-0001", out.getvalue())
            # the first run note anchors missed-run checks: nothing before it is "missed"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                mm.main(["run-note", "--job", "evening", "--result", "sent (x)", "--insight", "none — first run",
                         "--root", str(d), "--now", "2026-10-25 21:00"])
                mm.main(["check", "--root", str(d), "--now", "2026-10-25 23:00", "--quiet"])
            rep = json.loads((d / "logs/maint/last-report.json").read_text())
            self.assertFalse([f for f in rep["violations"] + rep["warnings"] if f["code"] == "C8"])
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
