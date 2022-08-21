#!/usr/bin/env python3
import argparse
import datetime
import logging
import os
import shutil
import subprocess
import sys


BULLET_VERSION = "3.17"
FFMPEG_VERSION = "n4.4.1"
MYGUI_VERSION = "MyGUI3.4.1"
SDL2_VERSION = "release-2.0.14"
QT_VERSION = "5.15.0"
UNSHIELD_VERSION = "1.4.2"
OPENMW_OSG_BRANCH = "3.6"
CPUS = os.cpu_count() + 1
INSTALL_PREFIX = os.path.join("/", "opt", "build-openmw")
DESC = "Build OpenMW for your system, install it all to {}.  Also builds the OpenMW fork of OSG, and optionally libBullet, Unshield, and MyGUI, and links against those builds.".format(
    INSTALL_PREFIX
)
LOGFMT = "%(asctime)s | %(message)s"
OUT_DIR = os.getenv("HOME")
SRC_DIR = os.path.join(INSTALL_PREFIX, "src")
ARCH_PKGS = "".split()
# TODO: conditionally add bullet and unshield
DEBIAN_PKGS = "cmake git libopenal-dev libbullet-dev libsdl2-dev qt5-default libfreetype6-dev libavcodec-dev libavformat-dev libavutil-dev libswscale-dev cmake build-essential libqt5opengl5-dev libunshield-dev libmygui-dev libbullet-dev".split()
FEDORA_PKGS = "sqlite-devel unshield-devel redhat-lsb-core openal-devel libjpeg-turbo-devel SDL2-devel qt5-qtbase-devel git boost-thread boost-program-options boost-system boost-devel ffmpeg-devel ffmpeg-libs gcc-c++ tinyxml-devel cmake lz4-devel zlib-devel freetype-devel luajit-devel libXt-devel".split()
UBUNTU_PKGS = (
    ["libfreetype6-dev", "libbz2-dev", "liblzma-dev"]
    + DEBIAN_PKGS
    + [
        "libboost-iostreams1.62-dev",
        "libboost-filesystem1.62-dev",
        "libboost1.62-dev",
        "libboost-thread1.62-dev",
        "libboost-program-options1.62-dev",
        "libboost-system1.62-dev",
    ]
)
DEBIAN_PKGS += [
    "libboost-filesystem-dev",
    "libboost1.71-dev",
    "libboost-thread-dev",
    "libboost-program-options-dev",
    "libboost-system-dev",
]
VOID_PKGS = "make SDL2-devel boost-devel bullet-devel cmake ffmpeg-devel freetype-devel gcc git libXt-devel libavformat libavutil liblz4-devel libmygui-devel libopenal-devel libopenjpeg2-devel libswresample libswscale libunshield-devel pkg-config python-devel python3-devel qt5-devel sqlite-devel zlib-devel".split()
PROG = "build-openmw"
VERSION = "1.13"


def emit_log(msg: str, level=logging.INFO, quiet=False, *args, **kwargs) -> None:
    """Logging wrapper."""
    if not quiet:
        if level == logging.DEBUG:
            logging.debug(msg, *args, **kwargs)
        elif level == logging.INFO:
            logging.info(msg, *args, **kwargs)
        elif level == logging.WARN:
            logging.warning(msg, *args, **kwargs)
        elif level == logging.ERROR:
            logging.error(msg, *args, **kwargs)


def ensure_dir(path: str, create=True):
    """
    Small directory-making wrapper, uses sudo to create
    if need be and then chowns to the running user.
    """
    if not os.path.exists(path) and not os.path.isdir(path):
        if create:
            try:
                os.mkdir(path)
            except PermissionError:
                emit_log("Can't write '{}', trying with sudo...".format(path))
                execute_shell(["sudo", "mkdir", path])[1]
                emit_log("Chowning '{}' so sudo isn't needed anymore...".format(path))
                execute_shell(["sudo", "chown", "{}:".format(os.getlogin()), path])[1]
            emit_log("{} now exists".format(path))
        else:
            emit_log("Does {0} exist? {1}".format(path, os.path.isdir(path)))
            return os.path.isdir(path)
    else:
        emit_log("{} exists".format(path))


def error_and_die(msg: str) -> SystemExit:
    sys.stderr.write("ERROR: " + msg + " Exiting ..." + "\n")
    sys.exit(1)


