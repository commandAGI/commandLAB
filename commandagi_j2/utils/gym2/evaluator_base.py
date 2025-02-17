from abc import ABC, abstractmethod
from typing import Any
from commandagi_j2.utils.gym2.collector_base import BaseEpisode
from commandagi_j2.utils.gym2.env_base import Mandate


class BaseEvaluator(ABC):
    """Abstract base class for evaluating agent episodes.

    >>> from commandagi_j2.utils.gym2.evaluator_base import BaseEvaluator
    >>> issubclass(BaseEvaluator, ABC)
    True
    """

    @abstractmethod
    def evaluate_episode(self, episode: BaseEpisode, mandate: Mandate) -> Any:
        """Evaluate an episode against a given mandate.

        Args:
            episode (Episode): The episode to evaluate
            mandate (Mandate): The criteria/goals the episode should satisfy

        Returns:
            Any: The evaluation result, format determined by implementation

        >>> class MockEvaluator(BaseEvaluator):
        ...     def evaluate_episode(self, episode, mandate): return {"score": 1.0}
        ...     def get_metrics(self): return {"avg_score": 1.0}
        >>> evaluator = MockEvaluator()
        >>> result = evaluator.evaluate_episode(None, "test_mandate")
        >>> result["score"]
        1.0
        """

    @abstractmethod
    def get_metrics(self) -> dict:
        """Get evaluation metrics.

        Returns:
            dict: A dictionary of evaluation metrics

        >>> class MockEvaluator(BaseEvaluator):
        ...     def evaluate_episode(self, episode, mandate): return {"score": 1.0}
        ...     def get_metrics(self): return {"avg_score": 1.0}
        >>> evaluator = MockEvaluator()
        >>> metrics = evaluator.get_metrics()
        >>> metrics["avg_score"]
        1.0
        """
