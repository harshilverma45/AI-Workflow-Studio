from types import SimpleNamespace

from app.workflows.loop_graph import build_loop_graph, response_text


def initial_state(max_iterations: int = 2, quality_threshold: float = 0.85) -> dict[str, object]:
    """Create the initial state used by the loop graph tests."""
    return {
        "original_prompt": "Explain iterative improvement.",
        "current_prompt": "Explain iterative improvement.",
        "response": "",
        "evaluation": "",
        "score": 0.0,
        "iteration_number": 1,
        "max_iterations": max_iterations,
        "quality_threshold": quality_threshold,
        "iteration_results": [],
    }


class FakeModel:
    """Return scripted model responses without making network requests."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> SimpleNamespace:
        """Return the next scripted response and record the request prompt."""
        self.prompts.append(prompt)
        return SimpleNamespace(content=next(self.responses))


def test_response_text_extracts_text_blocks_without_serializing_other_content() -> None:
    """Structured model content should not leak into the user-facing answer."""
    content = [
        {"type": "text", "text": "Readable answer"},
        {"type": "image", "data": "very-long-encoded-payload"},
    ]

    assert response_text(content) == "Readable answer"


def test_score_is_parsed_and_passing_score_stops_early() -> None:
    """A passing score should finish after the first critique."""
    model = FakeModel(["Draft answer", "SCORE: 0.90\nStrong answer."])

    result = build_loop_graph(model).invoke(initial_state(max_iterations=3))

    assert result["score"] == 0.9
    assert result["iteration_number"] == 1
    assert len(result["iteration_results"]) == 1
    assert len(model.prompts) == 2


def test_low_score_routes_through_improvement() -> None:
    """A low score should trigger another generation iteration."""
    model = FakeModel(
        [
            "First draft",
            "SCORE: 0.40\nAdd more detail.",
            "Improved draft",
            "SCORE: 0.90\nClear and complete.",
        ]
    )

    result = build_loop_graph(model).invoke(initial_state())

    assert len(result["iteration_results"]) == 2
    assert result["score"] == 0.9
    assert "Improve this answer" in model.prompts[2]


def test_maximum_iterations_stops_when_score_stays_low() -> None:
    """The graph should stop at the configured maximum iteration count."""
    model = FakeModel(
        [
            "First draft",
            "SCORE: 0.30\nNeeds work.",
            "Second draft",
            "SCORE: 0.40\nStill needs work.",
        ]
    )

    result = build_loop_graph(model).invoke(initial_state(max_iterations=2))

    assert len(result["iteration_results"]) == 2
    assert result["score"] == 0.4
    assert len(model.prompts) == 4


def test_malformed_score_defaults_to_zero_and_respects_limit() -> None:
    """A critique without a parseable score should not bypass the loop limit."""
    model = FakeModel(
        [
            "First draft",
            "This critique forgot the score.",
            "Second draft",
            "No numeric score here either.",
        ]
    )

    result = build_loop_graph(model).invoke(initial_state(max_iterations=2))

    assert len(result["iteration_results"]) == 2
    assert result["score"] == 0.0