def execute_shell(cli_args: list, env=None, verbose=False) -> tuple:
    """Small convenience wrapper around subprocess.Popen."""
    # TODO: Some way to show the build env when printing the command
    emit_log("EXECUTING: " + " ".join(cli_args), level=logging.DEBUG)
    if verbose:
        p = subprocess.Popen(cli_args, env=env)
    else:
        p = subprocess.Popen(
            cli_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=env
        )
    c = p.communicate()
    return p.returncode, c


def build_library(
    libname,
    check_file=None,
    clone_dest=None,
    cmake=True,
    cmake_args=None,
    cmake_target="..",
    cpus=None,
    env=None,
    force=False,
    install_prefix=INSTALL_PREFIX,
    git_url=None,
    make_install=True,
    patch=None,
    quiet=False,
    src_dir=SRC_DIR,
    verbose=False,
    version="master",
):
    def _configure_make():
        emit_log("{} building with configure and make!".format(libname))

        emit_log("{} running make clean ...".format(libname))
        out, err = execute_shell(["make", "clean"], verbose=verbose)[1]
        # if err:
        #     error_and_die(err.decode("utf-8"))

        emit_log("{} running configure ...".format(libname))
        if libname == "qt5":
            c = [
                "./configure",
                "--prefix={0}/{1}".format(install_prefix, libname),
                "-opensource",
                "-confirm-license",
                "-qt-harfbuzz",
                "-fontconfig",
                "-no-use-gold-linker",
                "-no-mimetype-database",
                "-nomake",
                "examples",
                "-shared",
            ]
        else:
            c = ["./configure", "--prefix={0}/{1}".format(install_prefix, libname)]

        # ./configure -prefix /usr/local -headerdir /usr/local/include/qt5 -opensource -confirm-license -qt-harfbuzz -fontconfig -no-use-gold-linker -no-mimetype-database -nomake examples -shared > ${deps_dir}/qt5.log 2>&1

        out, err = execute_shell(c, verbose=verbose)[1]
        if err:
            error_and_die(err.decode("utf-8"))

        emit_log("{} running make (this will take a while) ...".format(libname))
        exitcode, output = execute_shell(["make", "-j{}".format(cpus)], verbose=verbose)
        if exitcode != 0:
            emit_log(output[1])
            error_and_die("make exited nonzero!")

        emit_log("{} running make install ...".format(libname))
        out, err = execute_shell(["make", "install"], verbose=verbose)[1]
        if err:
            error_and_die(err.decode("utf-8"))

        emit_log("{} installed successfully!".format(libname))

    def _git_clean_src():
        os.chdir(os.path.join(src_dir, clone_dest))
        if force:
            # TODO: also do this if an explicit fetch flag is used
            emit_log("Fetching latest sources ...")
            execute_shell(["git", "fetch", "--all"])[1][0]
        emit_log("{} executing source clean".format(libname))
        execute_shell(["git", "checkout", "--", "."], verbose=verbose)
        execute_shell(["git", "clean", "-df"], verbose=verbose)

        if libname == "osg-openmw":
            emit_log(
                "{} resetting source to the desired rev ({rev})".format(
                    libname, rev=OPENMW_OSG_BRANCH
                )
            )
            execute_shell(["git", "checkout", OPENMW_OSG_BRANCH], verbose=verbose)
            execute_shell(
                ["git", "reset", "--hard", "origin/" + OPENMW_OSG_BRANCH],
                verbose=verbose,
            )

        elif libname != "osg-openmw":
            emit_log(
                "{} resetting source to the desired rev ({rev})".format(
                    libname, rev=version
                )
            )
            execute_shell(["git", "checkout", version], verbose=verbose)
            execute_shell(["git", "reset", "--hard", version], verbose=verbose)

    if not clone_dest:
        clone_dest = libname
    if os.path.exists(check_file) and os.path.isfile(check_file) and not force:
        emit_log("{} found!".format(libname))
    else:
        emit_log("{} building now ...".format(libname))
        if not os.path.exists(os.path.join(src_dir, clone_dest)):
            emit_log("{} source directory not found, cloning...".format(clone_dest))
            os.chdir(src_dir)
            if "osg-openmw" in clone_dest:
                execute_shell(
                    ["git", "clone", "-b", OPENMW_OSG_BRANCH, git_url, clone_dest],
                    verbose=verbose,
                )[1]
            else:
                execute_shell(["git", "clone", git_url, clone_dest], verbose=verbose)[1]
            if not os.path.exists(os.path.join(src_dir, libname)):
                error_and_die("Could not clone {} for some reason!".format(clone_dest))

        if force and os.path.exists(os.path.join(install_prefix, libname)):
            emit_log("{} forcing removal of previous install".format(libname))
            shutil.rmtree(os.path.join(install_prefix, libname))

        _git_clean_src()

        if patch:
            emit_log("Applying patch: " + patch)
            code = os.system("patch -p1 < " + patch)
            if code > 0:
                error_and_die("There was a problem applying the patch!")

        os.chdir(os.path.join(src_dir, clone_dest))

        if cmake:
            emit_log("{} building with cmake".format(libname))
            build_dir = os.path.join(src_dir, clone_dest, "build")
            if os.path.isdir(build_dir):
                emit_log("Removing dir tree: " + build_dir)
                shutil.rmtree(build_dir)
            os.mkdir(build_dir)
            os.chdir(build_dir)

            emit_log("{} running cmake ...".format(libname))
            build_cmd = [
                "cmake",
                "-DCMAKE_INSTALL_PREFIX={}/{}".format(install_prefix, libname),
            ]
            if cmake_args:
                build_cmd += cmake_args
            build_cmd += [cmake_target]
            exitcode, output = execute_shell(build_cmd, env=env, verbose=verbose)
            if exitcode != 0:
                emit_log(output[1])
                error_and_die("cmake exited nonzero!")

            emit_log("{} running make (this will take a while) ...".format(libname))
            exitcode, output = execute_shell(
                ["make", "-j{}".format(cpus)], env=env, verbose=verbose
            )
            if exitcode != 0:
                emit_log(output[1])
                error_and_die("make exited nonzero!")

            if make_install:
                emit_log("{} running make install ...".format(libname))
                out, err = execute_shell(["make", "install"], env=env, verbose=verbose)[
                    1
                ]
                if err:
                    error_and_die(err.decode("utf-8"))

                emit_log("{} installed successfully".format(libname))
        else:
            _configure_make()


