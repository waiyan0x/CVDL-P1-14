"""Start the private TorchServe worker and public HTTP gateway in one container."""

import os
import signal
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path
from threading import Event


def run():
    assets = Path(os.environ.get('EDS_TORCHSERVE_DIRECTORY', '/app/torchserve')).resolve()
    port = os.environ.get('PORT', '8080')
    stop = Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    commands = [
        [sys.executable, '-m', 'ts.model_server', '--start', '--foreground', '--ncs',
         '--disable-token-auth', '--ts-config', str(assets / 'config.properties'),
         '--model-store', str(assets / 'model-store'), '--models', 'eds-detector=eds-detector.mar'],
        [sys.executable, '-m', 'uvicorn', 'backend.app.main:app', '--host', '0.0.0.0',
         '--port', port, '--workers', '1'],
    ]

    processes = []
    with tempfile.TemporaryDirectory(prefix='eds-torchserve-') as torchserve_directory:
        try:
            processes.append(subprocess.Popen(commands[0], cwd=torchserve_directory, start_new_session=True))
            processes.append(subprocess.Popen(commands[1], start_new_session=True))
            while not stop.wait(0.25):
                if any(process.poll() is not None for process in processes):
                    return 1
            return 0
        finally:
            for process in reversed(processes):
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGTERM)
            for process in processes:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    with suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


if __name__ == '__main__':
    sys.exit(run())
