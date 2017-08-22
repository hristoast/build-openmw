# build-openmw

This script aims to provide an optimized, portable, and reproducible way to build OpenMW oneself.

It currently only works on Void Linux and Debian Jessie but very minimal changes should only be required to expand to other distributions.

## Usage

```
./build-openmw.sh --help

Usage: build-openmw [-h] [-J] [-M] [-N] [-s SHA] [-t TAG] [--with-mygui] [--with-unshield]

Build OpenMW!

If ran with no arguments, the latest commit in master is built and packaged into a tarball along with the dependencies which were built.

Optional Arguments:
  --force               Force building, even if the requested revision is already built
  -h, --help            Show this help message and exit
  -J, --just-openmw     Only package OpenMW
  -N, --no-tar          Don't create any tarballs
  -M, --mp              Build TES3MP (Multiplayer fork of OpenMW - EXPERIMENTAL)
  -s SHA, --sha SHA     Build the specified git revision (sha1)
  -t TAG, --tag TAG     Build the specified git tag
  --with-mygui          Build MyGUI and link against it
  --with-unshield       Build Unshield and link against it
```

## Why?

OpenMW has several dependencies that are at various stages of release on any given GNU/Linux distribution.  This script tries to simplify the process of running OpenMW by building and bundling what have been, in my experience, the most widely varying of these.
