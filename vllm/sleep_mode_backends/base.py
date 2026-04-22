"""Sleep-mode backend protocol + built-in cumem dispatcher.

RFC #34303 — draft scaffolding. The protocol is deliberately small: a backend
is anything that can answer `.sleep(engine, level, mode)` and
`.wake_up(engine, tags)`. The current in-tree path is wrapped as
`CuMemBackend` and set as the default, so this file is a no-op for existing
users until they opt in via `--sleep-mode <other>`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SleepModeBackend(Protocol):
    name: str

    def sleep(self, engine, level: int, mode: str) -> None: ...

    def wake_up(self, engine, tags: list[str] | None) -> None: ...


class CuMemBackend:
    """Legacy built-in backend: `CuMemAllocator` tagged release."""

    name = "cumem"

    def sleep(self, engine, level: int, mode: str) -> None:
        engine.sleep(level=level, mode=mode)

    def wake_up(self, engine, tags: list[str] | None) -> None:
        engine.wake_up(tags)


_BUILTIN: dict[str, SleepModeBackend] = {"cumem": CuMemBackend()}


def get_backend(name: str) -> SleepModeBackend:
    """Resolve a sleep-mode backend by name.

    Order:
      1. Built-in table (`cumem`).
      2. `vllm.general_plugins` entrypoint group — third-party backends like
         thaw register a `sleep_mode_backend` callable that returns an
         instance satisfying the `SleepModeBackend` protocol.

    Unknown backends raise `ValueError`; the RFC tiers `cuda-checkpoint` and
    `cuda-checkpoint+criu` are placeholders until their implementations land.
    """
    if name in _BUILTIN:
        return _BUILTIN[name]

    # Scaffold: plug-in discovery. Third-party backends expose a factory
    # through entrypoints; vllm.general_plugins is the existing channel.
    try:
        from importlib.metadata import entry_points

        eps = entry_points(group="vllm.general_plugins")
        for ep in eps:
            if ep.name == f"sleep_mode:{name}":
                factory = ep.load()
                backend = factory()
                if not isinstance(backend, SleepModeBackend):
                    raise TypeError(
                        f"entry point {ep} returned {type(backend).__name__}, "
                        "which does not implement SleepModeBackend"
                    )
                return backend
    except Exception as exc:  # pragma: no cover — scaffold-only
        raise ValueError(
            f"sleep-mode backend {name!r} could not be loaded: {exc}"
        ) from exc

    raise ValueError(
        f"unknown sleep-mode backend {name!r}; expected one of "
        "{'cumem', 'cuda-checkpoint', 'cuda-checkpoint+criu', 'thaw'} "
        "or a third-party backend registered via vllm.general_plugins"
    )
