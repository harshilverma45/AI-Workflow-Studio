from app.core.config import settings
from app.workflows.loop_graph import build_loop_graph


class LoopEngine:
    """Run the configured Gemini workflow or a local test fallback."""

    def run(self, prompt: str) -> dict[str, object]:
        """Run one generation and evaluation cycle for the provided prompt."""
        if settings.model_provider.lower() == "gemini":
            return self._run_gemini(prompt)

        return self._run_deterministic(prompt)

    def _run_deterministic(self, prompt: str) -> dict[str, object]:
        """Run a dependency-free local execution for development and testing."""
        response = f"Draft response for: {prompt}"
        evaluation = "The draft directly addresses the requested prompt."
        score = 0.85
        return {
            "prompt": prompt,
            "iterations": 1,
            "final_response": response,
            "quality_score": score,
            "iteration_results": [
                {
                    "iteration_number": 1,
                    "prompt": prompt,
                    "response": response,
                    "evaluation": evaluation,
                    "score": score,
                }
            ],
        }

    def _run_gemini(self, prompt: str) -> dict[str, object]:
        """Run Gemini generation, critique, scoring, and improvement steps."""
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is required when MODEL_PROVIDER=gemini. "
                "Use MODEL_PROVIDER=local for offline tests."
            )

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as error:
            raise RuntimeError(
                "Gemini support is not installed. Run 'pip install langchain-google-genai'."
            ) from error

        model = ChatGoogleGenerativeAI(
            google_api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            temperature=0,
        )

        graph = build_loop_graph(model)
        result = graph.invoke(
            {
                "original_prompt": prompt,
                "current_prompt": prompt,
                "response": "",
                "evaluation": "",
                "score": 0.0,
                "iteration_number": 1,
                "max_iterations": settings.max_iterations,
                "quality_threshold": settings.quality_threshold,
                "iteration_results": [],
            }
        )
        iteration_results = result["iteration_results"]
        return {
            "prompt": prompt,
            "iterations": len(iteration_results),
            "final_response": result["response"],
            "quality_score": result["score"],
            "iteration_results": iteration_results,
        }
