"""End-to-end graph tests. Only the thin LLM boundaries are stubbed; routing, Qdrant, validation,
scoring, triage and formatting all run for real."""
import pytest

from agent.graph import build_graph
from agent.nodes.formatter import render_markdown
from agent.state import (CandidateExtraction, ExtractedEducation, JobChunk, JobRequirement, Recommendation,
                         WorkExperience)
from main import run_one
from rag import store

CV_EN = """Ahmed Hassan
ahmed@example.com | +971501234567
Summary: Backend engineer building APIs.
Experience
Senior Backend Engineer, Acme Corp, 2018 - 2024. Built REST APIs with Python and FastAPI, deployed on AWS using Docker.
Backend Developer, Beta LLC, 2015 - 2018. Worked with PostgreSQL and Redis.
Education
BSc Computer Science, Cairo University, 2014
Skills: Python, FastAPI, Docker, PostgreSQL, AWS, Redis
""" * 1

CV_AR = """أحمد حسن
ahmed@example.com
مهندس برمجيات خلفية لديه خبرة في بناء واجهات برمجية باستخدام Python و Docker
الخبرة: مهندس برمجيات أول، شركة أكمي، 2018 - 2024
التعليم: بكالوريوس علوم الحاسب، جامعة القاهرة، 2014
المهارات: Python, Docker, PostgreSQL
""" * 3


def _ext(name="Ahmed Hassan", skills=("Python", "FastAPI", "Docker", "PostgreSQL", "AWS", "Redis")):
    return CandidateExtraction(
        name=name, email="ahmed@example.com", skills=list(skills),
        experience=[WorkExperience(title="Senior Backend Engineer", company="Acme Corp", start_year=2018, end_year=2024,
                                   description="Built REST APIs with Python and FastAPI"),
                    WorkExperience(title="Backend Developer", company="Beta LLC", start_year=2015, end_year=2018)],
        education=[ExtractedEducation(degree="BSc", field_of_study="Computer Science", institution="Cairo University",
                                      graduation_year=2014)])


@pytest.fixture
def job():
    req = JobRequirement(job_id="backend", job_version="v1", language="en", title="Backend Engineer",
                         required_skills=["Python", "Docker", "Kubernetes", "GraphQL", "Terraform"],
                         nice_to_have_skills=["AWS"], min_experience_years=5,
                         education_requirement="BSc in Computer Science",
                         responsibilities_summary="Build and operate backend services.")
    store.upsert_job(req, [JobChunk(section="Requirements", text="Python, Docker, Kubernetes, GraphQL")])
    return req


@pytest.fixture
def stubs(monkeypatch):
    calls = {"justify": 0, "judge": []}
    monkeypatch.setattr("config.settings.GAP_MODE", "hybrid")

    def judge(skill, evidence):
        calls["judge"].append(skill)
        if skill == "Kubernetes":   # adjacent to Docker, quote is REAL -> stays partial
            return "partial", evidence.splitlines()[0].lstrip("- ")
        if skill == "GraphQL":      # claims 'met' with a fabricated quote -> downgraded to partial
            return "met", "this quote is not in the evidence"
        return "partial", "also fabricated"  # Terraform: partial + fabricated quote -> missing

    monkeypatch.setattr("agent.nodes.gap_agent._call_judge", judge)
    monkeypatch.setattr("agent.nodes.matcher._call_assess", lambda *a: ("strong", "meets", "some"))

    def justify(**kw):
        calls["justify"] += 1
        if kw["target_language"] == "ar":  # first attempt in the WRONG language to test the retry
            return "The candidate is a strong fit." if calls["justify"] == 1 else "المرشح مناسب للوظيفة مع فجوة في Kubernetes."
        return "Strong backend profile with gaps in Kubernetes and GraphQL."

    monkeypatch.setattr("agent.nodes.matcher._call_justify", justify)
    monkeypatch.setattr("agent.nodes.recommender._from_catalog", lambda s, t: None)
    monkeypatch.setattr("agent.nodes.recommender._from_web", lambda s, jt, t: Recommendation(
        missing_skill=s, title=f"Learn {s}", provider="Coursera", url=f"https://x.io/{s}", source="web_search",
        reason="سبب" if t == "ar" else "Closes the gap."))
    return calls


def test_english_cv_full_flow(tmp_path, job, stubs, monkeypatch):
    monkeypatch.setattr("config.settings.SKILL_SIM_AMBIG", 0.0)  # send every non-exact skill to the judge
    monkeypatch.setattr("agent.nodes.extractor._call_extract", lambda vision, pages, text: _ext())
    cv = tmp_path / "ahmed.txt"
    cv.write_text(CV_EN * 1, encoding="utf-8")
    r = run_one(build_graph(), str(cv), "backend")

    assert r.status == "ok", r.errors
    assert r.target_language == "en" and r.parse_method == "text"
    assert r.profile.experience_years == 9.0  # 2015-2024, computed in code
    v = {x.skill: x for x in r.skill_gap.verdicts}
    assert v["Python"].method == "exact" and v["Python"].verdict == "met"
    assert v["Kubernetes"].verdict == "partial" and v["Kubernetes"].method == "llm"
    assert v["GraphQL"].verdict == "partial"   # met + unverifiable quote -> downgraded one level
    assert v["Terraform"].verdict == "missing"  # partial + unverifiable quote -> downgraded one level
    assert v["AWS"].method == "exact"
    assert r.match.match_score > 0 and 0 <= r.match.match_confidence <= 1
    assert {x.missing_skill for x in r.recommendations} == {"Terraform", "Kubernetes", "GraphQL"}
    assert "Candidate Evaluation Report" in render_markdown(r)


