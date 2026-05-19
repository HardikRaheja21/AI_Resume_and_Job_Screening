import pytest
from backend.services import answer_evaluator
from backend.utils.config import settings


def test_heuristic_evaluation_strong_answer():
    result = answer_evaluator.evaluate_answer_heuristic(
        question="Explain the difference between Python lists and tuples.",
        answer="Lists are mutable, meaning you can modify their elements after creation. Tuples are immutable, so once created, you cannot change them. This immutability makes tuples hashable and useful as dictionary keys.",
        expected_keywords=["mutable", "immutable", "hashable"],
        difficulty_level=1,
    )
    assert result["score"] >= 7.0
    assert "mutable" in result["matched_keywords"]
    assert "immutable" in result["matched_keywords"]
    assert result["recommendation"] in ["select", "hold"]


def test_heuristic_evaluation_weak_answer():
    result = answer_evaluator.evaluate_answer_heuristic(
        question="Explain the difference between Python lists and tuples.",
        answer="different",
        expected_keywords=["mutable", "immutable", "hashable"],
        difficulty_level=1,
    )
    assert result["score"] < 5.0
    assert result["recommendation"] == "reject"
    assert "Answer is too short" in result["feedback"]


def test_heuristic_evaluation_partial_answer():
    result = answer_evaluator.evaluate_answer_heuristic(
        question="How do you optimize a slow SQL query?",
        answer="You can add indexes to make queries faster.",
        expected_keywords=["index", "explain", "query plan"],
        difficulty_level=2,
    )
    assert 4.0 <= result["score"] < 8.0
    assert "index" in result["matched_keywords"]


def test_heuristic_evaluation_with_concepts():
    result = answer_evaluator.evaluate_answer_heuristic(
        question="Describe a difficult technical problem you solved.",
        answer="We had performance issues because we were doing N+1 queries. We debugged this by enabling query logging and found the optimization opportunity. The strategy was to implement batch loading.",
        expected_keywords=["performance", "optimization", "debug"],
        difficulty_level=2,
    )
    assert result["score"] >= 7.0
    concept_score = result["scoring_details"]["concept_score"]
    assert concept_score > 0.5


def test_heuristic_evaluation_voice_input():
    result = answer_evaluator.evaluate_answer_heuristic(
        question="What is dependency injection?",
        answer="Dependency injection is when you pass dependencies to a component instead of having it create them.",
        expected_keywords=["dependencies", "inject"],
        difficulty_level=1,
        input_type="voice",
    )
    assert "Voice transcript" in result["feedback"]
    assert result["input_type" if "input_type" in result else "scoring_details"].get("input_type", "text") == "text"


def test_semantic_evaluation_strong_answer(monkeypatch):
    monkeypatch.setattr(settings, "MATCHER_DISABLE_EMBEDDINGS", False)
    result = answer_evaluator.evaluate_answer_semantic(
        question="Explain the difference between lists and tuples in Python.",
        answer="Lists are mutable collections that can be modified after creation, while tuples are immutable and cannot be changed. Tuples can be used as dictionary keys because of their immutability.",
        expected_keywords=["mutable", "immutable"],
        expected_concepts=["mutability", "immutability", "hashability"],
        difficulty_level=1,
    )
    assert "score" in result
    assert 0.0 <= result["score"] <= 10.0
    assert "feedback" in result
    assert "recommendation" in result
    assert "scoring_details" in result


def test_semantic_evaluation_with_concepts(monkeypatch):
    monkeypatch.setattr(settings, "MATCHER_DISABLE_EMBEDDINGS", False)
    result = answer_evaluator.evaluate_answer_semantic(
        question="How would you optimize a slow SQL query?",
        answer="First, I'd use EXPLAIN to analyze the query plan. Then I'd check if adding indexes on frequently filtered columns would help. I'd also consider denormalization or query restructuring based on the performance characteristics.",
        expected_keywords=["explain", "index", "optimize"],
        expected_concepts=["query performance", "database optimization", "indexing strategy"],
        difficulty_level=2,
    )
    assert result["score"] >= 5.0
    assert result["scoring_details"]["semantic_question_score"] >= 0.0
    assert result["scoring_details"]["semantic_relevance_score"] >= 0.0


