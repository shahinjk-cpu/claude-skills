---
name: qwenputer
description: Compiled 32-bit RISC-V CPU inside Qwen3.5-4B neural weights. Executes exact deterministic C and MicroPython code inside forward passes without external tool sandboxes, using Gated DeltaNet state as RAM.
metadata:
  version: 1.0.0
---

# Qwenputer: CPU Compiled into LLM Weights

`Qwenputer` is a computer compiled directly into the weights of a language model (`Qwen3.5-4B`). Unlike traditional agents that call external Python sandboxes or bash interpreters, Qwenputer embeds an exact 32-bit RISC-V CPU directly across 11 transformer layers in front of Qwen's layers, with mathematically calculated (unlearned) weights.

Local repository: `C:\Users\sahin\.gemini\antigravity\scratch\repos\qwenputer`

## Architecture Highlights

1. **Gated DeltaNet State as RAM**:
   - Qwen3.5's DeltaNet layers carry a running state that the delta rule overwrites row-by-row with mathematical precision.
   - Each state row functions as a memory cell holding code, data, registers, and program counter.
2. **Deterministic Computation**:
   - Passes the official `riscv-tests` architectural test suite inside the forward pass.
   - Solves arithmetic, cryptographic, and algorithmic tasks without hallucination or numerical drift.
3. **QwenPU & Vector Execution**:
   - Includes vector unit extensions for parallel operations.
   - Supports compilation of C and MicroPython targets via `chipformer`.

## Execution & Usage

```bash
cd C:\Users\sahin\.gemini\antigravity\scratch\repos\qwenputer
# Run tests
pytest tests/
# Compile and run RISC-V assembly inside the model
python -m chipformer.cli run --target riscv32 "int main() { return 42 * 1337; }"
```
