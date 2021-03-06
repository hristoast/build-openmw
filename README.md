# build-openmw

This script aims to provide an optimized, portable, and reproducible way to build [OpenMW](https://github.com/openmw/openmw) oneself.  Also supports [TES3MP](https://github.com/TES3MP/openmw-tes3mp).

## Installation

The script requires Python 3.3 or higher and can be ran directly out of a cloned repo, or installed system-wide like so:

    make install

## Uninstall

To uninstall what was installed by this:

    rm -rf /opt/build-openmw/*
    
You'll be left with an empty directory.  If you've used a different install prefix, then adjust your delete command appropriately.

## Usage

Run `build-openmw.py` with no arguments to get everything you need - it will potentially take several hours to complete unless you have a powerful CPU and a lot of RAM.  Subsequent runs will only rebuild OpenMW, and only if there have been changes in the upstream repository (unless a `--force-*` argument is given.)

Pass the `--help` argument to see advanced usage options.  For a local install, use something like this:

    build-openmw --make-install --verbose

If this isn't your first run, you can skip installing packages via your package manager like this:

    build-openmw --make-install --skip-install-pkgs --verbose

Both of the above build everything needed to run OpenMW without creating any package.

## Advanced

### Build TES3MP (experimental)

To build the `0.7.0` branch of TES3MP:

    build-openmw -MP -b 0.7.0

### Build a portable TES3MP inside a docker container

Uses GrimKriegor's excellent `tes3mp-forge` build container

    # From inside this repository, build the image
    make image

    # Run the build, it will be placed into `$HOME/backups/build-openmw`
    make tes3mp-package

### Build a release

To build the `0.43` release of OpenMW:

    build-openmw --tag openmw-0.43.0

Any valid git tag can be built this way.

### Build a branch of a fork

This script allows one to easily build any git rev.  If you want to build a branch from a fork, for example, you would first ensure you've added the remote for the fork you want to build:

    git remote add anyoldname3 https://github.com/AnyOldName3/openmw.git

Then, pass your branch as an argument:

    build-openmw --make-install --skip-install-pkgs --branch anyoldname3/osgshadow-test-vdsm

This will build and not package the tip of the `osgshadow-test-vdsm` branch from Anyoldname3's fork.

### Rebuild a dependency

If for some reason you want to rebuild any dependency (maybe osg-openmw has an update), you can use the various force flags:

    # Force rebuild OSG
    build-openmw --force-osg

    # Force rebuild everything
    build-openmw --force-all

## Why?

OpenMW has several dependencies that are at various stages of release on any given GNU/Linux distribution.  This script tries to simplify the process of running OpenMW by building and bundling what have been, in my experience, the most widely varying of these.

Nowadays, even with wide availablility of all dependencies, it's still nice to have an automated and reproducible way of doing the build process.