def get_distro() -> tuple:
    """Try to run 'lsb_release -d' and return the output."""
    return execute_shell(["lsb_release", "-d"])[1]


def get_repo_sha(
    src_dir: str, repo="openmw", rev=None, pull=True, verbose=False
) -> str:
    try:
        os.chdir(os.path.join(src_dir, repo))
    except FileNotFoundError:
        return False
    if pull:
        emit_log("Fetching latest sources ...")
        execute_shell(["git", "fetch", "--all"])[1][0]

    execute_shell(["git", "checkout", rev], verbose=verbose)[1][0]
    execute_shell(["git", "reset", "--hard", rev], verbose=verbose)[1][0]

    out = execute_shell(["git", "rev-parse", "--short", "HEAD"])[1][0]
    return out.decode().strip()


def install_packages(distro: str, **kwargs) -> bool:
    quiet = kwargs.pop("quiet", "")
    verbose = kwargs.pop("verbose", "")

    emit_log(
        "Attempting to install dependency packages, please enter your sudo password as needed...",
        quiet=quiet,
    )
    user_uid = os.getuid()
    # TODO: install system OSG as needed..
    if "void" in distro.lower():
        emit_log("Distro detected as 'Void Linux'")
        cmd = ["xbps-install", "--yes"] + VOID_PKGS
        if user_uid > 0:
            cmd = ["sudo"] + cmd
        out, err = execute_shell(cmd, verbose=verbose)[1]
    elif "arch" in distro.lower():
        emit_log("Distro detected as 'Arch Linux'")
        cmd = ["pacman", "-sy"] + ARCH_PKGS
        if user_uid > 0:
            cmd = ["sudo"] + cmd
        out, err = execute_shell(cmd, verbose=verbose)[1]
    elif "debian" in distro.lower():
        emit_log("Distro detected as 'Debian'")
        if user_uid > 0:
            cmd = ["sudo", "apt-get", "install", "-y", "--force-yes"] + DEBIAN_PKGS
        else:
            cmd = ["apt-get", "install", "-y", "--force-yes"] + DEBIAN_PKGS
        out, err = execute_shell(cmd, verbose=verbose)[1]
    elif "devuan" in distro.lower():
        emit_log("Distro detected as 'Devuan'")
        # Debian packages should just work in this case.
        if user_uid > 0:
            cmd = ["sudo", "apt-get", "install", "-y", "--force-yes"] + DEBIAN_PKGS
        else:
            cmd = ["apt-get", "install", "-y", "--force-yes"] + DEBIAN_PKGS
        out, err = execute_shell(cmd, verbose=verbose)[1]
    elif "ubuntu" in distro.lower() or "mint" in distro.lower():
        emit_log("Distro detected as 'Mint' or 'Ubuntu'!")
        msg = "Package installation completed!"
        if user_uid > 0:
            cmd = ["sudo", "apt-get", "install", "-y", "--force-yes"] + UBUNTU_PKGS
        else:
            cmd = ["apt-get", "install", "-y", "--force-yes"] + UBUNTU_PKGS
        out, err = execute_shell(cmd, verbose=verbose)[1]
    elif "fedora" in distro.lower():
        emit_log("Distro detected as 'Fedora'")
        if user_uid > 0:
            # cmd = ["dnf", "groupinstall", "-y", "development-tools"]
            # out, err = execute_shell(cmd, verbose=verbose)[1]
            cmd = ["dnf", "install", "-y"] + FEDORA_PKGS
            out, err = execute_shell(cmd, verbose=verbose)[1]
        else:
            # cmd = ["sudo", "dnf", "groupinstall", "-y", "development-tools"]
            # out, err = execute_shell(cmd, verbose=verbose)[1]
            cmd = ["sudo", "dnf", "install", "-y"] + FEDORA_PKGS
            out, err = execute_shell(cmd, verbose=verbose)[1]
    else:
        error_and_die(
            "Your OS is not yet supported!  If you think you know what you are doing, you can use '-S' to continue anyways."
        )
    msg = "Package installation completed"

    emit_log(msg)
    return out, err


