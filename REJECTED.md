<!-- REJECTED.md -->
# Rejected / Deferred Ideas

A record of design experiments and ideas that were explored but intentionally not pursued.

## 🧮 Incremental Rebuilds via SHA-256 Hashing

**Date:** 2025-10-15  
**Status:** Rejected for now  

### Context
Considered adding file hashing and diffing to skip copying unchanged files during builds.

### Reason for Rejection
- Adds complexity (state tracking, stale cleanup, cache invalidation)
- Negligible performance benefit for typical workloads (dozens of files)
- Opposes the project’s design principle of deterministic, disposable builds

### Revisit If
- Builds exceed ~10k files
- Persistent caches are implemented
