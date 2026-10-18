# Charts for the WorkerQueue / worker start failure fixes

Rendered by `make_charts.py` from the raw data in `data/` (micro benchmarks: best of rounds;
end-to-end: 9 interleaved runs per side, 100 hosts x 30 tasks, forks=50, arm64, no emulation).
Semaphore and completion charts use values measured on Alpine 3.24 (musl 1.2.6).
