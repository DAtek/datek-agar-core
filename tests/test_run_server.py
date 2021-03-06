from threading import Thread
from time import sleep

from datek_agar_core.run_server import run_server, stop_server
from tests.conftest import PORT, HOST


def test_run(cli_runner):
    Thread(target=stop, args=(0.1, )).start()
    result = cli_runner.invoke(run_server)

    assert result.exit_code == 0


def test_port_already_in_use(test_server, cli_runner):
    result = cli_runner.invoke(run_server, args=f"--host {HOST} --port {PORT}")

    assert result.exit_code == 1
    

def stop(after_seconds: float):
    sleep(after_seconds)
    stop_server()
