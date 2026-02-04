# Contributing

Thanks for your interest in contributing to CampusConnect AI Service.

## How to Report Bugs

1. Open a GitHub issue.
2. Include:
   - Steps to reproduce
   - Expected vs actual behavior
   - Logs or error output (redact secrets)
   - OS and Python version

## How to Propose Features

1. Open a GitHub issue with:
   - Problem statement
   - Proposed solution
   - Alternatives considered
2. Keep scope small and focused.

## Development Setup

```bash
git clone https://github.com/yourusername/campusconnect-ai.git
cd campusconnect-ai
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Running Tests

```bash
pytest tests/ -v
```

## Code Style

- Follow existing patterns and structure.
- Keep functions small and testable.
- Add tests for new functionality.
- Avoid committing secrets or credentials.

## Pull Request Process

1. Create a branch: `feat/<short-name>` or `fix/<short-name>`
2. Make changes with tests.
3. Ensure all tests pass.
4. Open a PR with a clear summary and test results.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
