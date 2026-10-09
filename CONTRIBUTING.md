# Contributing to HPD-RVE

Thank you for your interest in contributing to HPD-RVE! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/HPD-RVE.git
   cd HPD-RVE
   ```
3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Development Workflow

### Branch Naming
- `feature/<description>` — for new features
- `fix/<description>` — for bug fixes
- `docs/<description>` — for documentation changes
- `refactor/<description>` — for code refactoring

### Code Style
- Follow PEP 8 for Python code
- Use descriptive variable names
- Add docstrings to all public functions and classes (NumPy/Google style preferred)
- Keep functions focused and single-purpose

### Testing
- Add unit tests for new features in `tests/`
- Run tests before submitting a PR:
  ```bash
  pytest tests/
  ```
- Ensure existing tests still pass

### Commit Messages
Use conventional commit format:
```
type(scope): brief description

- feat: new feature
- fix: bug fix
- docs: documentation
- refactor: code restructuring
- test: adding tests
```

## Pull Request Process

1. Update the README.md if your changes affect usage
2. Update the CHANGELOG.md with your changes
3. Ensure all tests pass
4. Submit a PR with a clear description of changes
5. Link any related issues

## Reporting Bugs

When reporting bugs, please include:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Minimal code example if possible
- Error traceback

## Feature Requests

Feature requests are welcome! Please open an issue with:
- Clear description of the feature
- Use case and motivation
- Potential implementation approach (if known)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