def test_arabic_output_language_retry(tmp_path, job, stubs, monkeypatch):
    monkeypatch.setattr("agent.nodes.extractor._call_extract",
                        lambda vision, pages, text: _ext(name="أحمد حسن", skills=("Python", "Docker", "PostgreSQL")))
    cv = tmp_path / "ahmed_ar.txt"
    cv.write_text(CV_AR, encoding="utf-8")
    r = run_one(build_graph(), str(cv), "backend")

    assert r.status == "ok", r.errors
    assert r.detected_language in ("ar", "mixed") and r.target_language == "ar"
    assert stubs["justify"] == 0  # justification is deterministic and does not use an LLM
    assert "درجة المطابقة" in r.match.justification
    assert "تقرير تقييم المرشح" in render_markdown(r)


def test_missing_job_fails_fast_without_touching_the_gpu(tmp_path, monkeypatch):
    def boom(*a):
        raise AssertionError("extraction must not run when the job does not exist")

    monkeypatch.setattr("agent.nodes.extractor._call_extract", boom)
    cv = tmp_path / "x.txt"
    cv.write_text(CV_EN, encoding="utf-8")
    r = run_one(build_graph(), str(cv), "does-not-exist")
    assert r.status == "failed" and r.errors[0].error_type == "job_not_found"


def test_ungrounded_skills_force_human_review(tmp_path, job, stubs, monkeypatch):
    # model invents skills that are not in the document; no page images -> cannot escalate -> flag
    monkeypatch.setattr("agent.nodes.extractor._call_extract",
                        lambda v, p, t: _ext(skills=("Python", "Docker", "Rust", "Haskell", "Scala")))
    cv = tmp_path / "c.txt"
    cv.write_text(CV_EN, encoding="utf-8")
    r = run_one(build_graph(), str(cv), "backend")
    assert r.status == "ok"
    assert {"Rust", "Haskell", "Scala"} <= set(r.profile.ungrounded_skills)
    assert r.match.triage_bucket == "review" and "unresolved_validation" in r.match.review_reasons


def test_validator_escalates_text_path_to_vision(monkeypatch):
    from agent.nodes.validator import validator
    from agent.state import HRState
    from agent.nodes.extractor import build_profile

    text = CV_EN
    st = HRState(cv_path="a.pdf", job_id="j", candidate_id="c", text_layer=text, text_ok=True,
                 page_paths=["p1.png"], extract_attempts=1)
    st = st.model_copy(update={"profile": build_profile(_ext(skills=("Rust", "Haskell")), st, False)})
    out = validator(st)
    assert out["retry_extract"] is True and out["use_vision"] is True


# ── ReAct gap agent ─────────────────────────────────────────────────────────
def test_low_similarity_to_skills_list_no_longer_means_missing():
    from analysis.skills import prematch
    jobs = [("Kubernetes", "required")]
    decided, pending = prematch(jobs, ["Python", "Docker"], escalate_low=False)
    assert decided[0].verdict == "missing" and not pending        # old behaviour: never investigated
    decided, pending = prematch(jobs, ["Python", "Docker"], escalate_low=True)
    assert not decided and pending[0][0] == "Kubernetes"          # now handed to the agent


def test_react_gap_finds_skill_hidden_in_experience_and_runs_verification_loop(tmp_path, monkeypatch):
    from agent.nodes.gap_agent import make_gap_tools
    monkeypatch.setattr("config.settings.GAP_MODE", "react")
    req = JobRequirement(job_id="devops", job_version="v1", title="DevOps Engineer",
                         required_skills=["Python", "Kubernetes", "GraphQL"], min_experience_years=3,
                         responsibilities_summary="Run clusters.")
    store.upsert_job(req, [JobChunk(section="Requirements", text="Kubernetes in production")])

    ext = _ext(skills=("Python", "Docker"))
    ext.experience[0].description = "Operated production Kubernetes clusters for 12 services"
    monkeypatch.setattr("agent.nodes.extractor._call_extract", lambda v, p, t: ext)
    monkeypatch.setattr("agent.nodes.matcher._call_assess", lambda *a: ("strong", "meets", "some"))
    monkeypatch.setattr("agent.nodes.matcher._call_justify", lambda **kw: "Solid DevOps profile.")

    calls = []

    def fake_agent(skill, lines, vecs, chunks, seen, feedback):
        calls.append((skill, bool(feedback)))
        search_cv, job_context = make_gap_tools(lines, vecs, chunks, seen)  # real tools, real CV search
        if skill == "GraphQL":
            search_cv("GraphQL")
            return "missing", ""
        search_cv("Kubernetes")
        if not feedback:                       # 1st attempt: fabricated quote -> must be rejected
            return "met", "5 years of Kubernetes at Google"
        return "met", next(x for x in seen if "Kubernetes" in x)  # after feedback: a real, retrieved line

    monkeypatch.setattr("agent.nodes.gap_agent._call_react_judge", fake_agent)
    cv = tmp_path / "c.txt"
    cv.write_text(CV_EN, encoding="utf-8")
    r = run_one(build_graph(), str(cv), "devops")

    v = {x.skill: x for x in r.skill_gap.verdicts}
    assert v["Python"].method == "exact"
    assert v["Kubernetes"].verdict == "met" and v["Kubernetes"].method == "agent"   # found inside experience text
    assert "Kubernetes" in v["Kubernetes"].evidence
    assert calls.count(("Kubernetes", False)) == 1 and calls.count(("Kubernetes", True)) == 1  # loop ran once
    assert v["GraphQL"].verdict == "missing"


