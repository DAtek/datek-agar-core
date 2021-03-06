from asyncio import run, get_event_loop, Future

import click
from datek_agar_core.network.server import UDPServer
from datek_agar_core.utils import create_logger


try:
    import uvloop
except ImportError:
    class Dummy:
        def install(self):
            pass

    uvloop = Dummy()

_logger = create_logger(__name__)
_stop_signal: Future = ...


@click.command()
@click.option("--host", default="0.0.0.0", help="Host")
@click.option("--port", default=9582, help="Port")
@click.option("--size", default=200, help="World size")
@click.option("--livestock", default=90, help="Total livestock in the world")
def run_server(**kwargs):
    uvloop.install()
    _logger.info("Configuration:")
    for key, value in kwargs.items():
        _logger.info(f"{key}: {value}")

    try:
        run(_main(**kwargs))
    except KeyboardInterrupt:
        pass


def stop_server():
    global _stop_signal
    _stop_signal.set_result(1)


async def _main(
    *,
    host: str,
    port: int,
    size: int,
    livestock: int
):
    global _stop_signal
    _stop_signal = Future()
    _logger.info("Starting server")
    loop = get_event_loop()
    loop.shutdown_default_executor = _handle_shutdown
    server = UDPServer(
        host=host,
        port=port,
        world_size=size,
        total_nutrient=livestock
    )

    server.start()
    _logger.info("Server started")

    await server.wait_started()
    await _stop_signal
    server.stop()
    await server.task


async def _handle_shutdown(*args, **kwargs):
    _logger.info("Shutting down")

