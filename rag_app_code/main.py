import os
import json
from pathlib import Path
from vectorstore.qdrant_client import seed_vectorstore_from_rag_data
from rag.retriever import retrieve_matching_jds
from rag.evaluator import evaluate_candidate_against_jds
from rag.extractor import extract_and_format_candidate_en

def read_all_cv_files(cv_folder: str = "cv_data") -> list[tuple[str, str]]:
    """Reads all text, markdown, or JSON CV files from cv_data directory.
    
    Returns a list of tuples: [(file_name, cv_content), ...]
    """
    cv_dir = Path(cv_folder)
    
    # Collect all supported files
    cv_files = (
        list(cv_dir.glob("*.txt")) 
        + list(cv_dir.glob("*.json")) 
        + list(cv_dir.glob("*.md"))
    )
    
    if not cv_files:
        raise FileNotFoundError(f"No CV files (.txt, .json, .md) found inside {cv_folder}/ directory.")
    
    cv_records = []
    for file_path in cv_files:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix == ".json":
                data = json.load(f)
                content = json.dumps(data, ensure_ascii=False)
            else:
                content = f.read()
            cv_records.append((file_path.name, content))
            
    return cv_records

def save_result_checkpoint(file_name: str, english_preview: str, matched_jds: list, evaluation) -> Path:
    """Saves evaluation output for a specific candidate into result/ directory."""
    result_dir = Path("result")
    result_dir.mkdir(exist_ok=True)
    
    # Create distinct report file based on the input CV filename
    safe_name = Path(file_name).stem
    checkpoint_path = result_dir / f"checkpoint_{safe_name}.md"

    top_jd = matched_jds[0] if matched_jds else {}

    content = f"""================ EVALUATION CHECKPOINT [{safe_name}] ================

[FILE NAME]
{file_name}

[CANDIDATE CV PREVIEW]
{english_preview}

[TARGET JOB REQUIREMENT]
Title: {top_jd.get('title', 'N/A')}

[EVALUATION METRICS]
Match Score: {evaluation.match_score}%

[STRENGTHS]
"""
    for s in evaluation.strengths:
        content += f"- {s}\n"

    content += "\n[GAPS & MISSING SKILLS]\n"
    for g in evaluation.gaps:
        content += f"- {g}\n"

    content += f"\n[RECOMMENDATION]\n{evaluation.recommendation}\n"

    with open(checkpoint_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Saved report to: {checkpoint_path}")
    return checkpoint_path

def main():
    print("1. Seeding vector database with job description embeddings...")
    seed_vectorstore_from_rag_data()

    print("\n2. Fetching all CV files from cv_data directory...")
    cv_records = read_all_cv_files("cv_data")
    print(f"Found {len(cv_records)} CV(s) to process.")

    # Process each CV sequentially
    for index, (file_name, cv_text) in enumerate(cv_records, start=1):
        print("\n" + "="*50)
        print(f"Processing CV [{index}/{len(cv_records)}]: {file_name}")
        print("="*50)

        print("3. Extracting English candidate preview...")
        extracted_data, english_preview = extract_and_format_candidate_en(cv_text)

        print("4. Retrieving top matching job requirements...")
        matched_jds = retrieve_matching_jds(cv_text, top_k=1)

        print("5. Evaluating candidate CV against job requirements...")
        evaluation = evaluate_candidate_against_jds(cv_text, matched_jds)

        print(f"\nMatch Score: {evaluation.match_score}%")
        print("Key Strengths:")
        for s in evaluation.strengths:
            print(f"  - {s}")
        
        print("\nIdentified Gaps:")
        for g in evaluation.gaps:
            print(f"  - {g}")
            
        print(f"\nFinal Recommendation:\n{evaluation.recommendation}")

        # Save checkpoint per candidate
        save_result_checkpoint(file_name, english_preview, matched_jds, evaluation)

if __name__ == "__main__":
    main()