def parse_argv() -> None:
    """Set up args and parse them."""
    parser = argparse.ArgumentParser(description=DESC, prog=PROG)
    parser.add_argument(
        "--version", action="version", version=VERSION, help=argparse.SUPPRESS
    )
    version_options = parser.add_mutually_exclusive_group()
    version_options.add_argument("-s", "--sha", help="The git sha1sum to build.")
    version_options.add_argument("-t", "--tag", help="The git release tag to build.")
    version_options.add_argument(
        "-b", "--branch", help="The git branch to build (the tip of.)"
    )
    options = parser.add_argument_group("Options")
    options.add_argument(
        "--system-bullet",
        action="store_true",
        help="Build LibBullet, rather than use the system package.",
    )
    options.add_argument(
        "--build-ffmpeg",
        action="store_true",
        help="Build FFMPEG, rather than use the system package.",
    )
    options.add_argument(
        "--build-mygui",
        action="store_true",
        help="Build MyGUI, rather than use the system package.",
    )
    options.add_argument(
        "--build-qt5",
        action="store_true",
        help="Build Qt5, rather than use the system package.",
    )
    options.add_argument(
        "--build-sdl2",
        action="store_true",
        help="Build SDL2, rather than use the system package.",
    )
    options.add_argument(
        "--build-unshield",
        action="store_true",
        help="Build libunshield, rather than use the system package.",
    )
    options.add_argument(
        "--force-bullet", action="store_true", help="Force build LibBullet."
    )
    options.add_argument(
        "--force-ffmpeg", action="store_true", help="Force build FFMPEG."
    )
    options.add_argument(
        "--force-mygui", action="store_true", help="Force build MyGUI."
    )
    options.add_argument("--force-qt5", action="store_true", help="Force build Qt5.")
    options.add_argument("--force-sdl2", action="store_true", help="Force build SDL2.")
    options.add_argument(
        "--force-openmw", action="store_true", help="Force build OpenMW."
    )
    options.add_argument("--force-osg", action="store_true", help="Force build OSG.")
    options.add_argument(
        "--force-raknet", action="store_true", help="Force build Raknet."
    )
    options.add_argument(
        "--force-unshield", action="store_true", help="Force build Unshield."
    )
    options.add_argument(
        "--force-all",
        action="store_true",
        help="Force build all dependencies and OpenMW.",
    )
    options.add_argument(
        "--system-osg",
        action="store_true",
        help="Use the system-provided OSG instead of the OpenMW forked one.",
    )
    # TODO: Don't hardcode the OSG branch, use the below flag.
    # options.add_argument(
    #     "--openmw-osg-branch",
    #     action="store_true",
    #     help="Specify the OpenMW OSG fork branch to build.  Default: "
    #     + OPENMW_OSG_BRANCH,
    # )
    options.add_argument(
        "--install-prefix",
        help="Set the install prefix. Default: {}".format(INSTALL_PREFIX),
    )
    options.add_argument(
        "-j",
        "--jobs",
        help="How many cores to use with make.  Default: {}".format(CPUS),
    )
    options.add_argument(
        "-p", "--make-pkg", action="store_true", help="Make a portable package."
    )
    options.add_argument(
        "-N",
        "--no-pull",
        action="store_true",
        help="Don't do a 'git fetch --all' on the OpenMW sources.",
    )
    options.add_argument(
        "-o",
        "--out",
        metavar="DIR",
        help="Where to write the package to.  Default: {}".format(OUT_DIR),
    )
    options.add_argument(
        "-P", "--patch", help="Path to a patch file that should be applied."
    )
    options.add_argument(
        "-S",
        "--skip-install-pkgs",
        action="store_true",
        help="Don't try to install dependencies.",
    )
    options.add_argument(
        "--src-dir", help="Set the source directory. Default: {}".format(SRC_DIR)
    )
    options.add_argument(
        "-U", "--update", action="store_true", help="Try to update this script."
    )
    options.add_argument(
        "--with-debug", action="store_true", help="Build OpenMW with debug symbols."
    )
    options.add_argument(
        "--with-essimporter",
        action="store_true",
        help="Do build the ess importer. (Default: false)",
    )
    options.add_argument(
        "--without-cs",
        action="store_true",
        help="Do not build OpenMW-CS. (Default: false)",
    )
    options.add_argument(
        "--without-iniimporter",
        action="store_true",
        help="Do not build INI Importer. (Default: false)",
    )
    options.add_argument(
        "--without-launcher",
        action="store_true",
        help="Do not build the OpenMW launcher. (Default: false)",
    )
    options.add_argument(
        "--without-wizard",
        action="store_true",
        help="Do not build the install wizard. (Default: false)",
    )
    options.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output."
    )

    return parser.parse_args()


