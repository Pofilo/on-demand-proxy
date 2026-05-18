# On Demand Proxy
Last stable version [available here](https://git.pofilo.fr/pofilo/on-demand-proxy/tags).

Proxy to start your service on demand.

## Requirements

+ The script uses **python 3.14.3**
+ Dependencies listed in `pyproject.toml`

## Installation

### Docker

Build the image with something like: `docker build -t on-demand-proxy:latest .`
Then, check the example for Stirling PDF in the example folder.

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

### Linters

+ Install dependencies: `pip install .[linters]`
+ Run linters:

```bash
ruff format --diff
ruff check
```

### Typos

+ Install [typos](https://github.com/crate-ci/typos)
+ Run it: `typos`


## Notes

Please note that using `/var/run/docker.sock:/var/run/docker.sock:ro` (in the `docker-compose.yml` example) is subject to errors in case of change done on the file (upgrade for examples).
It could lead to errors like `Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?`.

A solution is to replace this line by `/var/run/:/var/run/:ro` but there is much more unnecessary files shared to the docker container.
Another possibility is to restart the container each time the socket is changed.

## License

This project is licensed under the GNU GPL License. See the [LICENSE](https://git.pofilo.fr/pofilo/on-demand-proxy/src/branch/master/LICENSE) file for the full license text.

## Bugs

If you experience an issue, have other ideas for the development, or anything else, feel free to [report it](https://git.pofilo.fr/pofilo/on-demand-proxy/issues) or [fix it with a PR](https://git.pofilo.fr/pofilo/on-demand-proxy/pulls)!
