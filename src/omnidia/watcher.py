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

"""Keep the graph database in sync with file system events."""

from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileSystemMovedEvent
from watchdog.observers.polling import PollingObserver as Observer

from omnidia.db import Neo4jHTTP
from omnidia.exclusion import excluded


class Handler(FileSystemEventHandler):
    """Apply file system changes to the graph database."""

    def __init__(self, db: Neo4jHTTP) -> None:
        """Store the database used by event handlers."""
        super().__init__()
        self.db = db
        """Database updated when file system events arrive."""

    def on_moved(self, event: FileSystemMovedEvent) -> None:
        """Update a file node when the file moves."""
        if not event.is_directory:
            old_path = Path(event.src_path).resolve()
            new_path = Path(event.dest_path).resolve()
            if excluded(str(new_path)):
                self.on_deleted(event)
            else:
                self.db.exec(f'MERGE (n:File {{path: "{old_path}"}}) SET n = {{path: "{new_path}"}}')
                if old_path.parent != new_path.parent:  # changed directory
                    self.db.exec(
                        f"""
                        MATCH (f:File {{path: \"{new_path}\"}}),
                            (d_old:Directory {{path: \"{old_path.parent!s}\"}}),
                            (d_new:Directory {{path: \"{new_path.parent!s}\"}}),
                            (f) -[r_old:In]-> (d_old)
                        DELETE r_old
                        CREATE (f) -[:In]-> (d_new)
                        """,
                    )

    def on_created(self, event: FileSystemEvent) -> None:
        """Add a node for a new file or directory."""
        label = "Directory" if event.is_directory else "File"
        file_path = Path(event.src_path).resolve()
        parent_path = str(file_path.parent)
        file_path = str(file_path)
        if not excluded(file_path):
            self.db.exec(
                f"""
                MATCH (d:Directory {{path: \"{parent_path}\"}})
                CREATE (d) <-[:In]- (:{label} {{path: \"{file_path}\"}})
                """,
            )

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Remove the node for a deleted file or directory."""
        label = "Directory" if event.is_directory else "File"
        path = str(Path(event.src_path).resolve())
        self.db.exec(f'MATCH (n:{label} {{path: "{path}"}}) DETACH DELETE n')


def watch(path: str) -> None:
    """Watch a directory and apply changes until interrupted."""
    neo4j = Neo4jHTTP("http://localhost:7474", "neo4j", "s3cr3t")
    handler = Handler(db=neo4j)
    observer = Observer()
    observer.schedule(handler, path=path, recursive=True)
    observer.start()
    try:
        while True:
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
