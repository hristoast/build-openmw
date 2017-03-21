# build-openmw

This script aims to provide an optimized, portable, and reproducible way to build OpenMW oneself.

It currently only works on Void Linux and Debian Jessie but very minimal changes should only be required to expand to other distributions.

## Usage

Run `build-openmw.sh` to build the "OpenMW Runtime".  This produces a file called `morrowind-$distro.tar.bzip2` in the home directory of the user running the script (`sudo` is required) as well as a fully functional "OpenMW Runtime" at `/opt/morrowind`.  If you decide to copy the produced tarball to another host to run, make sure it's extracted to `/opt/morrowind` or that `/opt/morrowind` is a symlink to wherever you choose to extract it to.

You can then play the game by calling the `run.sh` script that is bundled:

    /opt/morrowind/run.sh --launcher

If you haven't yet gotten the game set up, you will definitely want to use the `--launcher` argument and go through the setup wizard.  Once that's done, you can configure the game via the normal launcher GUI (select the Morrowind.esm file and any mods you have.)

You can also run the installer that comes with the package:

    /opt/morrowind/install.sh

This places an executable at `/usr/bin/morrowind`.

You could also make a convenience function, like this for `bash`:

    function morrowind
    {
        /opt/morrowind/run.sh ${@}
    }

Or this for `fish`:

    function morrowind
	    /opt/morrowind/run.sh $argv
    end

Then you can just do `morrowind` or `morrowind --launcher` from a terminal or launcher.

## Why?

OpenMW has several dependencies that are at various stages of release on any given GNU/Linux distribution.  This script tries to simplify the process of running OpenMW by building and bundling the biggest of these dependencies.
