# Definition of done: status

| Item | Status | What is left |
|---|---|---|
| Both manuscripts contain real results in every table, no placeholders | **Blocked** | Tables exist but are computed on synthetic data and provisional parameters. Needs real data (Phase 0 go decisions) and calibration from primary sources |
| Every reference verified against the original source | Not started | Manuscript skeletons have no references yet |
| Every institutional or regulatory fact traced to a primary document | Not started | Event calendar entries are all `lead` |
| Repository public, documented and tested, with a tagged release | Partly | Documented and tested (run `make test`). Not a git repository yet, so no tag. Make it public only after the data-terms review |
| Declarations complete (data, code, competing interests, AI use) | Drafted | Authors must complete and confirm; see manuscript skeletons |
| Manuscripts formatted to the target journals' guidelines | Blocked | Target journals not chosen |
| Fixed seeds, one config per experiment, config hash saved with results | Done | |
| `make reproduce` regenerates every table and figure | Done | Takes about 40 minutes |
| Unit tests for the cost engine and compliance filter | Done | |
| Pinned dependencies and a Dockerfile or lock file | Done | `requirements.lock`, `Dockerfile` (written but not yet built or run) |
| Licence and data-terms review | Not started | See `docs/data_terms_review.md` |
