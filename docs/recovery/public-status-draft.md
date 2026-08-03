# Public Status Draft

`0.4.2` is currently under investigation.

We’ve confirmed two real issues:

- a Singles export regression
- a Windows path-length export failure for long mod names/IDs

We are also comparing the packaged `0.4.0` and `0.4.2` Windows releases directly to investigate the Defender false-positive difference.

If that packaging issue does not resolve cleanly and quickly, the fallback path is a recovery build from the last known-good `0.4.0` baseline with the safe export fixes re-applied.

The builder is not abandoned, but the current packaged release is being treated cautiously until that recovery path is settled.
