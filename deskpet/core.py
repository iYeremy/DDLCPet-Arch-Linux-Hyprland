from __future__ import annotations

import math
import random
import time
from collections import deque
from typing import Deque, Optional, Tuple

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import QEnterEvent, QHoverEvent, QMouseEvent
from PyQt6.QtWidgets import QLabel

from .config import CONFIG, DeskPetConfig
from .sprites import SpriteAnimation, Sprites


class DeskPet(QLabel):
    """Mascota con física ligera inspirada en el proyecto de GameMaker."""

    def __init__(self, screen_geometry, config: DeskPetConfig | None = None):
        super().__init__()

        self.config = config or CONFIG
        self._screen_geometry = screen_geometry
        self.sprites = Sprites(self.config.sprites)

        self.current_animation: SpriteAnimation | None = None
        self._current_animation_name: str | None = None
        self.current_frame_index = 0
        self._mirror_current_animation = False

        # Ventana sin bordes, transparente y con eventos de hover.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setScaledContents(True)

        self.resize(*self.config.window.size)
        self._position_at_bottom_center()

        self.pos_x = float(self.x)
        self.pos_y = float(self.y)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.state = "idle"
        self._on_ground = True
        self._bob_phase = random.uniform(0.0, math.tau)
        self._ground_settle_ms = 0.0

        # Temporizadores internos
        self._time_to_next_hop_ms = self._random_hop_delay()
        self._time_to_next_walk_ms = self._random_walk_interval()
        self._hover_cooldown_ms = 0
        self._cursor_inside = False
        self._hover_enter_time = 0.0
        self._hover_trigger_delay = 0.15
        self._last_hover_pos: Optional[QPoint] = None
        self._hover_active = False
        self._hover_anchor_x: Optional[float] = None

        # Datos para drag estilo “golf”
        self._dragging = False
        self._drag_offset = QPoint(0, 0)
        self._drag_samples: Deque[Tuple[float, QPoint]] = deque(maxlen=12)

        # Timers principales
        self.move_timer = QTimer()
        self.move_timer.timeout.connect(self.move_pet)
        self.move_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.move_timer.start(self.config.movement.update_rate_ms)

        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._advance_animation)
        self.animation_timer.setTimerType(Qt.TimerType.PreciseTimer)

        self._apply_state_animation("idle")

    # ------------------------------------------------------------------
    # Geometría y animaciones
    # ------------------------------------------------------------------

    def _screen_rect(self) -> QRect:
        screen = self.screen()
        if screen is not None:
            return screen.geometry()
        return self._screen_geometry

    def _bottom_y(self) -> float:
        rect = self._screen_rect()
        return (
            rect.y()
            + rect.height()
            - self.height()
            - self.config.window.bottom_offset
        )

    def _position_at_bottom_center(self) -> None:
        rect = self._screen_rect()
        target_width, _ = self.config.window.size
        center_x = rect.x() + (rect.width() - target_width) // 2
        self.x = center_x
        self.y = int(round(self._bottom_y()))
        self.move(self.x, self.y)

    def _apply_state_animation(self, state: str) -> None:
        if self._current_animation_name == state and self.current_animation:
            if self._update_mirror_flag():
                self._set_current_frame_pixmap()
            return

        animation = self.sprites.get(state)
        self.current_animation = animation
        self._current_animation_name = state
        self.current_frame_index = 0
        self._update_mirror_flag()
        self._set_current_frame_pixmap()
        if animation.length > 1:
            self.animation_timer.start(animation.frame_interval_ms)
        else:
            self.animation_timer.stop()

    def _advance_animation(self) -> None:
        if not self.current_animation or self.current_animation.length <= 1:
            self.animation_timer.stop()
            return
        self.current_frame_index = (self.current_frame_index + 1) % self.current_animation.length
        self._set_current_frame_pixmap()

    def _should_mirror_current_animation(self) -> bool:
        # Sprite base mira hacia la derecha; espejar cuando vamos a la izquierda
        return self.vel_x < 0

    def _update_mirror_flag(self) -> bool:
        new_value = self._should_mirror_current_animation()
        changed = new_value != self._mirror_current_animation
        self._mirror_current_animation = new_value
        return changed

    def _set_current_frame_pixmap(self) -> None:
        if not self.current_animation:
            return
        pixmap = self.current_animation.frame(
            self.current_frame_index, mirror=self._mirror_current_animation
        )
        self.setPixmap(pixmap)

    # ------------------------------------------------------------------
    # Movimiento principal
    # ------------------------------------------------------------------

    def move_pet(self) -> None:
        if self._dragging:
            return

        dt_ms = self.config.movement.update_rate_ms
        dt = dt_ms / 1000.0

        self._time_to_next_hop_ms -= dt_ms
        self._time_to_next_walk_ms -= dt_ms
        self._hover_cooldown_ms = max(0, self._hover_cooldown_ms - dt_ms)
        if self._cursor_inside and self._last_hover_pos is not None:
            delay_elapsed = time.monotonic() - self._hover_enter_time >= self._hover_trigger_delay
            self._maybe_trigger_hover_jump(self._last_hover_pos, bypass_delay=delay_elapsed)
        if self._cursor_inside and self._last_hover_pos is not None:
            delay_elapsed = time.monotonic() - self._hover_enter_time >= self._hover_trigger_delay
            self._maybe_trigger_hover_jump(self._last_hover_pos, bypass_delay=delay_elapsed)

        if (
            self._on_ground
            and self._time_to_next_hop_ms <= 0
            and (not self._cursor_inside or self._hover_active)
        ):
            self._trigger_hop(self.config.physics.hop_impulse)

        walk_ready = (
            self._on_ground
            and self._time_to_next_walk_ms <= 0
            and abs(self.vel_x) < 0.3
            and not self._hover_active
        )
        if walk_ready:
            self.vel_x += self._random_horizontal_push()
            self._time_to_next_walk_ms = self._random_walk_interval()

        self._apply_physics(dt)
        self._ground_settle_ms = max(0.0, self._ground_settle_ms - dt_ms)
        self._apply_bobbing(dt)
        self._update_visual_state()

    def _apply_physics(self, dt: float) -> None:
        physics = self.config.physics

        self.vel_y += physics.gravity
        self.vel_x = max(-physics.max_speed_x, min(physics.max_speed_x, self.vel_x))
        self.vel_y = max(-physics.max_speed_y, min(physics.max_speed_y, self.vel_y))

        self.pos_x += self.vel_x
        self.pos_y += self.vel_y

        rect = self._screen_rect()
        min_x = rect.x()
        max_x = rect.x() + rect.width() - self.width()
        if self._hover_active:
            if self._hover_anchor_x is None:
                self._hover_anchor_x = max(min_x, min(max_x, self.pos_x))
            self.pos_x = self._hover_anchor_x
            self.vel_x = 0.0
        elif self.pos_x < min_x:
            self.pos_x = min_x
            self.vel_x = abs(self.vel_x) * physics.bounce_damping
        elif self.pos_x > max_x:
            self.pos_x = max_x
            self.vel_x = -abs(self.vel_x) * physics.bounce_damping

        ground_y = self._bottom_y()
        bounce_threshold = 1.4
        if self.pos_y >= ground_y:
            if self.vel_y > bounce_threshold:
                self.pos_y = ground_y - 0.1
                self.vel_y = -self.vel_y * physics.bounce_damping
                self._on_ground = False
                self._ground_settle_ms = 80.0
            else:
                self.pos_y = ground_y
                if self.vel_y > 0:
                    self.vel_y = 0.0
                if not self._on_ground:
                    self._ground_settle_ms = 200.0
                self._on_ground = True
        else:
            self._on_ground = False

        drag = physics.ground_drag if self._on_ground else physics.air_drag
        self.vel_x *= max(0.0, 1.0 - drag)

        self.x = int(round(self.pos_x))
        self.y = int(round(self.pos_y))
        self.move(self.x, self.y)

    def _apply_bobbing(self, dt: float) -> None:
        if (
            not self._on_ground
            or self.config.movement.bob_amplitude <= 0
            or self._ground_settle_ms > 0
            or abs(self.vel_x) < 0.35
        ):
            return
        self._bob_phase += self.config.movement.bob_speed
        offset = math.sin(self._bob_phase) * self.config.movement.bob_amplitude
        self.pos_y = self._bottom_y() + offset
        self.y = int(round(self.pos_y))
        self.move(self.x, self.y)

    def _update_visual_state(self) -> None:
        if not self._on_ground or abs(self.vel_y) > 0.3:
            desired = "jump"
        elif abs(self.vel_x) > 0.25:
            desired = "walk"
        else:
            desired = "idle"

        if desired != self.state:
            self.state = desired
            visual_state = "idle" if desired in ("idle", "walk") else "jump"
            self._apply_state_animation(visual_state)
        else:
            if self._update_mirror_flag():
                self._set_current_frame_pixmap()

    # ------------------------------------------------------------------
    # Saltos y comportamiento aleatorio
    # ------------------------------------------------------------------

    def _trigger_hop(
        self,
        impulse: float,
        horizontal_bias: float = 0.0,
        allow_random_push: bool = True,
    ) -> None:
        self.vel_y = -abs(impulse)
        if horizontal_bias:
            self.vel_x += horizontal_bias
        if allow_random_push and abs(self.vel_x) < 0.3:
            self.vel_x += self._random_horizontal_push()
        self._on_ground = False
        self._time_to_next_hop_ms = self._random_hop_delay()
        self._time_to_next_walk_ms = self._random_walk_interval()
        self.state = "jump"
        self._apply_state_animation("jump")

    def _maybe_trigger_hover_jump(self, local_pos, *, bypass_delay: bool = False) -> None:
        if (
            not self._on_ground
            or self._hover_cooldown_ms > 0
            or self._dragging
        ):
            return
        if not bypass_delay:
            if time.monotonic() - self._hover_enter_time < self._hover_trigger_delay:
                return
        center = self.width() / 2
        direction = 1 if local_pos.x() < center else -1
        bias = direction * random.uniform(*self.config.movement.walk_speed_range)
        self._hover_active = True
        self._hover_anchor_x = self.pos_x
        self.vel_x = 0.0
        self._trigger_hop(
            self.config.physics.hover_impulse,
            horizontal_bias=0.0,
            allow_random_push=False,
        )
        self._hover_cooldown_ms = self.config.physics.hover_cooldown_ms

    def _random_hop_delay(self) -> float:
        low, high = self.config.physics.hop_interval_ms
        return random.uniform(low, high)

    def _random_walk_interval(self) -> float:
        low, high = self.config.movement.walk_interval_ms
        return random.uniform(low, high)

    def _random_horizontal_push(self) -> float:
        min_speed, max_speed = self.config.movement.walk_speed_range
        magnitude = random.uniform(min_speed, max_speed)
        return random.choice([-1.0, 1.0]) * magnitude

    # ------------------------------------------------------------------
    # Eventos Qt (hover, drag tipo “golf”)
    # ------------------------------------------------------------------

    def enterEvent(self, event: QEnterEvent) -> None:
        self._cursor_inside = True
        self._last_hover_pos = event.position().toPoint()
        self._hover_enter_time = time.monotonic()
        super().enterEvent(event)

    def leaveEvent(self, event: QEnterEvent) -> None:
        self._cursor_inside = False
        self._hover_enter_time = 0.0
        self._last_hover_pos = None
        self._hover_active = False
        self._hover_anchor_x = None
        super().leaveEvent(event)

    def hoverMoveEvent(self, event: QHoverEvent) -> None:
        if self._cursor_inside:
            self._last_hover_pos = event.position().toPoint()
            self._maybe_trigger_hover_jump(self._last_hover_pos)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.pos()
            self._drag_samples.clear()
            self.vel_x = 0.0
            self.vel_y = 0.0
            self._hover_active = False
            self._hover_anchor_x = None
            self.move_timer.stop()
            self.animation_timer.stop()
            self._record_drag_sample(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            global_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(global_pos)
            self.x, self.y = global_pos.x(), global_pos.y()
            self.pos_x, self.pos_y = float(self.x), float(self.y)
            self._record_drag_sample(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._launch_from_drag()
            self.move_timer.start(self.config.movement.update_rate_ms)
            if self.current_animation and self.current_animation.length > 1:
                self.animation_timer.start(self.current_animation.frame_interval_ms)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------
    # Drag helpers
    # ------------------------------------------------------------------

    def _record_drag_sample(self, point: QPoint) -> None:
        self._drag_samples.append((time.monotonic(), QPoint(point)))

    def _launch_from_drag(self) -> None:
        if len(self._drag_samples) < 2:
            self._trigger_hop(self.config.physics.hop_impulse)
            return

        end_time, end_point = self._drag_samples[-1]
        reference_time, reference_point = None, None
        for sample_time, sample_point in reversed(self._drag_samples):
            if end_time - sample_time >= 0.06:
                reference_time = sample_time
                reference_point = sample_point
                break

        if reference_time is None:
            reference_time, reference_point = self._drag_samples[0]

        dt = max(0.001, end_time - reference_time)
        dx = end_point.x() - reference_point.x()
        dy = end_point.y() - reference_point.y()

        multiplier = self.config.physics.launch_multiplier
        self.vel_x = (dx / dt) * multiplier
        self.vel_y = (dy / dt) * multiplier
        if abs(self.vel_x) < 0.2 and abs(self.vel_y) < 0.2:
            self._trigger_hop(self.config.physics.hop_impulse)
            return

        self._on_ground = False
        self.state = "jump"
        self._apply_state_animation("jump")
        self._time_to_next_hop_ms = self._random_hop_delay()
        self._time_to_next_walk_ms = self._random_walk_interval()