def test_unverifiable_quote_after_feedback_is_downgraded(monkeypatch):
    from agent.nodes.gap_agent import _judge_react
    monkeypatch.setattr("agent.nodes.gap_agent._call_react_judge", lambda *a: ("met", "invented quote"))
    v = _judge_react("Kubernetes", "required", "Docker", 0.3, ["Docker experience"], None, [])
    assert v.verdict == "partial" and v.evidence == ""   # met -> partial when never verifiable


def test_docx_without_libreoffice_uses_text_and_tables(tmp_path, monkeypatch):
    from docx import Document
    from agent.nodes.ingest import ingest
    from agent.state import HRState

    monkeypatch.setattr("shutil.which", lambda *_: None)          # no soffice on this machine
    d = Document()
    for _ in range(6):
        d.add_paragraph("مهندس برمجيات أول لديه خبرة واسعة في بناء الأنظمة الخلفية وتطوير الواجهات البرمجية")
    d.add_table(rows=1, cols=2).rows[0].cells[0].text = "Skills"
    d.tables[0].rows[0].cells[1].text = "Python, Docker"
    f = tmp_path / "cv.docx"
    d.save(f)

    out = ingest(HRState(cv_path=str(f), job_id="j"))
    assert out["page_paths"] == [] and "Python, Docker" in out["text_layer"] and "مهندس" in out["text_layer"]
    assert out["text_ok"] is True


def test_docx_converted_to_pdf_when_libreoffice_exists(tmp_path, monkeypatch):
    """Simulates soffice: verifies the command isolates its profile and pages are rendered from the PDF."""
    import pypdfium2 as pdfium
    from PIL import Image
    from docx import Document
    from agent.nodes import ingest as I
    from agent.state import HRState

    d = Document()
    d.add_paragraph("x " * 200)
    f = tmp_path / "cv.docx"
    d.save(f)
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        outdir = cmd[cmd.index("--outdir") + 1]
        Image.new("RGB", (200, 280), "white").save(f"{outdir}/cv.pdf")  # a real 1-page PDF
    monkeypatch.setattr(I.shutil, "which", lambda *_: "/usr/bin/soffice")
    monkeypatch.setattr(I.subprocess, "run", fake_run)

    out = I.ingest(HRState(cv_path=str(f), job_id="j"))
    assert any(a.startswith("-env:UserInstallation=") for a in seen["cmd"])  # parallel-safe
    assert len(out["page_paths"]) == 1


def test_docling_converter_modes_and_caching(monkeypatch):
    """Docling is not installed in CI; inject a fake to verify which options each mode builds."""
    import sys, types
    from agent.nodes import ingest as I

    built = []

    class Opts:
        def __init__(self, **kw): self.kw = kw

    class PdfFormatOption:
        def __init__(self, pipeline_options): self.opts = pipeline_options

    class DocumentConverter:
        def __init__(self, format_options=None): built.append(format_options)

    mods = {
        "docling": types.ModuleType("docling"),
        "docling.datamodel": types.ModuleType("docling.datamodel"),
        "docling.datamodel.base_models": types.SimpleNamespace(InputFormat=types.SimpleNamespace(PDF="pdf")),
        "docling.datamodel.pipeline_options": types.SimpleNamespace(PdfPipelineOptions=Opts),
        "docling.document_converter": types.SimpleNamespace(DocumentConverter=DocumentConverter,
                                                            PdfFormatOption=PdfFormatOption),
    }
    for k, v in mods.items():
        monkeypatch.setitem(sys.modules, k, v)

    for mode, ocr, tables in [("simple", False, False), ("tables", False, True)]:
        monkeypatch.setattr("config.settings.DOCLING_MODE", mode)
        I._converter.cache_clear()
        I._converter()
        assert built[-1]["pdf"].opts.kw == {"do_ocr": ocr, "do_table_structure": tables}
    n = len(built)
    I._converter()
    assert len(built) == n  # cached: models are not reloaded per CV

    monkeypatch.setattr("config.settings.DOCLING_MODE", "full")
    I._converter.cache_clear()
    I._converter()
    assert built[-1] is None  # library defaults
