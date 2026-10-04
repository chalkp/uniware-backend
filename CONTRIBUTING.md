# Contributing to UniWare Backend

## Workflow
1. Pick or create an issue and assign yourself.
2. Branch from the default branch: `feature/<short-name>`, `fix/<short-name>`, `chore/<short-name>`.
3. Commit in small steps with short imperative messages ("Add equipment filter").
4. Run `make lint` and `make test` before pushing (`make format` auto-fixes style).
5. Open a PR using the template. Keep PRs small (< 500 lines).
6. Get 1 approval, resolve all review comments, wait for CI to go green.
7. **Squash and merge.** The branch is deleted automatically.

## Rules
- Nobody pushes directly to mester, and nobody merges their own PR unreviewed.
- Review within 24 hours.
- If you change a model, commit the migration (`make makemigrations`).
- New env vars go in `.env.example` **and** `docker-compose.yml`.
- **Never commit `.env`**.
- Add tests for new behavior; the suite enforces 85% coverage.
- Agree on API contract changes in an issue before coding, so the frontend isn't surprised.
