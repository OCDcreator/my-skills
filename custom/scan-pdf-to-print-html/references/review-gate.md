# Review Gate

Use this default review order for every faithful OCR handout:

1. run generator unit tests
2. rebuild real handout.html
3. run `validate_job_state.py --require-html`
4. export fresh screenshot and PDF
5. check known failure classes
6. if `knowledge-to-print-html` review tooling is available, run its page-review packet generation
7. review page 1 with a fresh reviewer subagent
8. fix page 1 and revalidate before page 2
9. continue sequentially until all pages pass
