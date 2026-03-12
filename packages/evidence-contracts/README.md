# Evidence Contracts

This package contains Ralph Loop trust-plane contracts.

Source artifacts:
- `stage_result`
- `bundle_manifest`
- `evidence_summary`

Common rules:
- every artifact carries common metadata,
- stage scoring uses `computed_score`,
- user runtime consumes only `evidence_summary`,
- raw stage artifacts stay outside user-facing APIs.