def test_semantic_evaluation_uses_retrieval_context(monkeypatch):
    monkeypatch.setattr(settings, "MATCHER_DISABLE_EMBEDDINGS", False)
    monkeypatch.setattr(
        answer_evaluator,
        "_retrieve_resume_chunks",
        lambda **kwargs: [
            {
                "chunk_type": "projects",
                "content_snippet": "Built a scalable REST API backend with authentication and caching.",
                "document": "Built a scalable REST API backend with authentication and caching.",
            },
            {
                "chunk_type": "experience",
                "content_snippet": "5 years experience in backend engineering with Python and SQL.",
                "document": "5 years experience in backend engineering with Python and SQL.",
            },
        ],
    )
    result = answer_evaluator.evaluate_answer_semantic(
        question="How would you secure a production API?",
        answer="I would use authentication, authorization, encryption, and caching to protect endpoints and improve performance.",
        expected_keywords=["authentication", "authorization"],
        difficulty_level=2,
        session="dummy",
        current_user="dummy",
        resume_id=1,
    )
    assert result["retrieval_used"] is True
    assert result["technical_depth"] >= 0.0
    assert "missing_concepts" in result
    assert result["confidence_score"] >= 0.0


def test_semantic_evaluation_difficulty_adjustment(monkeypatch):
    monkeypatch.setattr(settings, "MATCHER_DISABLE_EMBEDDINGS", False)
    strong_result = answer_evaluator.evaluate_answer_semantic(
        question="Explain Python generators.",
        answer="Generators use the yield keyword to produce values one at a time, allowing memory-efficient iteration over large datasets without loading everything into memory at once.",
        expected_keywords=["yield", "memory", "iteration"],
        difficulty_level=2,
    )
    assert strong_result["next_difficulty"] >= 2

    weak_result = answer_evaluator.evaluate_answer_semantic(
        question="Explain Python generators.",
        answer="generators are things",
        expected_keywords=["yield", "memory", "iteration"],
        difficulty_level=2,
    )
    assert weak_result["next_difficulty"] <= 2


def test_semantic_evaluation_score_bounds():
    result = answer_evaluator.evaluate_answer_semantic(
        question="What is a variable?",
        answer="a variable is a named location in memory that stores a value which can change during program execution",
        expected_keywords=["memory", "value"],
        difficulty_level=1,
    )
    assert 0.0 <= result["score"] <= 10.0
    for key in ["heuristic_score", "semantic_question_score", "semantic_relevance_score"]:
        assert 0.0 <= result["scoring_details"][key] <= 10.0


def test_heuristic_and_semantic_consistency():
    """Verify heuristic and semantic methods return compatible structures."""
    question = "Explain REST APIs."
    answer = "REST uses HTTP methods GET, POST, PUT, DELETE to perform operations on resources identified by URIs."
    keywords = ["HTTP", "REST", "resources"]
    
    heuristic = answer_evaluator.evaluate_answer_heuristic(
        question=question, answer=answer, expected_keywords=keywords
    )
    semantic = answer_evaluator.evaluate_answer_semantic(
        question=question, answer=answer, expected_keywords=keywords
    )
    
    for key in ["score", "feedback", "matched_keywords", "next_difficulty", "recommendation", "question"]:
        assert key in heuristic
        assert key in semantic
    
    assert "scoring_details" in heuristic
    assert "scoring_details" in semantic


def test_answer_with_empty_keywords():
    result = answer_evaluator.evaluate_answer_heuristic(
        question="Tell me about yourself.",
        answer="I have 5 years of software development experience.",
        expected_keywords=[],
        difficulty_level=1,
    )
    assert result["score"] >= 0.0
    assert len(result["matched_keywords"]) == 0


def test_answer_with_special_characters():
    result = answer_evaluator.evaluate_answer_heuristic(
        question="What is a hash function?",
        answer="A hash function maps input data to fixed-size output using mathematical operations (e.g., SHA-256).",
        expected_keywords=["hash", "function", "mathematical"],
        difficulty_level=1,
    )
    assert result["score"] >= 5.0
    assert "hash" in result["matched_keywords"]


def test_semantic_evaluation_embeddings_disabled(monkeypatch):
    monkeypatch.setattr(settings, "MATCHER_DISABLE_EMBEDDINGS", True)
    result = answer_evaluator.evaluate_answer_semantic(
        question="What is Python?",
        answer="Python is a high-level programming language known for its simplicity and readability.",
        expected_keywords=["programming", "language"],
        difficulty_level=1,
    )
    assert result["scoring_details"]["semantic_question_score"] == 0.0
    assert result["scoring_details"]["semantic_relevance_score"] == 0.0
