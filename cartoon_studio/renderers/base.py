from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseRenderer(ABC):
    @abstractmethod
    def prepare(self, project: Any) -> None: ...

    @abstractmethod
    def render_scene(self, scene: Any, context: Any) -> Any: ...

    @abstractmethod
    def render_frame(self, frame: int) -> Any:
        """Render one independent timeline frame as an image-like object."""
        ...

    @abstractmethod
    def signature(self, frame: int) -> str:
        """Return a deterministic hash of everything affecting this frame."""
        ...

    @abstractmethod
    def finalize(self) -> None: ...
