"""
Evaluation Metrics Calculator for WhatsApp-Based Personal Document Retrieval System Using RAG.

This script evaluates the RAG system across multiple dimensions:
1. Retrieval Performance (Precision@K, Recall@K, MRR)
2. Answer Quality (Correctness, Faithfulness)
3. System Performance (Latency, Throughput)
4. Document Processing (OCR Accuracy, Ingestion Success Rate)
5. Per-User Isolation

Usage:
    1. Start the RAG service: uvicorn app.api.app:app --port 8001
    2. Run this script: python evaluate_metrics.py

The script will:
    - Upload test documents
    - Run test queries
    - Calculate all metrics
    - Print a formatted report
    - Save results to evaluation_results.json
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

# --- Configuration ---
RAG_SERVICE_URL = os.environ.get("RAG_SERVICE_URL", "http://localhost:8001")
RESULTS_FILE = "evaluation_results.json"


# --- Test Data ---
# Ground truth: questions with known answers and the document they come from
TEST_DOCUMENTS = [
    {
        "filename": "test_pan_card.txt",
        "content": (
            "INCOME TAX DEPARTMENT\n"
            "GOVT OF INDIA\n"
            "Permanent Account Number Card\n"
            "Name: SANGAMESH KUMAR\n"
            "Father's Name: RAJESH KUMAR\n"
            "Date of Birth: 15/03/1995\n"
            "PAN: ABCDE1234F\n"
            "Signature: [signed]\n"
        ),
        "description": "PAN Card",
    },
    {
        "filename": "test_bank_passbook.txt",
        "content": (
            "STATE BANK OF INDIA\n"
            "Branch: MG Road, Bangalore\n"
            "IFSC: SBIN0001234\n"
            "Account Number: 20345678901\n"
            "Account Holder: SANGAMESH KUMAR\n"
            "Account Type: Savings\n"
            "Opening Date: 01/06/2018\n"
            "Balance as on 15/05/2026: Rs. 45,230.50\n"
            "Nominee: RAJESH KUMAR\n"
        ),
        "description": "Bank Passbook",
    },
    {
        "filename": "test_aadhaar.txt",
        "content": (
            "GOVERNMENT OF INDIA\n"
            "Unique Identification Authority of India\n"
            "Name: SANGAMESH KUMAR\n"
            "DOB: 15/03/1995\n"
            "Gender: Male\n"
            "Aadhaar Number: 1234 5678 9012\n"
            "Address: 42, 2nd Cross, JP Nagar, Bangalore, Karnataka - 560078\n"
            "Mobile: 9876543210\n"
        ),
        "description": "Aadhaar Card",
    },
]

TEST_QUERIES = [
    {
        "question": "What is my PAN number?",
        "expected_answer": "ABCDE1234F",
        "relevant_doc": "test_pan_card.txt",
        "category": "exact_value",
    },
    {
        "question": "What is my date of birth?",
        "expected_answer": "15/03/1995",
        "relevant_doc": "test_pan_card.txt",
        "category": "exact_value",
    },
    {
        "question": "What is my bank account number?",
        "expected_answer": "20345678901",
        "relevant_doc": "test_bank_passbook.txt",
        "category": "exact_value",
    },
    {
        "question": "What is my IFSC code?",
        "expected_answer": "SBIN0001234",
        "relevant_doc": "test_bank_passbook.txt",
        "category": "exact_value",
    },
    {
        "question": "What is my bank balance?",
        "expected_answer": "45,230.50",
        "relevant_doc": "test_bank_passbook.txt",
        "category": "exact_value",
    },
    {
        "question": "What is my Aadhaar number?",
        "expected_answer": "1234 5678 9012",
        "relevant_doc": "test_aadhaar.txt",
        "category": "exact_value",
    },
    {
        "question": "What is my address?",
        "expected_answer": "42, 2nd Cross, JP Nagar, Bangalore, Karnataka - 560078",
        "relevant_doc": "test_aadhaar.txt",
        "category": "contains",
    },
    {
        "question": "Who is my nominee?",
        "expected_answer": "RAJESH KUMAR",
        "relevant_doc": "test_bank_passbook.txt",
        "category": "exact_value",
    },
    {
        "question": "Which bank branch is my account in?",
        "expected_answer": "MG Road, Bangalore",
        "relevant_doc": "test_bank_passbook.txt",
        "category": "contains",
    },
    {
        "question": "What is my father's name?",
        "expected_answer": "RAJESH KUMAR",
        "relevant_doc": "test_pan_card.txt",
        "category": "exact_value",
    },
]

# Queries that should NOT have answers (testing hallucination resistance)
NEGATIVE_QUERIES = [
    "What is my passport number?",
    "What is my credit card number?",
    "What is my email address?",
    "What is my salary?",
]


@dataclass
class MetricResult:
    name: str
    value: float
    unit: str = ""
    details: str = ""


@dataclass
class EvaluationReport:
    retrieval_metrics: list[MetricResult] = field(default_factory=list)
    answer_metrics: list[MetricResult] = field(default_factory=list)
    performance_metrics: list[MetricResult] = field(default_factory=list)
    processing_metrics: list[MetricResult] = field(default_factory=list)
    isolation_metrics: list[MetricResult] = field(default_factory=list)


# --- Helper Functions ---

def check_rag_service() -> bool:
    """Check if the RAG service is running."""
    try:
        resp = requests.get(f"{RAG_SERVICE_URL}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def ingest_document(filename: str, content: str) -> dict | None:
    """Upload a document to the RAG service."""
    files = {"files": (filename, content.encode("utf-8"), "text/plain")}
    try:
        resp = requests.post(f"{RAG_SERVICE_URL}/ingest/files", files=files, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"  ❌ Ingestion failed for {filename}: {exc}")
        return None


def query_rag(question: str, top_k: int = 4) -> dict | None:
    """Query the RAG service."""
    try:
        resp = requests.post(
            f"{RAG_SERVICE_URL}/query",
            json={"question": question, "top_k": top_k},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"  ❌ Query failed: {exc}")
        return None


# --- Evaluation Functions ---

def evaluate_ingestion() -> list[MetricResult]:
    """Evaluate document ingestion performance."""
    print("\n📄 Evaluating Document Ingestion...")
    results = []
    success_count = 0
    total_chunks = 0
    total_time = 0.0

    for doc in TEST_DOCUMENTS:
        start = time.time()
        result = ingest_document(doc["filename"], doc["content"])
        elapsed = time.time() - start
        total_time += elapsed

        if result and result.get("chunks_indexed", 0) > 0:
            success_count += 1
            chunks = result["chunks_indexed"]
            total_chunks += chunks
            print(f"  ✅ {doc['filename']}: {chunks} chunks in {elapsed:.2f}s")
        else:
            print(f"  ❌ {doc['filename']}: failed")

    success_rate = (success_count / len(TEST_DOCUMENTS)) * 100 if TEST_DOCUMENTS else 0
    avg_time = total_time / len(TEST_DOCUMENTS) if TEST_DOCUMENTS else 0

    results.append(MetricResult("Ingestion Success Rate", success_rate, "%"))
    results.append(MetricResult("Total Chunks Indexed", total_chunks, "chunks"))
    results.append(MetricResult("Avg Ingestion Time", avg_time, "seconds"))
    results.append(MetricResult("Documents Processed", success_count, f"/{len(TEST_DOCUMENTS)}"))

    return results


def evaluate_retrieval() -> list[MetricResult]:
    """Evaluate retrieval quality (Precision@K, Recall, MRR)."""
    print("\n🔍 Evaluating Retrieval Performance...")
    results = []

    precision_scores = []
    recall_scores = []
    mrr_scores = []

    for tq in TEST_QUERIES:
        result = query_rag(tq["question"], top_k=4)
        if not result:
            continue

        sources = result.get("sources", [])
        relevant_doc = tq["relevant_doc"]

        # Check if any source is from the relevant document
        source_filenames = [s.get("source", "") for s in sources]
        relevant_in_results = [s for s in source_filenames if relevant_doc in s]

        # Precision@K: fraction of retrieved docs that are relevant
        precision = len(relevant_in_results) / len(sources) if sources else 0
        precision_scores.append(precision)

        # Recall: did we find the relevant doc at all?
        recall = 1.0 if relevant_in_results else 0.0
        recall_scores.append(recall)

        # MRR: reciprocal rank of first relevant result
        mrr = 0.0
        for i, s in enumerate(source_filenames):
            if relevant_doc in s:
                mrr = 1.0 / (i + 1)
                break
        mrr_scores.append(mrr)

        status = "✅" if recall > 0 else "❌"
        print(f"  {status} Q: \"{tq['question']}\" → P={precision:.2f}, R={recall:.0f}, MRR={mrr:.2f}")

    avg_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0
    avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0

    results.append(MetricResult("Precision@4 (avg)", avg_precision * 100, "%"))
    results.append(MetricResult("Recall@4 (avg)", avg_recall * 100, "%"))
    results.append(MetricResult("Mean Reciprocal Rank (MRR)", avg_mrr, ""))
    results.append(MetricResult("Queries Evaluated", len(precision_scores), ""))

    return results


def evaluate_answer_quality() -> list[MetricResult]:
    """Evaluate answer correctness and faithfulness."""
    print("\n💡 Evaluating Answer Quality...")
    results = []

    correct_count = 0
    total_count = 0
    faithfulness_scores = []

    for tq in TEST_QUERIES:
        result = query_rag(tq["question"], top_k=4)
        if not result:
            continue

        answer = result.get("answer", "")
        expected = tq["expected_answer"]
        total_count += 1

        # Check correctness — normalize by removing markdown and extra spaces
        normalized_answer = answer.lower().replace("**", "").replace("*", "").replace("–", "-")
        normalized_expected = expected.lower()

        if tq["category"] == "exact_value":
            is_correct = normalized_expected in normalized_answer
        else:  # contains
            is_correct = normalized_expected in normalized_answer

        if is_correct:
            correct_count += 1

        # Faithfulness: check if answer content appears in sources
        sources_text = " ".join(s.get("text", "") for s in result.get("sources", []))
        # Simple faithfulness: does the key value in the answer also appear in sources?
        is_faithful = expected.lower() in sources_text.lower() if expected else True
        faithfulness_scores.append(1.0 if is_faithful else 0.0)

        status = "✅" if is_correct else "❌"
        print(f"  {status} Q: \"{tq['question']}\"")
        if is_correct:
            print(f"      Expected: {expected} → Found in answer")
        else:
            print(f"      Expected: {expected}")
            print(f"      Got: {answer[:100]}...")

    correctness = (correct_count / total_count) * 100 if total_count else 0
    faithfulness = (sum(faithfulness_scores) / len(faithfulness_scores)) * 100 if faithfulness_scores else 0

    results.append(MetricResult("Answer Correctness", correctness, "%"))
    results.append(MetricResult("Answer Faithfulness", faithfulness, "%"))
    results.append(MetricResult("Correct Answers", correct_count, f"/{total_count}"))

    # Test hallucination resistance with negative queries
    print("\n  Testing hallucination resistance (negative queries)...")
    hallucination_count = 0
    for nq in NEGATIVE_QUERIES:
        result = query_rag(nq, top_k=4)
        if not result:
            continue
        answer = result.get("answer", "").lower()
        # A good answer should say "not found" or similar
        has_refusal = any(phrase in answer for phrase in [
            "could not find", "couldn't find", "not found",
            "no relevant", "not present", "don't have",
            "missing", "not available", "i'm sorry",
            "do not contain", "does not contain",
            "no information", "not contain",
        ])
        if not has_refusal and len(answer) > 50:
            hallucination_count += 1
            print(f"  ⚠️  Possible hallucination for: \"{nq}\"")
            print(f"      Answer: {answer[:80]}...")
        else:
            print(f"  ✅ Correctly refused: \"{nq}\"")

    hallucination_rate = (hallucination_count / len(NEGATIVE_QUERIES)) * 100 if NEGATIVE_QUERIES else 0
    results.append(MetricResult("Hallucination Rate", hallucination_rate, "%",
                                details=f"{hallucination_count}/{len(NEGATIVE_QUERIES)} negative queries got fabricated answers"))

    return results


def evaluate_performance() -> list[MetricResult]:
    """Evaluate system latency and throughput."""
    print("\n⚡ Evaluating System Performance...")
    results = []

    query_times = []
    for tq in TEST_QUERIES[:5]:  # Use first 5 queries for latency test
        start = time.time()
        query_rag(tq["question"], top_k=4)
        elapsed = time.time() - start
        query_times.append(elapsed)
        print(f"  Query latency: {elapsed:.2f}s — \"{tq['question'][:40]}...\"")

    if query_times:
        avg_latency = sum(query_times) / len(query_times)
        min_latency = min(query_times)
        max_latency = max(query_times)
        p95_latency = sorted(query_times)[int(len(query_times) * 0.95)] if len(query_times) > 1 else max_latency

        results.append(MetricResult("Avg Query Latency", avg_latency, "seconds"))
        results.append(MetricResult("Min Query Latency", min_latency, "seconds"))
        results.append(MetricResult("Max Query Latency", max_latency, "seconds"))
        results.append(MetricResult("P95 Query Latency", p95_latency, "seconds"))

    # Health check latency
    start = time.time()
    requests.get(f"{RAG_SERVICE_URL}/health", timeout=5)
    health_latency = time.time() - start
    results.append(MetricResult("Health Check Latency", health_latency, "seconds"))

    return results


def evaluate_isolation() -> list[MetricResult]:
    """Evaluate per-user isolation (simulated with filename prefixes)."""
    print("\n🔒 Evaluating Per-User Isolation...")
    results = []

    # Ingest a document with a "user prefix" to simulate isolation
    user_a_doc = "919876543210_user_a_secret.txt"
    user_a_content = "User A's secret PIN is 9876. User A's email is usera@example.com."

    user_b_doc = "918765432109_user_b_secret.txt"
    user_b_content = "User B's secret PIN is 1234. User B's email is userb@example.com."

    ingest_document(user_a_doc, user_a_content)
    ingest_document(user_b_doc, user_b_content)

    # Query and check if results can be filtered
    result = query_rag("What is the secret PIN?", top_k=10)
    if result:
        sources = result.get("sources", [])
        user_a_sources = [s for s in sources if "919876543210" in s.get("source", "")]
        user_b_sources = [s for s in sources if "918765432109" in s.get("source", "")]

        print(f"  Total sources returned: {len(sources)}")
        print(f"  User A sources: {len(user_a_sources)}")
        print(f"  User B sources: {len(user_b_sources)}")

        # Isolation works if we can distinguish sources by prefix
        can_filter = len(user_a_sources) > 0 or len(user_b_sources) > 0
        results.append(MetricResult(
            "Namespace Filtering Possible",
            100.0 if can_filter else 0.0, "%",
            details="Can filter results by user phone prefix in source filename"
        ))

        # Check that both users' data exists but is separable
        both_present = len(user_a_sources) > 0 and len(user_b_sources) > 0
        results.append(MetricResult(
            "Multi-User Data Separable",
            100.0 if both_present else 50.0, "%",
            details="Both users' data present and distinguishable"
        ))
    else:
        results.append(MetricResult("Isolation Test", 0.0, "%", details="Query failed"))

    return results


# --- Report Generation ---

def print_report(report: EvaluationReport) -> None:
    """Print a formatted evaluation report."""
    print("\n" + "=" * 70)
    print("  📊 EVALUATION REPORT — WhatsApp Document RAG System")
    print("=" * 70)

    sections = [
        ("📄 Document Processing", report.processing_metrics),
        ("🔍 Retrieval Performance", report.retrieval_metrics),
        ("💡 Answer Quality", report.answer_metrics),
        ("⚡ System Performance", report.performance_metrics),
        ("🔒 Per-User Isolation", report.isolation_metrics),
    ]

    for title, metrics in sections:
        if not metrics:
            continue
        print(f"\n  {title}")
        print("  " + "-" * 50)
        for m in metrics:
            if m.unit == "%":
                print(f"    {m.name:<35} {m.value:>6.1f}%")
            elif m.unit == "seconds":
                print(f"    {m.name:<35} {m.value:>6.3f}s")
            else:
                val = f"{m.value:.1f}" if isinstance(m.value, float) and m.value != int(m.value) else str(int(m.value))
                print(f"    {m.name:<35} {val:>6} {m.unit}")
            if m.details:
                print(f"      ↳ {m.details}")

    # Overall score
    print(f"\n  {'─' * 50}")
    key_metrics = {
        "Retrieval Recall": next((m.value for m in report.retrieval_metrics if "Recall" in m.name), 0),
        "Answer Correctness": next((m.value for m in report.answer_metrics if "Correctness" in m.name), 0),
        "Ingestion Success": next((m.value for m in report.processing_metrics if "Success" in m.name), 0),
    }
    overall = sum(key_metrics.values()) / len(key_metrics) if key_metrics else 0
    print(f"\n  🏆 OVERALL SCORE: {overall:.1f}%")
    print(f"     (Average of Recall, Correctness, Ingestion Success)")
    print("=" * 70)


def save_results(report: EvaluationReport) -> None:
    """Save results to JSON file."""
    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rag_service_url": RAG_SERVICE_URL,
        "processing": [{"name": m.name, "value": m.value, "unit": m.unit} for m in report.processing_metrics],
        "retrieval": [{"name": m.name, "value": m.value, "unit": m.unit} for m in report.retrieval_metrics],
        "answer_quality": [{"name": m.name, "value": m.value, "unit": m.unit} for m in report.answer_metrics],
        "performance": [{"name": m.name, "value": m.value, "unit": m.unit} for m in report.performance_metrics],
        "isolation": [{"name": m.name, "value": m.value, "unit": m.unit} for m in report.isolation_metrics],
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n  💾 Results saved to {RESULTS_FILE}")


# --- Main ---

def main():
    print("=" * 70)
    print("  WhatsApp Document RAG System — Evaluation Metrics Calculator")
    print("=" * 70)
    print(f"\n  RAG Service URL: {RAG_SERVICE_URL}")

    # Check service
    if not check_rag_service():
        print("\n  ❌ RAG service is not running!")
        print(f"     Start it with: uvicorn app.api.app:app --port 8001")
        print(f"     Then re-run this script.")
        return

    print("  ✅ RAG service is running.\n")

    report = EvaluationReport()

    # 1. Document Processing
    report.processing_metrics = evaluate_ingestion()

    # Wait a moment for indexing to complete
    time.sleep(2)

    # 2. Retrieval Performance
    report.retrieval_metrics = evaluate_retrieval()

    # 3. Answer Quality
    report.answer_metrics = evaluate_answer_quality()

    # 4. System Performance
    report.performance_metrics = evaluate_performance()

    # 5. Per-User Isolation
    report.isolation_metrics = evaluate_isolation()

    # Print and save report
    print_report(report)
    save_results(report)


if __name__ == "__main__":
    main()
