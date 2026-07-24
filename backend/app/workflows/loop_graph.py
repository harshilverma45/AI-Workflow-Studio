import re
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class LoopState(TypedDict):
    """State carried between generation, critique, and improvement nodes."""

    original_prompt: str
    current_prompt: str
    response: str
    evaluation: str
    score: float
    iteration_number: int
    max_iterations: int
    quality_threshold: float
    iteration_results: list[dict[str, object]]


def response_text(content: Any) -> str:
    """Extract displayable text from LangChain's string or structured content."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        text = content.get("text")
        return text if isinstance(text, str) else ""
    if isinstance(content, list):
        return "\n".join(
            item["text"]
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        )
    return str(content)


def build_loop_graph(model: Any):
    """Build a Gemini-backed Loop Engineering graph."""

    def generate(state: LoopState) -> dict[str, object]:
        """Generate an answer for the current prompt."""
        response = model.invoke(
            "Generate the best possible answer for this user prompt. "
            f"User prompt:\n\n{state['current_prompt']}"
        )
        return {"response": response_text(response.content)}

    def critique(state: LoopState) -> dict[str, object]:
        """Critique the generated answer and extract its numeric score."""
        evaluation_response = model.invoke(
            "Critique the answer below. Return a score from 0.0 to 1.0 on the first line "
            "using exactly 'SCORE: number', then explain the most important improvement.\n\n"
            f"User prompt: {state['original_prompt']}\n\nAnswer: {state['response']}"
        )
        evaluation = response_text(evaluation_response.content)
        score_match = re.search(
            r"SCORE:\s*(0(?:\.\d+)?|1(?:\.0+)?)", evaluation, re.IGNORECASE
        )
        score = float(score_match.group(1)) if score_match else 0.0
        result = {
            "iteration_number": state["iteration_number"],
            "prompt": state["current_prompt"],
            "response": state["response"],
            "evaluation": evaluation,
            "score": score,
        }
        return {
            "evaluation": evaluation,
            "score": score,
            "iteration_results": [*state["iteration_results"], result],
        }

    def should_continue(state: LoopState) -> str:
        """Choose whether to improve the answer or finish the graph."""
        if (
            state["score"] >= state["quality_threshold"]
            or state["iteration_number"] >= state["max_iterations"]
        ):
            return "finish"
        return "improve"

    def improve(state: LoopState) -> dict[str, object]:
        """Prepare the next generation prompt from the critique."""
        return {
            "iteration_number": state["iteration_number"] + 1,
            "current_prompt": (
                f"Improve this answer using the critique. Original prompt: "
                f"{state['original_prompt']}\n\nAnswer: {state['response']}\n\n"
                f"Critique: {state['evaluation']}"
            ),
        }

    graph = StateGraph(LoopState)
    graph.add_node("generate", generate)
    graph.add_node("critique", critique)
    graph.add_node("improve", improve)
    graph.set_entry_point("generate")
    graph.add_edge("generate", "critique")
    graph.add_conditional_edges(
        "critique",
        should_continue,
        {"improve": "improve", "finish": END},
    )
    graph.add_edge("improve", "generate")
    return graph.compile()