def main() -> None:
    # TODO: option to skip a given dependency?
    logging.basicConfig(format=LOGFMT, level=logging.INFO, stream=sys.stdout)
    start = datetime.datetime.now()
    cpus = CPUS
    distro = None
    system_bullet = False
    build_ffmpeg = False
    build_mygui = False
    build_sdl2 = False
    build_qt5 = False
    build_unshield = False
    force_bullet = False
    force_ffmpeg = False
    force_mygui = False
    force_sdl2 = False
    force_qt5 = False
    force_openmw = False
    force_osg = False
    force_unshield = False
    install_prefix = INSTALL_PREFIX
    system_osg = False
    parsed = parse_argv()
    out_dir = OUT_DIR
    patch = None
    pull = True
    skip_install_pkgs = False
    src_dir = SRC_DIR
    verbose = False
    sha = None
    tag = None
    branch = "master"
    with_debug = False
    with_essimporter = False
    without_cs = False
    without_iniimporter = False
    without_launcher = False
    without_wizard = False

    if parsed.force_all:
        force_bullet = True
        force_ffmpeg = True
        force_mygui = True
        force_openmw = True
        force_osg = True
        force_qt5 = True
        force_unshield = True
        emit_log("Force building all dependencies")
    if parsed.system_bullet:
        system_bullet = True
        emit_log("Using the system LibBullet")
    if parsed.build_ffmpeg:
        build_ffmpeg = True
        emit_log("Building FFMPEG")
    if parsed.build_mygui:
        build_mygui = True
        emit_log("Building MyGUI")
    if parsed.build_qt5:
        build_qt5 = True
        emit_log("Building Qt")
    if parsed.build_sdl2:
        build_sdl2 = True
        emit_log("Building SDL2")
    if parsed.build_unshield:
        build_unshield = True
        emit_log("Building Unshield")
    if parsed.force_bullet:
        force_bullet = True
        emit_log("Forcing build of LibBullet")
    if parsed.force_ffmpeg:
        force_ffmpeg = True
        emit_log("Forcing build of FFMPEG")
    if parsed.force_mygui:
        force_mygui = True
        emit_log("Forcing build of MyGUI")
    if parsed.force_qt5:
        force_qt5 = True
        emit_log("Forcing build of Qt")
    if parsed.force_sdl2:
        force_sdl2 = True
        emit_log("Forcing build of SDL2")
    if parsed.force_openmw:
        force_openmw = True
        emit_log("Forcing build of OpenMW")
    if parsed.force_osg:
        force_osg = True
        emit_log("Forcing build of OSG")
    if parsed.force_unshield:
        force_unshield = True
        emit_log("Forcing build of Unshield")
    if parsed.install_prefix:
        install_prefix = parsed.install_prefix
        emit_log("Using the install prefix: " + install_prefix)
    if parsed.jobs:
        cpus = parsed.jobs
        emit_log("'-j{}' will be used with make".format(cpus))
    if parsed.no_pull:
        pull = False
        emit_log("git fetch will not be ran")
    if parsed.out:
        out_dir = parsed.out
        emit_log("Out dir set to: " + out_dir)
    if parsed.patch:
        patch = os.path.abspath(parsed.patch)
        if os.path.isfile(patch):
            emit_log("Will attempt to use this patch: " + patch)
        else:
            error_and_die("The supplied patch isn't a file!")
    if parsed.skip_install_pkgs:
        skip_install_pkgs = parsed.skip_install_pkgs
        emit_log("Package installs will be skipped")
    if parsed.system_osg:
        system_osg = True
        emit_log("The system OSG will be used.")
        emit_log("The system OSG will be used.")
    if parsed.src_dir:
        src_dir = parsed.src_dir
        emit_log("Source directory set to: " + src_dir)
    if parsed.verbose:
        verbose = parsed.verbose
        logging.getLogger().setLevel(logging.DEBUG)
        emit_log("Verbose output enabled")
    if parsed.with_debug:
        with_debug = True
    if parsed.with_essimporter:
        with_essimporter = True
    if parsed.without_cs:
        without_cs = True
    if parsed.without_iniimporter:
        without_iniimporter = True
    if parsed.without_launcher:
        without_launcher = True
    if parsed.without_wizard:
        without_wizard = True
    if parsed.branch:
        branch = rev = parsed.branch
        if "/" not in branch:
            branch = rev = "origin/" + parsed.branch
        emit_log("Branch selected: " + branch)
    elif parsed.sha:
        sha = rev = parsed.sha
        emit_log("SHA selected: " + sha)
    elif parsed.tag:
        tag = rev = parsed.tag
        emit_log("Tag selected: " + tag)
    else:
        rev = "origin/" + branch

    try:
        out, err = get_distro()
        if err:
            error_and_die(err.decode())
    except FileNotFoundError:
        if skip_install_pkgs:
            pass
        else:
            error_and_die(
                "Unable to determine your distro to install dependencies!  Try again and use '-S' if you know what you are doing."
            )
    else:
        distro = out.decode().split(":")[1].strip()

    if not skip_install_pkgs:
        out, err = install_packages(distro, verbose=verbose)
        if err:
            # Isn't always necessarily exit-worthy
            emit_log("Stderr received: " + err.decode())

    src_dir = os.path.join(install_prefix, "src")
    # This is a serious edge case, but let's
    # show a sane error when /opt doesn't exist.
    ensure_dir(os.path.join("/", "opt"))
    ensure_dir(install_prefix)
    ensure_dir(src_dir)

    if build_ffmpeg or force_ffmpeg:
        # FFMPEG
        build_library(
            "ffmpeg",
            check_file=os.path.join(install_prefix, "ffmpeg", "bin", "ffmpeg"),
            cmake=False,
            cpus=cpus,
            force=force_ffmpeg,
            git_url="https://github.com/FFmpeg/FFmpeg.git",
            install_prefix=install_prefix,
            src_dir=src_dir,
            verbose=verbose,
            version=FFMPEG_VERSION,
        )

    if not system_osg:
        # OSG-OPENMW

        build_library(
            "osg-openmw",
            check_file=os.path.join(install_prefix, "osg-openmw", "lib", "libosg.so"),
            cmake_args=[
                "-DBUILD_OSG_PLUGINS_BY_DEFAULT=0",
                "-DBUILD_OSG_PLUGIN_OSG=1",
                "-DBUILD_OSG_PLUGIN_DDS=1",
                "-DBUILD_OSG_PLUGIN_TGA=1",
                "-DBUILD_OSG_PLUGIN_BMP=1",
                "-DBUILD_OSG_PLUGIN_JPEG=1",
                "-DBUILD_OSG_PLUGIN_PNG=1",
                "-DBUILD_OSG_DEPRECATED_SERIALIZERS=0",
                "-DBUILD_OSG_EXAMPLES=0",
            ],
            cpus=cpus,
            force=force_osg,
            git_url="https://github.com/OpenMW/osg.git",
            install_prefix=install_prefix,
            src_dir=src_dir,
            verbose=verbose,
        )

    # BULLET
    if not system_bullet or force_bullet:
        build_library(
            "bullet",
            check_file=os.path.join(
                install_prefix, "bullet", "lib", "libLinearMath.so"
            ),
            cmake_args=[
                "-DINSTALL_LIBS=on",
                "-DBUILD_BULLET3=off",
                "-DBUILD_CPU_DEMOS=off",
                "-DBUILD_UNIT_TESTS=off",
                "-DBUILD_BULLET2_DEMOS=off",
                "-DBUILD_EXTRAS=off",
                "-DBUILD_GIMPACTUTILS_EXTRA=off",
                "-DBUILD_HACD_EXTRA=off",
                "-DBUILD_INVERSE_DYNAMIC_EXTRA=off",
                "-DBUILD_OBJ2SDF_EXTRA=off",
                "-DBUILD_OPENGL3_DEMOS=off",
                "-DBUILD_BULLET_ROBOTICS_EXTRA=off",
                "-DBUILD_BULLET_ROBOTICS_GUI_EXTRA=off",
                "-DBUILD_SHARED_LIBS=on",
                "-DBULLET2_MULTITHREADING=on",
                "-DUSE_DOUBLE_PRECISION=on",
                "-DCMAKE_BUILD_TYPE=Release",
            ],
            cpus=cpus,
            force=force_bullet,
            git_url="https://github.com/bulletphysics/bullet3.git",
            install_prefix=install_prefix,
            src_dir=src_dir,
            verbose=verbose,
            version=BULLET_VERSION,
        )

    # UNSHIELD
    if build_unshield or force_unshield:
        build_library(
            "unshield",
            check_file=os.path.join(install_prefix, "unshield", "bin", "unshield"),
            cpus=cpus,
            force=force_unshield,
            git_url="https://github.com/twogood/unshield.git",
            install_prefix=install_prefix,
            src_dir=src_dir,
            verbose=verbose,
            version=UNSHIELD_VERSION,
        )

    # MYGUI
    if build_mygui or force_mygui:
        build_library(
            "mygui",
            check_file=os.path.join(
                install_prefix,
                "mygui",
                "include",
                "MYGUI",
                "MyGUI.h",
            ),
            cmake_args=[
                "-DMYGUI_BUILD_TOOLS=OFF",
                "-DMYGUI_RENDERSYSTEM=1",
                "-DMYGUI_BUILD_DEMOS=OFF",
                "-DMYGUI_BUILD_PLUGINS=OFF",
                "-DMYGUI_BUILD_TEST_APP=OFF",
                "-DMYGUI_BUILD_TOOLS=OFF",
                "-DMYGUI_BUILD_UNITTESTS=OFF",
            ],
            cpus=cpus,
            force=force_mygui,
            git_url="https://github.com/MyGUI/mygui.git",
            install_prefix=install_prefix,
            src_dir=src_dir,
            verbose=verbose,
            version=MYGUI_VERSION,
        )

    # Qt5 (base)
    if build_qt5:
        build_library(
            "qt5",
            check_file=os.path.join(install_prefix, "qt5", "bin", "qmake"),
            cmake=False,
            cpus=cpus,
            force=force_qt5,
            git_url="https://github.com/qt/qtbase.git",
            install_prefix=install_prefix,
            src_dir=src_dir,
            verbose=verbose,
            version=QT_VERSION,
        )

    # SDL2
    if build_sdl2:
        build_library(
            "sdl2",
            check_file=os.path.join(install_prefix, "sdl2", "bin", "sdl2-config"),
            cmake=False,
            cpus=cpus,
            force=force_sdl2,
            git_url="https://github.com/libsdl-org/SDL.git",
            install_prefix=install_prefix,
            src_dir=src_dir,
            verbose=verbose,
            version=SDL2_VERSION,
        )

    # OPENMW
    openmw_sha = get_repo_sha(src_dir, rev=rev, pull=pull, verbose=verbose)
    if openmw_sha:
        openmw = "openmw-{}".format(openmw_sha)
    else:
        # There's no sha yet since the source hasn't been cloned.
        openmw = "openmw"

    build_env = {"PATH": os.environ["PATH"]}

    if system_osg:
        prefix_path = ""
    else:
        prefix_path = "{0}/osg-openmw"

    if not system_bullet or force_bullet:
        prefix_path += ":{0}/bullet"
    if not build_ffmpeg or force_ffmpeg:
        prefix_path += ":{0}/ffmpeg"
        prefix_path += ":{0}/mygui"
    if build_qt5 or force_qt5:
        prefix_path += ":{0}/qt5"
    if build_sdl2 or force_sdl2:
        prefix_path += ":{0}/sdl2"
    if build_unshield or force_unshield:
        prefix_path += ":{0}/unshield"

    build_env["CMAKE_PREFIX_PATH"] = prefix_path.format(install_prefix)

    distro = None
    try:
        out, err = get_distro()
        if err:
            error_and_die(err.decode())
        distro = out.decode().split(":")[1].strip()
    except FileNotFoundError:
        if skip_install_pkgs:
            pass
        else:
            error_and_die(
                "Unable to determine your distro to install dependencies!  Try again and use '-S' if you know what you are doing."
            )

    build_type = "Release"
    if with_debug:
        build_type = "Debug"

    build_args = ["-DCMAKE_BUILD_TYPE=" + build_type, "-DDESIRED_QT_VERSION=5"]

    # Don't build the save importer..
    if not with_essimporter:
        build_args.append("-DBUILD_ESSIMPORTER=no")

    if without_cs:
        emit_log("NOT building the openmw-cs executable ...")
        build_args.append("-DBUILD_OPENCS=no")

    if without_iniimporter:
        emit_log("NOT building the openmw-iniimporter executable ...")
        build_args.append("-DBUILD_MWINIIMPORTER=no")

    if without_launcher:
        emit_log("NOT building the openmw-launcher executable ...")
        build_args.append("-DBUILD_LAUNCHER=no")

    if without_wizard:
        emit_log("NOT building the openmw-wizard executable ...")
        build_args.append("-DBUILD_WIZARD=no")

    if with_debug:
        build_args.append("-DOPENMW_LTO_BUILD=off")
    else:
        build_args.append("-DOPENMW_LTO_BUILD=on")

    if not system_osg:
        build_args.append(
            "-DOSG_DIR=" + os.path.join(install_prefix, "osg-openmw"),
        )

    build_library(
        openmw,
        check_file=os.path.join(install_prefix, openmw, "bin", "openmw"),
        cmake_args=build_args,
        clone_dest="openmw",
        cpus=cpus,
        env=build_env,
        force=force_openmw,
        git_url="https://github.com/OpenMW/openmw.git",
        install_prefix=install_prefix,
        patch=patch,
        src_dir=src_dir,
        verbose=verbose,
        version=rev,
    )
    os.chdir(install_prefix)
    # Don't fetch updates since new ones might exist
    openmw_sha = get_repo_sha(src_dir, rev=rev, pull=False, verbose=verbose)
    os.chdir(install_prefix)
    if str(openmw_sha) not in openmw:
        os.rename("openmw", "openmw-{}".format(openmw_sha))
    if os.path.islink("openmw"):
        os.remove("openmw")
    os.symlink("openmw-" + openmw_sha, "openmw")

    end = datetime.datetime.now()
    duration = end - start
    minutes = int(duration.total_seconds() // 60)
    seconds = int(duration.total_seconds() % 60)
    emit_log("Took {m} minutes, {s} seconds.".format(m=minutes, s=seconds))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        error_and_die("Ctrl-c recieved!")
