from agent.state import CandidateProfile, JobChunk, JobRequirement
from rag import bulk


def test_index_directory_isolates_cv_failures(tmp_path, monkeypatch):
    (tmp_path / "good.txt").write_text("good", encoding="utf-8")
    (tmp_path / "bad.txt").write_text("bad", encoding="utf-8")
    (tmp_path / "ignored.csv").write_text("ignored", encoding="utf-8")

    def fake_index(path, language):
        if path.endswith("bad.txt"):
            raise ValueError("invalid CV")
        return CandidateProfile(candidate_id="good-id", source_file="good.txt", name="Good")

    monkeypatch.setattr(bulk, "index_cv", fake_index)
    result = bulk.index_directory(str(tmp_path), "en")

    assert result[str(tmp_path / "good.txt")] == "good-id"
    assert result[str(tmp_path / "bad.txt")].startswith("ERROR: ValueError")
    assert str(tmp_path / "ignored.csv") not in result


def test_shortlist_uses_structured_job_query(monkeypatch):
    req = JobRequirement(job_id="devops", job_version="v1", title="DevOps Engineer",
                         required_skills=["Kubernetes", "Terraform"],
                         responsibilities_summary="Operate cloud platforms.")
    monkeypatch.setattr(bulk.store, "get_job", lambda job_id: (req, [
        JobChunk(section="Requirements", text="Deploy and operate Kubernetes clusters.")]))
    seen = {}
    monkeypatch.setattr(bulk.store, "search_candidates", lambda query, k: seen.update(query=query, k=k) or
                        [{"candidate_id": "c1", "retrieval_score": 0.9}])

    result = bulk.shortlist_job("devops", top_k=12)

    assert result == [{"candidate_id": "c1", "retrieval_score": 0.9}]
    assert seen["k"] == 12
    assert "Kubernetes" in seen["query"] and "DevOps Engineer" in seen["query"]
