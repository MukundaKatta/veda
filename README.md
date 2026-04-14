# veda — Open Learning Platform. Open-source learning platform

*वेद — knowledge, the sacred scriptures.*

veda takes its name in that spirit. Open Learning Platform. Open-source learning platform.

## Why veda

veda exists to make this workflow practical. Open learning platform. open-source learning platform. It favours a small, inspectable surface over sprawling configuration.

## Features

- `Difficulty` — exported from `src/veda/core.py`
- `Exercise` — exported from `src/veda/core.py`
- `Lesson` — exported from `src/veda/core.py`
- Included test suite

## Tech Stack

- **Runtime:** Python

## How It Works

The codebase is organised into `src/`, `tests/`. The primary entry points are `src/veda/core.py`, `src/veda/__init__.py`. `src/veda/core.py` exposes `Difficulty`, `Exercise`, `Lesson` — the core types that drive the behaviour.

## Getting Started

```bash
pip install -e .
```

## Usage

```python
from veda.core import Difficulty

instance = Difficulty()
# See the source for the full API
```

## Project Structure

```
veda/
├── CLAUDE.md
├── LICENSE
├── README.md
├── index.html
├── pyproject.toml
├── src/
├── tests/
```
