# On Demand Proxy
Last stable version [available here](https://git.pofilo.fr/pofilo/on-demand-proxy/tags).

Proxy to start your service on demand.

## Requirements

+ The script uses **python 3.14.3**
+ Dependencies listed in `pyproject.toml`

## Installation

### Manual with a virtual environment

+ Download the last stable version [available here](https://git.pofilo.fr/pofilo/on-demand-proxy/tags)
+ `cd on-demand-proxy`
+ Create virtual environment: `python3.14.3 -m venv venv`
+ Source it: `source venv/bin/activate`
+ Install `uv`: `pip install uv`
+ Install dependencies: `uv pip install .`

## Development

Install "pre-commit" hook: `ln -s $(pwd)/hook-pre-commit .git/hooks/pre-commit`.
Linters and typos will be checked before committing.

### Linters

+ Install dependencies: `pip install .[linters]`
+ Run linters:

```bash
ruff format --diff
ruff check
```

### Typos

+ Install [typos](https://github.com/crate-ci/typos)
+ Run it: `typos`

## License

This project is licensed under the GNU GPL License. See the [LICENSE](https://git.pofilo.fr/pofilo/on-demand-proxy/src/branch/master/LICENSE) file for the full license text.

## Bugs

If you experience an issue, have other ideas for the development, or anything else, feel free to [report it](https://git.pofilo.fr/pofilo/on-demand-proxy/issues) or [fix it with a PR](https://git.pofilo.fr/pofilo/on-demand-proxy/pulls)!
