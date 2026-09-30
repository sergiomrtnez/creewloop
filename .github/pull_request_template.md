## Description
<!-- Provide a concise summary of the changes and the technical rationale. -->

## Type of Change
<!-- Mark the relevant option with an 'x'. -->
- [ ] `feat`: A new feature
- [ ] `fix`: A bug fix
- [ ] `refactor`: Code refactoring without behavioral changes
- [ ] `test`: Adding or modifying automated tests
- [ ] `docs`: Documentation updates
- [ ] `style`: Formatting or style adjustments
- [ ] `perf`: Performance improvements
- [ ] `build`: Build system or dependency updates
- [ ] `ci`: CI/CD workflow configuration
- [ ] `chore`: Repository maintenance or tooling

## Conventional Commit Check
- [ ] Commit message follows Conventional Commits format: `<type>(<scope>): <imperative summary>`

## Testing & Verification
<!-- Describe tests run to verify these changes. -->
- [ ] Executed `python test_decision_flow.py` successfully
- [ ] Verified Textual TUI mounting and interaction (`python test_ui_interactive.py`)
- [ ] Verified linting and syntax compilation

## Security & Secrets Check
- [ ] No API keys, credentials, or sensitive secrets (.env) committed
- [ ] Generated artifacts in `output/` adhere to `.gitignore`
