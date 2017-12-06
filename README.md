# build-openmw

This script aims to provide an optimized, portable, and reproducible way to build OpenMW oneself.

## Installation

The script requires Python 3.3 or higher and can be ran directly out of a cloned repo, or installed system-wide like so:

    make install

## Uninstall

To uninstall what was installed by this:

    rm -rf /opt/morrowind/*
    
You'll be left with an empty directory.  If you've used a different install prefix, then adjust your delete command appropriately.

## Usage

Run `build-openmw.py` with no arguments to get everything you need - it will potentially take several hours to complete unless you have a powerful CPU and a lot of RAM.  Subsequent runs will only rebuild OpenMW, and only if there have been changes in the upstream repository (unless a `--force-*` argument is given.)

Pass the `--help` argument to see advanced usage options.  For a local install, use something like this:

    build-openmw -n -v

If this isn't your first run, you can skip installing packages via your package manager like this:

    build-openmw -n -S -v

Both of the above build everything needed to run OpenMW without creating any package.

## Advanced

### Build a release

To build the `0.43` release of OpenMW:

    build-openmw -t openmw-0.43.0

Any valid git tag can be built this way.

### Build a branch of a fork

This script allows one to easily build any git rev.  If you want to build a branch from a fork, for example, you would first ensure you've added the remote for the fork you want to build:

    git remote add anyoldname3 https://github.com/AnyOldName3/openmw.git

Then, pass your branch as an argument:

    build-openmw -n -S -b anyoldname3/osgshadow-test-vdsm

This will build and not package the tip of the `osgshadow-test-vdsm` branch from Anyoldname3's fork.

### Rebuild a dependency

If for some reason you want to rebuild any dependency (maybe osg-openmw has an update), you can use the various force flags:

    # Force rebuild OSG
    build-openmw --force-osg

    # Force rebuild everything
    build-openmw --force-all

## Why?

OpenMW has several dependencies that are at various stages of release on any given GNU/Linux distribution.  This script tries to simplify the process of running OpenMW by building and bundling what have been, in my experience, the most widely varying of these.
