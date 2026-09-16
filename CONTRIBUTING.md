# Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant Microsoft the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide a CLA and decorate the pull request appropriately. Follow the instructions provided by the bot. You only need to do this once across all repositories using Microsoft's CLA process.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with questions or concerns.

## Before You Start

- Search existing issues before opening a new one.
- Open an issue before starting large changes so the scope and direction can be discussed.
- Keep changes focused and include tests when behavior changes.

## Development Setup

1. Create and activate a virtual environment.
2. Install tox and the development dependencies.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS
python -m pip install -e .[dev] tox
```

### Using `uv.lock`

The committed `uv.lock` is generated through Microsoft's package proxy rather than directly from the Python Package Index (PyPI). Microsoft contributors are required to use this proxy so packages are subject to Microsoft's security and vulnerability policies. Consequently, the lockfile records Microsoft registry and artifact URLs that might not be accessible outside Microsoft.

Contributors who cannot access the Microsoft proxy should regenerate the lockfile using an accessible package index. For example, to use official PyPI:

```bash
uv lock --refresh --default-index https://pypi.org/simple
```

Regenerate rather than manually replacing only the registry value: `uv.lock` also contains index-specific source distribution and wheel URLs. The newly generated lockfile can be used locally with `uv sync`.

## Running Checks with Tox

Run all environments at once or pick individual ones.

```bash
# Run everything (pylint, mypy, black, tests on Python 3.10-3.14)
tox

# Run a single check
tox -e pylint       # Lint with pylint
tox -e mypy         # Type-check with mypy
tox -e black        # Format with black

# Run tests on a specific Python version
tox -e pytest-py312

# Run tests on multiple Python versions
tox -e pytest-py310,pytest-py311,pytest-py312,pytest-py313,pytest-py314

# Pass extra arguments to pytest
tox -e pytest-py312 -- -k test_name -v
```

## Pull Requests

- Describe the problem and the approach clearly.
- Link related issues when applicable.
- Update documentation when public behavior or setup changes.
- Keep the repository planning and README documents aligned with the implementation.