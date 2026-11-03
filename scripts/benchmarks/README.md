# Benchmarks

- `run_retrieval_quality_benchmark.py`: frozen retrieval quality evaluation.
- `run_retrieval_benchmark.py`: older live retrieval/backend comparison.
- `benchmark_retrieval_backends.py`: backend performance comparison.
- `benchmark_async_throughput.py`: concurrency measurements.
- `build_retrieval_benchmark_fixtures.py`: fixture construction utility; do not use it
  to rewrite the frozen accepted corpus.
- `build_phase9_reference_benchmark.py`: bounded reference-corpus builder.
- `load_test.py`: explicit HTTP load test, not part of offline correctness acceptance.

Inspect each command's arguments before running it. Use fresh output directories
and preserve existing results. Live tools require explicit scope, permissions and
budgets. See [Testing](../../docs/TESTING.md) and [Evaluation](../../docs/EVALUATION.md).
