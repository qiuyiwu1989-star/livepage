# LivePage contributor contract

This repository is the independent public codebase for 活页 LivePage.

- Never commit real slides, audio, transcripts, annotations, customer materials, runtime logs, credentials or signed URLs. Use explicitly synthetic fixtures.
- Preserve canonical identities, immutable source versions and append-only session records.
- Separate speaker quotes, AI interpretations and human confirmation. Model output is pending by default.
- Do not treat generated archive pages as editable slide conversions.
- Integrate existing capabilities by module; do not import a personal-site checkout or its history.
- Keep core content readable without disclosure controls; follow task-based navigation.
- No production deployment is implied by a source commit.
- Run PYTHONPATH=src python3 -m unittest discover -s tests for domain changes.
