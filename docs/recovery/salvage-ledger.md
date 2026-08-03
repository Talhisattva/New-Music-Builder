# Recovery Salvage Ledger

Date: August 3, 2026

## Safe To Reapply

- singles flat-contract fix
- short workshop-local staging path
- Windows path-length preflight guard
- low-risk export correctness fixes that do not change packaged runtime layout
- duplicate sound-definition dedupe for flat singles output

## Needs Re-Validation

- fast-path export throughput changes
- live preview/log churn changes during export
- mixed singles/mixtape export behavior beyond the core correctness path
- any release-folder pruning change that affects packaged binary layout

## Do Not Reapply Yet

- AppData runtime-state relocation
- AppData export staging relocation
- packaging/runtime layout changes without a measured reason
- any change whose only justification is “cleaner packaging” if it also changes the EXE/package shape
