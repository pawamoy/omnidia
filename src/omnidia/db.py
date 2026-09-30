# SPDX-License-Identifier: ISC
#
# ISC License
#
# Copyright (c) 2021, Timothée Mazzucotelli and contributors
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Database clients for Neo4j."""

from __future__ import annotations

import asyncio
import time
import traceback
from base64 import b64encode
from concurrent import futures
from typing import TYPE_CHECKING, Any

import httpx
from loguru import logger
from neo4j import READ_ACCESS, GraphDatabase, Record, Session
from neo4j.exceptions import ServiceUnavailable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator, Mapping

RETRY_WAITS = [0, 1, 4]
"""Seconds to wait between connection attempts."""

MAX_WORKERS = 30
"""Maximum number of threads used for Bolt database calls."""


class Neo4jBolt:
    """Neo4j database API."""

    def __init__(self, user: str, password: str, url: str, loop: asyncio.AbstractEventLoop) -> None:
        """Connect to Neo4j and prepare the thread pool for database calls."""
        self.loop = loop
        """Event loop used to schedule database calls."""

        self.executor = futures.ThreadPoolExecutor(max_workers=MAX_WORKERS)
        """Thread pool used for blocking Bolt calls."""

        for retry_wait in RETRY_WAITS:
            try:
                self.driver = GraphDatabase.driver(url, auth=(user, password))
                """Bolt driver used to create database sessions."""
            except Exception:  # noqa: PERF203
                if retry_wait == RETRY_WAITS[-1]:
                    raise
                # print("WARNING: retrying to Init DB; error:")
                traceback.print_exc()
                time.sleep(retry_wait)
            else:
                break

    async def fetch_start(self, query: str) -> tuple[Session, Iterator[Record]]:
        """Run a read query and return its session and record iterator."""
        session = self.driver.session(access_mode=READ_ACCESS)
        iterator = await self.loop.run_in_executor(self.executor, lambda: session.run(query).records())
        return session, iterator

    async def fetch_iterate(self, iterator: Iterator[Record]) -> AsyncIterator[dict[str, Any]]:
        """Read records from the iterator without blocking the event loop."""
        while True:
            try:
                res = await self.loop.run_in_executor(self.executor, lambda: next(iterator))
            except StopIteration:  # noqa: PERF203
                break
            else:
                yield dict(res)

    async def fetch(self, query: str) -> AsyncIterator[dict[str, Any]]:
        """Yield records from a read query, retrying connection failures."""
        for retry_wait in RETRY_WAITS:
            try:
                session, iterator = await self.fetch_start(query)
            except (BrokenPipeError, ServiceUnavailable):  # noqa: PERF203
                if retry_wait == RETRY_WAITS[-1]:
                    raise
                await asyncio.sleep(retry_wait)
            else:
                break

        async for record in self.fetch_iterate(iterator):
            yield record

        await self.loop.run_in_executor(self.executor, session.close)

    async def fetch_one(self, query: str) -> dict[str, Any] | None:
        """Return the first record from a read query, if present."""
        async for record in self.fetch(query):
            return record
        return None

    async def exec(self, query: str) -> None:
        """Run a query and discard its records."""
        async for _ in self.fetch(query):
            ...


class Neo4jHTTP:
    """Send Cypher queries to Neo4j over HTTP."""

    def __init__(self, url: str, user: str, password: str) -> None:
        """Create synchronous and asynchronous clients with basic authentication."""
        encoded = b64encode(f"{user}:{password}".encode()).decode()
        headers = {"Authorization": f"Basic {encoded}"}
        self.client = httpx.Client(base_url=url, headers=headers)
        """HTTP client used by synchronous queries."""

        self.async_client = httpx.AsyncClient(base_url=url, headers=headers)
        """HTTP client used by asynchronous queries."""

    def _payload(self, query: str, parameters: Mapping[str, Any] | None) -> dict[str, Any]:
        parameters = parameters or {}
        return {
            "statements": [
                {
                    "statement": query,
                    "parameters": parameters,
                },
            ],
        }

    def _response(self, response: httpx.Response) -> list[dict[str, Any]]:
        data = response.json()

        if "errors" in data:
            for error in data["errors"]:
                logger.error(error)
            return []

        return data["results"]

    def exec(self, query: str, parameters: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        """Run a query and return the HTTP result entries."""
        logger.info(query)
        with self.client as client:
            return self._response(client.post("db/neo4j/tx/commit", json=self._payload(query, parameters)))

    async def aexec(self, query: str, parameters: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        """Run a query asynchronously and return the HTTP result entries."""
        logger.info(query)
        async with self.async_client as client:
            return self._response(await client.post("db/neo4j/tx/commit", json=self._payload(query, parameters)))
