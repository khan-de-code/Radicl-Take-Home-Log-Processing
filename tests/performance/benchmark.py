"""Performance and latency benchmarking script for Log Normalizer."""

import asyncio
import contextlib
import json
import logging
import socket
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from adapters.inbound.tcp_server import LogNormalizerTCPServer
from domain.models import NormalizedLog
from domain.parser import parse_line

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")
console = Console()


async def dummy_on_error(line: str, error: Exception) -> None:
    """Ignore errors during benchmarking."""


def get_free_port() -> int:
    """Find a free TCP port to bind."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def run_tcp_benchmark(
    host: str,
    port: int,
    num_events: int,
    concurrency: int,
    payloads: list[str],
) -> tuple[float, list[float]]:
    """Run TCP server benchmark and return total duration and per-event latencies."""
    latencies: list[float] = []
    received_count = 0
    done_event = asyncio.Event()

    async def measured_sink(_log: NormalizedLog) -> None:
        nonlocal received_count
        received_count += 1
        if received_count >= num_events:
            done_event.set()

    server = LogNormalizerTCPServer(
        host=host,
        port=port,
        parser=parse_line,
        sink=measured_sink,
        on_error=dummy_on_error,
        max_connections=concurrency + 10,
        idle_timeout=10.0,
    )

    # Hook _process_line to measure processing latency per log
    original_process_line = server._process_line

    async def hooked_process_line(line: str) -> None:
        start = time.perf_counter()
        await original_process_line(line)
        end = time.perf_counter()
        latencies.append((end - start) * 1000.0)  # Convert to ms

    server._process_line = hooked_process_line

    await server.start()

    # TCP Client task sending a share of payloads
    async def send_logs_client(lines: list[str]) -> None:
        _reader, writer = await asyncio.open_connection(host, port)
        try:
            for line in lines:
                writer.write(line.encode("utf-8") + b"\n")
                await writer.drain()
        finally:
            writer.close()
            with contextlib.suppress(ConnectionError, OSError):
                await writer.wait_closed()

    # Prepare workloads
    client_tasks = []
    lines_per_client = num_events // concurrency
    for i in range(concurrency):
        client_payloads = [
            payloads[(i * lines_per_client + j) % len(payloads)] for j in range(lines_per_client)
        ]
        client_tasks.append(send_logs_client(client_payloads))

    start_time = time.perf_counter()
    await asyncio.gather(*client_tasks)

    try:
        await asyncio.wait_for(done_event.wait(), timeout=15.0)
    except TimeoutError:
        logger.warning("Timeout waiting for all events to be processed by server.")

    duration = time.perf_counter() - start_time
    await server.stop()

    return duration, latencies


def main() -> None:
    """Load sample logs, run benchmarks, and report results."""
    project_root = Path(__file__).parent.parent.parent

    # Load payloads
    payloads: list[str] = []

    # Load syslog samples
    syslog_dir = project_root / "samples" / "syslog"
    for path in syslog_dir.glob("*.log"):
        with path.open("r", encoding="utf-8") as f:
            payloads.extend([line.strip() for line in f if line.strip()])

    # Load JSON samples (minify them)
    json_dir = project_root / "samples" / "json"
    for path in json_dir.glob("*.json"):
        with path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                payloads.append(json.dumps(data))
            except json.JSONDecodeError:
                f.seek(0)
                payloads.extend([line.strip() for line in f if line.strip()])

    if not payloads:
        console.print("[bold red]Error: No sample payloads found.[/bold red]")
        return

    console.print(f"[green]Loaded {len(payloads)} sample payloads for benchmarking.[/green]")

    # Parameters
    num_events = 10000
    concurrency = 10
    host = "127.0.0.1"
    port = get_free_port()

    console.print(
        f"[bold blue]Starting TCP Normalizer Benchmark:[/bold blue] "
        f"[cyan]{num_events}[/cyan] events, [cyan]{concurrency}[/cyan] clients..."
    )

    duration, latencies = asyncio.run(
        run_tcp_benchmark(host, port, num_events, concurrency, payloads)
    )

    actual_processed = len(latencies)
    throughput = actual_processed / duration if duration > 0 else 0

    table = Table(title="Benchmark Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim", width=25)
    table.add_column("Value", justify="right")

    table.add_row("Total Processed Events", f"{actual_processed}")
    table.add_row("Total Time Elapsed", f"{duration:.4f} s")
    table.add_row("Throughput", f"[bold green]{throughput:.2f} events/s[/bold green]")

    if latencies:
        latencies.sort()
        avg_lat = sum(latencies) / len(latencies)
        p95_lat = latencies[int(len(latencies) * 0.95)]
        p99_lat = latencies[int(len(latencies) * 0.99)]
        max_lat = latencies[-1]
        min_lat = latencies[0]

        table.add_row("Latency Min", f"{min_lat:.4f} ms")
        table.add_row("Latency Average", f"{avg_lat:.4f} ms")
        table.add_row("Latency 95th %ile", f"[yellow]{p95_lat:.4f} ms[/yellow]")
        table.add_row("Latency 99th %ile", f"[red]{p99_lat:.4f} ms[/red]")
        table.add_row("Latency Max", f"{max_lat:.4f} ms")
    else:
        table.add_row("Latency", "[red]No latency samples collected.[/red]")

    console.print(table)


if __name__ == "__main__":
    main()
