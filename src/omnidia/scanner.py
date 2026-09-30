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

"""Add files and directories to the graph database."""

import os
from collections.abc import Iterable
from pathlib import Path

from omnidia.db import Neo4jHTTP
from omnidia.exclusion import excluded


def create_file(db: Neo4jHTTP, path: Path) -> None:
    """Create a file node unless its path is excluded."""
    resolved_path = str(path.resolve())
    if not excluded(resolved_path):
        db.exec(f'MERGE (n:File {{path: "{resolved_path}"}})')


def create_directory(db: Neo4jHTTP, path: Path) -> None:
    """Create a directory node unless its path is excluded."""
    resolved_path = str(path.resolve())
    if not excluded(resolved_path):
        db.exec(f'MERGE (n:Directory {{path: "{resolved_path}"}})')


def create_files(db: Neo4jHTTP, parent: Path, files: Iterable[str]) -> None:
    """Link each included file to its parent directory."""
    parent_path = str(parent.resolve())
    for file_name in files:
        file_path = str((parent / file_name).resolve())
        if not excluded(file_path):
            db.exec(
                f"""
                MATCH (d:Directory {{path: \"{parent_path}\"}})
                MERGE (d) <-[:In]- (f:File {{path: \"{file_path}\"}})
                """,
            )


def create_directories(db: Neo4jHTTP, parent: Path, dirs: Iterable[str]) -> None:
    """Link each included directory to its parent directory."""
    parent_path = str(parent.resolve())
    for dir_name in dirs:
        dir_path = str((parent / dir_name).resolve())
        if not excluded(dir_path):
            db.exec(
                f"""
                MATCH (d1:Directory {{path: \"{parent_path}\"}})
                MERGE (d1) <-[:In]- (d2:Directory {{path: \"{dir_path}\"}})
                """,
            )


def scan(path: str | Path) -> None:
    """Walk a directory tree and add its contents to the graph database."""
    neo4j = Neo4jHTTP("http://localhost:7474", "neo4j", "s3cr3t")
    for root, dirs, files in os.walk(path):
        dirpath = Path(root)
        create_directory(neo4j, dirpath)
        create_directories(neo4j, dirpath, dirs)
        create_files(neo4j, dirpath, files)
