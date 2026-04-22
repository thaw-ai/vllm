# Sleep-mode backends (RFC #34303 — draft)

> Status: **scaffold / draft PR**. This directory is the plug-in point that
> RFC [#34303](https://github.com/vllm-project/vllm/issues/34303) discusses.
> It does *not* change default behavior — the built-in `cumem` backend
> wraps today's `engine.sleep()` / `engine.wake_up()` paths 1:1.

## What this lands

- A `SleepModeBackend` protocol (`sleep`, `wake_up`).
- A `get_backend(name)` resolver that:
  1. Returns the built-in `CuMemBackend` for `"cumem"` (default — no change).
  2. Looks up `vllm.general_plugins` entrypoints with name
     `sleep_mode:<name>` for third-party backends.
- A `ModelConfig.sleep_mode_backend: Literal["cumem", "cuda-checkpoint",
  "cuda-checkpoint+criu", "thaw"]` field, surfaced as `--sleep-mode`.
- `LLM.sleep()` / `LLM.wake_up()` dispatch through `get_backend()` instead of
  hard-coding `engine.sleep()` / `engine.wake_up()`.

## Why this shape

The RFC's core question is "one backend or several?" — the cumem,
cuda-checkpoint, and CRIU tiers make different tradeoffs on first-token
latency vs. cold-start ceiling vs. host-RAM pressure vs. quantized-model
correctness. Rather than picking one, this scaffold lets users select per
deployment, and lets third-party backends (like
[thaw-ai/thaw](https://github.com/thaw-ai/thaw)) register through the
existing `vllm.general_plugins` hook. Zero core-vLLM coupling, zero default
behavior change.

## `thaw` backend registration (illustrative)

A third-party package registers its backend in `pyproject.toml`:

```toml
[project.entry-points."vllm.general_plugins"]
"sleep_mode:thaw" = "thaw_vllm.sleep_mode_backend:make_backend"
```

`make_backend()` returns an object that implements the `SleepModeBackend`
protocol. For thaw specifically, the implementation is
[`thaw_vllm.sleep_mode`](https://github.com/thaw-ai/thaw/blob/main/python/thaw_vllm/sleep_mode.py)
— it composes `freeze_model_tp` / `restore_model_tp` around `engine.sleep()`
and `engine.wake_up()` so `CuMemAllocator` still releases GPU memory, but
the durable snapshot is a thaw file (16 GB / 141 GB receipts on H100 +
2× H100 SXM, bit-identical greedy output).

## Not in this scaffold

- `cuda-checkpoint` / `cuda-checkpoint+criu` backend implementations. The
  resolver raises `ValueError` for those names today; they unblock as the
  RFC's Tier 1/Tier 2 implementations land.
- Config flag wiring to `EngineArgs` + `llm_engine.py`. The field is on
  `ModelConfig`; surfacing `--sleep-mode` in the CLI is a follow-up and
  deliberately small.
- Tests. `LLM.sleep()`/`wake_up()` are unchanged for `cumem`, which is the
  default — no behavioral drift for any existing deployment.

## Reference

- RFC issue: https://github.com/vllm-project/vllm/issues/34303
- thaw receipts: https://github.com/thaw-ai/thaw/tree/main/site/receipts/2026-04-22_rfc
- thaw implementation: https://github.com/thaw-ai/thaw/blob/main/python/thaw_vllm/sleep_mode.py
