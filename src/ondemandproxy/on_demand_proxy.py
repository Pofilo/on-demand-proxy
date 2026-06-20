"""
on-demand-proxy: Proxy to start your service on demand.
Copyright (C) pofilo <git@pofilo.fr>.

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import asyncio
import logging
import os
import subprocess
import time
from pathlib import Path

import docker
import yaml
from aiohttp import ClientSession, ClientTimeout, web

CONFIG_PATH = os.environ.get("CONFIG_PATH", "/app/config.yml")
DEFAULT_RETRY_AFTER = 3


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """
    Load and parse the YAML configuration file.
    """
    with Path.open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


class OnDemandProxy:
    """Reverse proxy that starts/stops a Docker Compose service on demand."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.config = load_config()

        self.name: str = None
        self.docker_compose_dir: str = None
        self.docker_compose_filename: str = None
        self.container_name: str = None
        self.target_url: str = None
        self.idle_timeout: int = 0
        self.last_request_time: float = 0
        self.starting: bool = False
        self._lock = asyncio.Lock()
        self.docker_client: docker.DockerClient | None = None
        self.loading_html: str = None
        self._idle_task: asyncio.Task | None = None
        self.app = web.Application()
        self.app.on_startup.append(self._on_startup)
        self.app.on_shutdown.append(self._on_shutdown)
        self.app.router.add_route("*", "/{path:.*}", self._proxy_handler)

    def is_container_running(self) -> bool:
        """
        Check if the Docker container is currently running.
        """
        try:
            container = self.docker_client.containers.get(self.container_name)
        except docker.errors.NotFound:
            return False
        except Exception:
            self.logger.exception(
                "Error while checking container %s", self.container_name
            )
            return False
        else:
            return container.status == "running"

    def start_service(self) -> None:
        """
        Start the Docker Compose service.
        """
        self.logger.info("Starting service '%s'", self.name)
        subprocess.run(  # noqa: S603 (subprocess-without-shell-equals-true)
            [
                "/usr/bin/docker",
                "compose",
                "-f",
                self.docker_compose_filename,
                "up",
                "-d",
            ],
            cwd=self.docker_compose_dir,
            check=True,
        )

    def stop_service(self) -> None:
        """
        Stop the Docker Compose service.
        """
        self.logger.info("Stopping service '%s'", self.name)
        subprocess.run(  # noqa: S603 (subprocess-without-shell-equals-true)
            ["/usr/bin/docker", "compose", "-f", self.docker_compose_filename, "down"],
            cwd=self.docker_compose_dir,
            check=True,
        )

    def check_health(self) -> bool:
        """
        Check if the service is healthy and ready to receive traffic.
        """
        try:
            container = self.docker_client.containers.get(self.container_name)
            health = container.attrs.get("State", {}).get("Health", {})
            return health.get("Status") == "healthy"
        except Exception:  # noqa: BLE001 (blind-except)
            return False

    async def _idle_checker(self) -> None:
        """
        Background task that stops the service after idle timeout.
        """
        while True:
            await asyncio.sleep(60)
            idle_duration = time.time() - self.last_request_time
            if idle_duration > self.idle_timeout and self.is_container_running():
                self.logger.info(
                    "Service '%s' idle for %ds (timeout: %ds). Stopping...",
                    self.name,
                    int(idle_duration),
                    self.idle_timeout,
                )
                try:
                    self.stop_service()
                except Exception:
                    self.logger.exception("Failed to stop '%s'", self.name)

    async def _on_startup(self, _app: web.Application) -> None:
        """
        Start idle checker on application startup.
        """
        try:
            service_config = self.config["service"]

            self.name = service_config["name"]
            docker_compose_file = Path(service_config["docker_compose_file"])
            self.docker_compose_dir = str(docker_compose_file.parent)
            self.docker_compose_filename = docker_compose_file.name
            self.container_name = service_config["container_name"]
            self.target_url = service_config["target_url"]
            self.idle_timeout = int(service_config["idle_timeout"])
            self.retry_after = service_config.get("retry_after", DEFAULT_RETRY_AFTER)
        except ValueError:
            self.logger.exception("Missing mandatory value in conf")
            raise

        self.docker_client = docker.DockerClient.from_env()

        template_path = Path(__file__).parent / "templates" / "loading.html"
        self.loading_html = template_path.read_text()
        self.loading_html = self.loading_html.replace("{{SERVICE_NAME}}", self.name)
        self.loading_html = self.loading_html.replace(
            "{{RETRY_AFTER}}", str(self.retry_after)
        )

        self._idle_task = asyncio.create_task(self._idle_checker())
        self.logger.info("On-demand proxy started for service '%s'", self.name)

    async def _on_shutdown(self, _app: web.Application) -> None:
        """
        Cancel idle checker and close Docker client on shutdown.
        """
        if self._idle_task:
            self._idle_task.cancel()
        if self.docker_client:
            self.docker_client.close()
        if self.check_health():
            self.stop_service()

    def _get_loading_response(self) -> web.Response:
        """
        Return an HTML loading page response.
        """
        return web.Response(
            text=self.loading_html,
            status=503,
            content_type="text/html",
            headers={"Retry-After": str(self.retry_after)},
        )

    async def _proxy_handler(self, request: web.Request) -> web.Response:
        """
        Handle all incoming requests: start service if needed, proxy when ready.
        """
        self.last_request_time = time.time()

        if not self.is_container_running():
            async with self._lock:
                # Check again after acquiring the lock (to reduce race condition)
                if not self.is_container_running() and not self.starting:
                    self.starting = True
                    try:
                        await asyncio.get_event_loop().run_in_executor(
                            None, self.start_service
                        )
                    except Exception:
                        self.starting = False
                        self.logger.exception("Failed to start '%s'", self.name)
                        return web.Response(
                            text=f"Failed to start {self.name}",
                            status=503,
                        )

            self.logger.info(
                "Service '%s' is starting, showing loading page (%s %s)",
                self.name,
                request.method,
                request.path,
            )
            return self._get_loading_response()

        is_healthy = await asyncio.get_event_loop().run_in_executor(
            None, self.check_health
        )

        if not is_healthy:
            self.logger.info(
                "Service '%s' not ready yet, showing loading page (%s %s)",
                self.name,
                request.method,
                request.path,
            )
            return self._get_loading_response()

        self.starting = False

        # Proxy the request
        path = request.match_info["path"]
        target_url = f"{self.target_url}/{path}"
        if request.query_string:
            target_url += f"?{request.query_string}"

        non_forwardable_headers = {
            "accept-encoding",
            "connection",
            "keep-alive",
            "transfer-encoding",
            "upgrade",
            "host",
        }
        headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in non_forwardable_headers
        }

        body = await request.read()

        async with ClientSession(
            timeout=ClientTimeout(sock_read=300, sock_connect=10)
        ) as session:
            try:
                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    data=body,
                    allow_redirects=False,
                ) as resp:
                    resp_body = await resp.read()
                    excluded_headers = non_forwardable_headers | {
                        "content-encoding",
                        "content-length",
                    }
                    resp_headers = {
                        k: v
                        for k, v in resp.headers.items()
                        if k.lower() not in excluded_headers
                    }
                    return web.Response(
                        body=resp_body,
                        status=resp.status,
                        headers=resp_headers,
                    )
            except Exception:  # noqa: BLE001 (blind-except)
                return self._get_loading_response()


def run() -> None:
    """
    Entry point for the application.
    """
    on_demand_proxy = OnDemandProxy(logger)
    proxy_config = on_demand_proxy.config.get("proxy", {})
    host = proxy_config.get("host", "127.0.0.1")
    port = proxy_config.get("port", 8080)
    web.run_app(on_demand_proxy.app, host=host, port=port, access_log=logger)
