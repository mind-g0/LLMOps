from agent.state import CandidateProfile, Flag, SkillVerdict, WorkExperience
from analysis import rules, scoring
from utils import text as T


def test_normalize_arabic_variants_and_digits():
    assert T.normalize_text("إدارة  المشاريع") == T.normalize_text("ادارة المشاريع")
    assert T.normalize_text("Python ٣") == "python 3"
    assert T.normalize_text("C++") == "c++"


def test_year_coercion():
    assert T.coerce_year("٢٠٢٠") == 2020
    assert T.coerce_year("Present") is None
    assert T.coerce_year("الآن") is None
    assert abs(T.coerce_year(1445) - 2023) <= 1  # Hijri year straddles two Gregorian years
    assert T.coerce_year(1899) is None


def test_language_detection_and_target_rule():
    assert T.detect_language("Senior backend engineer") == "en"
    assert T.detect_language("مهندس برمجيات لديه خبرة") == "ar"
    assert T.detect_language("مهندس برمجيات with 5 years of Python experience") == "mixed"
    assert T.resolve_target_language("mixed", "ar", None) == "ar"
    assert T.resolve_target_language("en", "en", "ar") == "ar"  # explicit override wins
    assert T.language_matches("هذا المرشح مناسب للوظيفة مع Python", "ar")
    assert not T.language_matches("This candidate is a good fit", "ar")


def test_garbled_arabic_text_layer_detected():
    presentation = "ﻣﻬﻨﺪﺱ ﺑﺮﻣﺠﻴﺎﺕ" * 20
    assert T.presentation_form_ratio(presentation) > 0.9


def _exp(s, e, cur=False):
    return WorkExperience(title="t", start_year=s, end_year=e, is_current=cur)


def test_experience_years_merges_overlaps():
    assert rules.compute_experience_years([_exp(2015, 2019), _exp(2018, 2021)], today=2026) == 6.0
    assert rules.compute_experience_years([_exp(2020, None, True)], today=2026) == 6.0


def _profile(**kw):
    base = dict(candidate_id="c", source_file="f", name="N", skills=["x"], experience=[], education=[])
    return CandidateProfile(**{**base, **kw})


def test_anomalies():
    p = _profile(experience=[_exp(2010, 2020), _exp(2011, 2021), _exp(2021, 2019)], stated_total_years=25)
    codes = {f.code for f in rules.detect_anomalies(p, today=2026)}
    assert {"overlap_employment", "date_order", "stated_vs_computed_years"} <= codes


def _v(skill, verdict, imp="required"):
    return SkillVerdict(skill=skill, importance=imp, verdict=verdict, method="exact")


def test_score_is_deterministic_and_weighted():
    vs = [_v("a", "met"), _v("b", "partial"), _v("c", "missing")]  # coverage 0.5
    score, br = scoring.compute_score(vs, years=5, min_years=5, relevance="strong", education_fit="meets",
                                      projects_certs="strong", education_required=True)
    assert br == {"experience": 35.0, "skills": 15.0, "education": 20.0, "projects_certs": 15.0}
    assert score == 85.0
    # no education requirement -> full education credit regardless of the LLM's verdict
    _, br2 = scoring.compute_score(vs, 5, 5, "strong", "unrelated", "strong", education_required=False)
    assert br2["education"] == 20.0


def test_triage_rules():
    assert scoring.triage(90, 0.9, [])[0] == "auto_accept"
    assert scoring.triage(20, 0.9, [])[0] == "auto_reject"
    assert scoring.triage(60, 0.9, [])[0] == "review"
    assert scoring.triage(90, 0.4, [])[0] == "review"          # high score, low confidence
    b, reasons = scoring.triage(90, 0.9, [Flag(code="overlap_employment")])
    assert b == "review" and "overlap_employment" in reasons


def test_web_query_is_scrubbed_of_pii():
    from agent.tools.search_tools import scrub_query
    q = scrub_query("kubernetes course for ahmed@mail.com +971 50 123 4567 https://x.io/cv")
    assert "@" not in q and "http" not in q and "4567" not in q
