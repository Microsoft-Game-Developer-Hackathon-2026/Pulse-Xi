"""Bounded local HTTP serving without Windows Proactor shutdown races.

Uvicorn 0.40 accepts an explicit loop factory. No asyncio subprocess operations
are used by this local server. Linux retains Uvicorn's normal auto/uvloop path.
"""
import asyncio
import sys


def create_loop() -> asyncio.AbstractEventLoop:
    if sys.platform == 'win32':
        return asyncio.SelectorEventLoop()
    from uvicorn.loops.auto import auto_loop_factory
    return auto_loop_factory()()
