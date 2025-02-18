from abc import ABC, abstractmethod
from typing import Optional, Union, List, Type
from commandagi_j2.utils.gym2.base_env import Env
from commandagi_j2.utils.gym2.base_agent import BaseAgent
from commandagi_j2.utils.gym2.collector_base import BaseEpisode
from commandagi_j2.utils.gym2.callbacks import Callback


class BaseDriver(ABC):
    """Abstract base class for driving agent-environment interactions."""

    @abstractmethod
    def __init__(
        self,
        env: Optional[Env] = None,
        agent: Optional[BaseAgent] = None,
        episode_cls: Type[BaseEpisode] = None,
        callbacks: Optional[List[Callback]] = None,
    ):
        """Initialize the driver.

        Args:
            env (Optional[Env]): The environment to use
            agent (Optional[BaseAgent]): The agent to use
            episode_cls (Type[BaseEpisode]): The episode class to use
            callbacks (Optional[List[Callback]]): List of callbacks to register
        """

    @abstractmethod
    def run_episode(
        self,
        max_steps: int = 100,
        episode_name: Optional[str] = None,
        return_episode: bool = False,
    ) -> Union[float, BaseEpisode]:
        """Run a single episode.

        Args:
            max_steps (int): Maximum number of steps to run
            episode_name (Optional[str]): Episode identifier for data collection
            return_episode (bool): Whether to return the full episode data

        Returns:
            Union[float, Episode]: Either the total reward or full episode data
        """

    @abstractmethod
    def reset(self) -> None:
        """Reset the driver's state."""

    @property
    def callbacks(self):
        if not hasattr(self, "_callbacks"):
            self._callbacks = []
        return self._callbacks

    def register_callback(self, callback: Callback) -> None:
        """Register a callback to be used during episode execution."""
        self.callbacks.append(callback)
