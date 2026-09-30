# Omnidia

[![ci](https://github.com/pawamoy/omnidia/workflows/ci/badge.svg)](https://github.com/pawamoy/omnidia/actions?query=workflow%3Aci)
[![documentation](https://img.shields.io/badge/docs-mkdocs%20material-blue.svg?style=flat)](https://pawamoy.github.io/omnidia/)
[![pypi version](https://img.shields.io/pypi/v/omnidia.svg)](https://pypi.org/project/omnidia/)

File (and abstract object) manager using a graph database and a web interface.

## Why is that?

A tree structure is not always efficient to explore and exploit your data.  
For example, where do you put a track called `Foo - Bar (Baz Remix).ogg`?  
In `Foo`'s directory or in `Baz`'s one? Maybe you could add a symbolic link so it's in both?  
What if this track is also part of a movie's original soundtrack?  
And you want it in one or two playlists of your own?  
And use it in a special project?  

In this case it would be easier to have the track somewhere, an abstracted element that knows
its path on the disk, and other elements defining links to it (its abstracted form).

Well, this is a graph. As an abstract layer above your file system.

Omnidia does not aim to provide an alternative file system. Its goal is to offer an interface
to manipulate your files (and other abstract objects) with graphs. Each file / object is a node
that can be connected to other files / objects. You can then search for things, connect them
and discover common attributes between different entities.

## Progression

Omnidia is currently just in alpha version. There are many graph database solutions, many
languages, many drivers and many framework that could be used to achieve this. For now the
chosen technologies are the following:

- [Python](https://www.python.org/) language
- [Neo4j](https://neo4j.com/) graph database
- [FastAPI](https://fastapi.tiangolo.com/) framework

The features available are the following:

- [watchdog](https://pypi.python.org/pypi/watchdog) handler to sync database with the content of a
  folder (i.e. copy files here -> nodes are created, delete/move/rename them -> same applied on db)

You can also visualize the nodes and edges
with Neo4j's web browser at [localhost:7474](localhost:7474).

## Installation

With `pip`:

```bash
pip install omnidia
```

With [`pipx`](https://github.com/pipxproject/pipx):

```bash
python3.8 -m pip install --user pipx
pipx install omnidia
```
