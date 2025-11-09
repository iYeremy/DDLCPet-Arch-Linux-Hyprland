"""Utilities to load strongly-typed configuration from config.toml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import tomllib

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.toml"


@dataclass(frozen=True)
class WindowConfig:
    size: Tuple[int, int]
    bottom_offset: int


@dataclass(frozen=True)
class MovementConfig:
    speed: float
    update_rate_ms: int
    state_interval_ms: int
    walk_speed_range: Tuple[float, float]
    walk_interval_ms: Tuple[int, int]
    turn_probability: float
    turn_cooldown_ms: int
    bob_amplitude: int
    bob_speed: float


@dataclass(frozen=True)
class PhysicsConfig:
    gravity: float
    hop_impulse: float
    hover_impulse: float
    hop_interval_ms: Tuple[int, int]
    hover_cooldown_ms: int
    ground_drag: float
    air_drag: float
    bounce_damping: float
    launch_multiplier: float
    max_speed_x: float
    max_speed_y: float


@dataclass(frozen=True)
class SpriteStateConfig:
    name: str
    file: str
    frames: int = 1
    fps: int = 8
    layout: str = "horizontal"  # horizontal or vertical sheets
    frame_size: Optional[Tuple[int, int]] = None

    @property
    def frame_interval_ms(self) -> int:
        fps = max(1, self.fps)
        return max(16, int(1000 / fps))


@dataclass(frozen=True)
class SpriteConfig:
    base_path: Path
    states: Dict[str, SpriteStateConfig]

    def resolve_state(self, name: str) -> SpriteStateConfig:
        if name in self.states:
            return self.states[name]
        if "idle" in self.states:
            return self.states["idle"]
        raise KeyError(f"No sprite state configured for '{name}'.")

    def resolve_path(self, filename: str) -> Path:
        return self.base_path / filename


@dataclass(frozen=True)
class DeskPetConfig:
    window: WindowConfig
    movement: MovementConfig
    physics: PhysicsConfig
    sprites: SpriteConfig


def _ensure_tuple(values: Iterable[int | float]) -> Tuple[int, int]:
    a, b = tuple(values)
    return int(a), int(b)


def _ensure_tuple_optional(values: Optional[Iterable[int | float]]) -> Optional[Tuple[int, int]]:
    if values is None:
        return None
    return _ensure_tuple(values)


def _ensure_float_tuple(values: Iterable[int | float]) -> Tuple[float, float]:
    a, b = tuple(values)
    return float(a), float(b)


def _load_raw_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing configuration file: {path}")
    with path.open("rb") as file:
        return tomllib.load(file)


def load_config(path: Path | None = None) -> DeskPetConfig:
    """Load the TOML config file and convert it into dataclasses."""
    path = path or CONFIG_PATH
    raw = _load_raw_config(path)

    window = WindowConfig(
        size=_ensure_tuple(raw["window"]["size"]),
        bottom_offset=int(raw["window"]["bottom_offset"]),
    )

    movement = MovementConfig(
        speed=float(raw["movement"]["speed"]),
        update_rate_ms=int(raw["movement"]["update_rate_ms"]),
        state_interval_ms=int(raw["movement"]["state_interval_ms"]),
        walk_speed_range=_ensure_float_tuple(raw["movement"]["walk_speed_range"]),
        walk_interval_ms=_ensure_tuple(raw["movement"]["walk_interval_ms"]),
        turn_probability=float(raw["movement"].get("turn_probability", 0.0)),
        turn_cooldown_ms=int(raw["movement"].get("turn_cooldown_ms", 0)),
        bob_amplitude=int(raw["movement"].get("bob_amplitude", 0)),
        bob_speed=float(raw["movement"].get("bob_speed", 0.0)),
    )

    physics_section = raw.get("physics", {})
    hop_interval = _ensure_tuple(physics_section.get("hop_interval_ms", (800, 2000)))
    physics = PhysicsConfig(
        gravity=float(physics_section.get("gravity", 0.35)),
        hop_impulse=float(physics_section.get("hop_impulse", 4.0)),
        hover_impulse=float(physics_section.get("hover_impulse", 6.0)),
        hop_interval_ms=hop_interval,
        hover_cooldown_ms=int(physics_section.get("hover_cooldown_ms", 900)),
        ground_drag=float(physics_section.get("ground_drag", 0.12)),
        air_drag=float(physics_section.get("air_drag", 0.02)),
        bounce_damping=float(physics_section.get("bounce_damping", 0.5)),
        launch_multiplier=float(physics_section.get("launch_multiplier", 0.02)),
        max_speed_x=float(physics_section.get("max_speed_x", 8.0)),
        max_speed_y=float(physics_section.get("max_speed_y", 14.0)),
    )

    sprite_section = raw["sprites"]
    base_path = sprite_section.get("base_path", "assets")
    states_raw = sprite_section.get("states", {})
    states: Dict[str, SpriteStateConfig] = {}
    for name, data in states_raw.items():
        states[name] = SpriteStateConfig(
            name=name,
            file=data["file"],
            frames=int(data.get("frames", 1)),
            fps=int(data.get("fps", 8)),
            layout=data.get("layout", "horizontal"),
            frame_size=_ensure_tuple_optional(data.get("frame_size")),
        )

    sprites = SpriteConfig(
        base_path=(PROJECT_ROOT / base_path).resolve(),
        states=states,
    )

    return DeskPetConfig(window=window, movement=movement, physics=physics, sprites=sprites)


CONFIG = load_config()
