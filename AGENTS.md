# Instructions for Codex: Bank operator training simulator

## Project goal
Build a local-first educational CRM simulator and study/exam platform for operator training. The app is NOT a real banking system. Use only synthetic customers, synthetic accounts, and sandbox data.

## Source of truth
- First read `CODEX_TASK.md`, `data/lessons_seed.json`, `data/terms_from_excel.json` and files under `sources/private/`.
- Private PDFs, PowerPoint and XLSX files are original user-provided reference material. Never commit them, paste them into public tickets, or publish them.
- Use material exactly as given. Do NOT fabricate bank limits, tariffs, deadlines, product policies, identity-verification procedures, or numeric values.
- Any item unsupported by the source must be labeled `Нет в лекциях` or designed as clearly fictional demo functionality.
- If two sources conflict or a slide is ambiguous, store `needs_trainer_confirmation=true`; do not choose a policy yourself. Do not auto-generate graded questions from disputed details.
- Preserve terms and product spellings from the files. Store source file and slide/page references for factual material and question answer keys.
- Demo identities and statuses must never resemble live bank credentials or usable financial identifiers. Never store PIN/CVV/code words or real customer data.

## Development standards
- Start with a working MVP before further enhancements.
- Suggested stack: React + TypeScript + Vite frontend, FastAPI backend, SQLite for local development (migration-friendly for PostgreSQL), pytest + Vitest + Playwright.
- Use clean API contracts, validation, seed fixtures, reusable components and accessible responsive UI.
- Avoid copying actual internal bank UI pixel-for-pixel. Build an original educational design in a green/white theme with optional dark mode.
- Every exam has 15 questions per day; show one at a time with scoring, explanations, and difficulty tags. Final exam should include all 4 days. Use only validated source-supported answers.
- Persist progress locally. Show operator progress, weak topics, and history of mistakes.
- Write a README with exact startup commands; add a demo account that needs no real credentials.
- When adding a factual question, include `source_file`, `source_page_or_slide`, `correct_answer`, `explanation`, `review_status`. Reject unpublished question keys without a source.
- Verify frontend/backend tests and start the app to smoke test it.
