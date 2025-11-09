"""Sprite loading helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from PyQt6.QtGui import QPixmap, QTransform

from .config import CONFIG, SpriteConfig, SpriteStateConfig


@dataclass
class SpriteAnimation:
    state: SpriteStateConfig
    frames: List[QPixmap]
    mirrored_frames: List[QPixmap] | None = field(default=None, init=False)

    @property
    def frame_interval_ms(self) -> int:
        return self.state.frame_interval_ms

    def _ensure_mirrored_frames(self) -> List[QPixmap]:
        if self.mirrored_frames is None:
            transform = QTransform().scale(-1, 1)
            self.mirrored_frames = [frame.transformed(transform) for frame in self.frames]
        return self.mirrored_frames

    def frame(self, index: int, mirror: bool = False) -> QPixmap:
        if not self.frames:
            raise ValueError(f"No frames loaded for state {self.state.name}")
        frames = self._ensure_mirrored_frames() if mirror else self.frames
        return frames[index % len(frames)]

    @property
    def length(self) -> int:
        return len(self.frames)


class Sprites:
    """Preload the pixmaps for each animation state."""

    def __init__(self, sprite_config: SpriteConfig | None = None):
        self.config = sprite_config or CONFIG.sprites
        self.animations: Dict[str, SpriteAnimation] = {}
        self._load()

    def _load(self) -> None:
        for name, state_cfg in self.config.states.items():
            animation = self._load_animation(state_cfg)
            self.animations[name] = animation

    def _load_animation(self, state_cfg: SpriteStateConfig) -> SpriteAnimation:
        path = self.config.resolve_path(state_cfg.file)
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            raise FileNotFoundError(f"Cannot load sprite '{state_cfg.name}' from {path}")
        frames = self._slice_frames(pixmap, state_cfg)
        if not frames:
            frames = [pixmap]
        return SpriteAnimation(state=state_cfg, frames=frames)

    def _slice_frames(self, pixmap: QPixmap, state_cfg: SpriteStateConfig) -> List[QPixmap]:
        frame_total = max(1, state_cfg.frames)
        if frame_total == 1:
            return [pixmap]

        if state_cfg.frame_size:
            frame_width, frame_height = state_cfg.frame_size
        elif state_cfg.layout == "vertical":
            frame_width = pixmap.width()
            frame_height = pixmap.height() // frame_total
        else:
            frame_width = pixmap.width() // frame_total
            frame_height = pixmap.height()

        frames: List[QPixmap] = []
        for index in range(frame_total):
            x = index * frame_width if state_cfg.layout != "vertical" else 0
            y = index * frame_height if state_cfg.layout == "vertical" else 0
            if x + frame_width > pixmap.width() or y + frame_height > pixmap.height():
                break
            frames.append(pixmap.copy(x, y, frame_width, frame_height))
        return frames

    def get(self, state: str) -> SpriteAnimation:
        if state in self.animations:
            return self.animations[state]
        if "idle" in self.animations:
            return self.animations["idle"]
        raise KeyError(f"No animation loaded for state '{state}'.")

    @property
    def idle(self) -> SpriteAnimation:
        return self.get("idle")

    @property
    def walk(self) -> SpriteAnimation:
        return self.get("walk")
