from __future__ import annotations

from flask import current_app, Flask

import concurrent.futures as cf
import functools as ft
import inspect as ip
import typing as t
import asyncio
import sys

try:
    # Python 3.13+
    gil_enabled: bool = sys._is_gil_enabled()
except AttributeError:
    gil_enabled = True


_THREAD_POOL_GUARD: dict[int, t.Any] = {}

T = t.TypeVar("T")


async def to_thread(
    func: t.Union[t.Callable[..., T], t.Callable[..., t.Awaitable[T]]],
    max_concurrent_threads: int = 10,
    *args,
    **kwargs,
):
    """Run a callable in a worker thread from an async context.

    Executes a sync or async function in a ThreadPoolExecutor while maintaining
    the Flask application context. Concurrency is limited by a shared semaphore
    per event loop to prevent thread pool exhaustion.

    Args:
        func: A sync callable (e.g., `def task()`) or async callable (e.g., `async def task()`).
              Both will be executed in a worker thread.
        max_concurrent_threads: Maximum number of concurrent threads for this
                               event loop. Defaults to 10.
        *args: Positional arguments passed to `func`.
        **kwargs: Keyword arguments passed to `func`.

    Returns:
        The return value of `func(*args, **kwargs)`.

    Raises:
        asyncio.TimeoutError: If the timeout context manager is exceeded.
        Exception: Any exception raised by `func` is propagated to the caller.

    Example (sync function):
        ```python
        import asyncio
        from flask_nova2 import to_thread

        def heavy_computation(n: int) -> int:
            # Simulate CPU-bound work
            total = sum(range(n))
            return total

        async def main():
            # Run sync function in thread, keeping Flask context alive
            result = await to_thread(heavy_computation, 1_000_000)
            print(f"Result: {result}")

        asyncio.run(main())
        ```

    Example (async function):
        ```python
        import asyncio
        from flask_nova2 import to_thread

        async def async_task(delay: float) -> str:
            await asyncio.sleep(delay)
            return f"Completed after {delay}s"

        async def main():
            result = await to_thread(async_task, max_concurrent_threads=5, 2.0)
            print(result)

        asyncio.run(main())
        ```

    Example (with timeout):
        ```python
        import asyncio
        from flask_nova2 import to_thread

        async def main():
            try:
                result = await asyncio.wait_for(
                    to_thread(long_running_task),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                print("Task exceeded 30 seconds")

        asyncio.run(main())
        ```

    Note:
        The semaphore is keyed by event loop ID, so each event loop maintains
        its own concurrency limit. This prevents deadlocks in multi-loop scenarios.
    """
    key = id(asyncio.get_event_loop())
    if key not in _THREAD_POOL_GUARD:
        _THREAD_POOL_GUARD[key] = asyncio.Semaphore(max_concurrent_threads)
    app = current_app

    guard = _THREAD_POOL_GUARD[key]

    async def runner():
        with app.app_context():
            if not ip.iscoroutinefunction(func):
                return func(*args, **kwargs)
            return asyncio.run(func(*args, **kwargs))

    async with guard:
        return asyncio.to_thread(runner)


async def to_process(
    app_factory: Flask,
    func: t.Callable[..., T],
    max_workers: int = 10,
    *args,
    **kwargs,
) -> T:
    """Execute a sync callable in a worker process or thread pool.

    Runs CPU-intensive or I/O-bound code in a separate pool while maintaining
    the Flask application context. On Python 3.13+ with the GIL disabled, uses
    ThreadPoolExecutor; otherwise uses ProcessPoolExecutor.

    Args:
        app_factory: Flask application instance used to create app context
                    in the worker process/thread.
        func: A sync callable to execute. Async functions will raise TypeError.
        max_workers: Maximum workers in the pool. Defaults to 10.
        *args: Positional arguments passed to `func`.
        **kwargs: Keyword arguments passed to `func`.

    Returns:
        The return value of `func(*args, **kwargs)`.

    Raises:
        TypeError: If `func` is async (use :meth:`to_thread` for async functions).
        Exception: Any exception raised by `func` is propagated to the caller.

    Example (CPU-bound task):
        ```python
        import asyncio
        from flask_nova2 import FlaskNova to_process

        app = FlaskNova()

        def cpu_intensive(n: int) -> int:
            # Simulate heavy computation
            return sum(x ** 2 for x in range(n))

        async def route_handler():
            # Offload to process pool, preserving Flask context
            result = await to_process(app, cpu_intensive, 100_000)
            return {"result": result}

        asyncio.run(route_handler())
        ```

    Example (with multiple workers):
        ```python
        import asyncio
        from flask_nova2 import to_process

        app = FlaskNova()

        def fetch_data(url: str) -> dict:
            import requests
            return requests.get(url).json()

        async def get_multiple_apis():
            urls = ["https://api1.com", "https://api2.com"]
            # Run up to 4 requests in parallel
            tasks = [
                to_process(app, fetch_data, max_workers=4, url)
                for url in urls
            ]
            results = await asyncio.gather(*tasks)
            return results

        asyncio.run(get_multiple_apis())
        ```

    Example (GIL-aware behavior):
        ```python
        # On Python 3.13+ with GIL disabled: ThreadPoolExecutor (fast context sharing)
        # On Python 3.12 or earlier: ProcessPoolExecutor (separate interpreter, slower)
        result = await to_process(app, func)
        ```

    Warning:
        - `func` must be picklable if using ProcessPoolExecutor (Python < 3.13 or GIL enabled).
        - Do not rely on module-level state; it may not be shared with workers.
        - For I/O-bound work, prefer `to_thread()` or native async I/O.
    """
    if sys.version_info >= (3.13) and not gil_enabled:  # type: ignore

        _pool = cf.ThreadPoolExecutor(
            max_workers=max_workers,
        )
    else:
        _pool = cf.ProcessPoolExecutor(max_workers=max_workers)  # type: ignore[assignment]

    async def runner() -> T:
        with app_factory.app_context():
            loop = asyncio.get_running_loop()
            wrapped_func = ft.partial(func, *args, **kwargs)
            result = await loop.run_in_executor(_pool, wrapped_func)
            return result

    return await runner()
