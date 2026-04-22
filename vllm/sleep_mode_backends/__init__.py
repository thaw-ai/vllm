# Sleep-mode backends (RFC #34303).
#
# vLLM's existing sleep-mode path uses CuMemAllocator to release tagged
# allocations. RFC #34303 proposes alternative backends:
#
#   - cuda-checkpoint         : cuCheckpointProcess* for CUDA-context capture
#   - cuda-checkpoint+criu    : combine with CRIU for full-process capture
#   - thaw                    : serialize weights + KV + scheduler to disk/S3
#
# This package exposes `get_backend(name)` which returns a backend object with
# `.sleep(engine, level, mode)` and `.wake_up(engine, tags)` methods. The
# default "cumem" backend is the identity dispatcher — it calls the legacy
# `engine.sleep()` / `engine.wake_up()` paths unchanged, so existing
# deployments keep working with no config change.
#
# The "thaw" backend is discovered through the `vllm.general_plugins`
# entrypoint system (thaw-ai/thaw registers as `load_format="thaw"` today;
# sleep_mode registration uses the same hook).

from vllm.sleep_mode_backends.base import SleepModeBackend, get_backend

__all__ = ["SleepModeBackend", "get_backend"]
