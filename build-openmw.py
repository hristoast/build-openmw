#!/usr/bin/env python3
import argparse
import datetime
import logging
import os
import shutil
import subprocess
import sys


BULLET_VERSION = "3.06"
MYGUI_VERSION = "3.2.2"
UNSHIELD_VERSION = "1.4.2"

RAKNET_VERSION = "origin/master"
OPENMW_OSG_BRANCH = "3.6"

TES3MP_CORESCRIPTS_VERSION = "0.7.0"

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
REDHAT_PKGS = "openal-devel SDL2-devel qt5-devel boost-filesystem git boost-thread boost-program-options boost-system ffmpeg-devel ffmpeg-libs gcc-c++ tinyxml-devel cmake".split()
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
VOID_PKGS = "SDL2-devel boost-devel bullet-devel cmake ffmpeg-devel freetype-devel gcc git libXt-devel libavformat libavutil liblz4-devel libmygui-devel libopenal-devel libopenjpeg2-devel libswresample libswscale libunshield-devel python-devel python3-devel qt5-devel zlib-devel".split()
VOID_TES3MP_PKGS = "LuaJIT-devel"

PROG = "build-openmw"
VERSION = "1.12"


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
            emit_log("Does {0} exist? {1}".format(path), os.path.isdir(path))
            return os.path.isdir(path)
    else:
        emit_log("{} exists".format(path))


def error_and_die(msg: str) -> SystemExit:
    sys.stderr.write("ERROR: " + msg + " Exiting ..." + "\n")
    sys.exit(1)


def execute_shell(cli_args: list, env=None, verbose=False) -> tuple:
    """Small convenience wrapper around subprocess.Popen."""
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
    def _git_clean_src():
        os.chdir(os.path.join(src_dir, clone_dest))
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
        if exitcode != 0 and libname != "tes3mp":
            emit_log(output[1])
            error_and_die("make exited nonzero!")

        if make_install:
            emit_log("{} running make install ...".format(libname))
            out, err = execute_shell(["make", "install"], env=env, verbose=verbose)[1]
            if err:
                error_and_die(err.decode("utf-8"))

            emit_log("{} installed successfully".format(libname))


def format_openmw_cmake_args(bullet_path: str, osg_path: str, use_bullet=False) -> list:
    if osg_path:
        lib = "lib"
        args = [
            "-DOPENTHREADS_INCLUDE_DIR={osg}/include".format(osg=osg_path),
            "-DOPENTHREADS_LIBRARY={osg}/{lib}/libOpenThreads.so".format(
                lib=lib, osg=osg_path
            ),
            "-DOSG_INCLUDE_DIR={osg}/include".format(osg=osg_path),
            "-DOSG_LIBRARY={osg}/{lib}/libosg.so".format(lib=lib, osg=osg_path),
            # "-DOSGANIMATION_INCLUDE_DIR={osg}/include".format(osg=osg_path),
            # "-DOSGANIMATION_LIBRARY={osg}/{lib}/libosgAnimation.so".format(
            #     lib=lib, osg=osg_path
            # ),
            "-DOSGDB_INCLUDE_DIR={osg}/include".format(osg=osg_path),
            "-DOSGDB_LIBRARY={osg}/{lib}/libosgDB.so".format(lib=lib, osg=osg_path),
            "-DOSGFX_INCLUDE_DIR={osg}/include".format(osg=osg_path),
            "-DOSGFX_LIBRARY={osg}/{lib}/libosgFX.so".format(lib=lib, osg=osg_path),
            "-DOSGGA_INCLUDE_DIR={osg}/include".format(osg=osg_path),
            "-DOSGGA_LIBRARY={osg}/{lib}/libosgGA.so".format(lib=lib, osg=osg_path),
            "-DOSGPARTICLE_INCLUDE_DIR={osg}/include".format(osg=osg_path),
            "-DOSGPARTICLE_LIBRARY={osg}/{lib}/libosgParticle.so".format(
                lib=lib, osg=osg_path
            ),
            "-DOSGTEXT_INCLUDE_DIR={osg}/include".format(osg=osg_path),
            "-DOSGTEXT_LIBRARY={osg}/{lib}/libosgText.so".format(lib=lib, osg=osg_path),
            "-DOSGUTIL_INCLUDE_DIR={osg}/include".format(osg=osg_path),
            "-DOSGUTIL_LIBRARY={osg}/{lib}/libosgUtil.so".format(lib=lib, osg=osg_path),
            "-DOSGVIEWER_INCLUDE_DIR={osg}/include".format(osg=osg_path),
            "-DOSGVIEWER_LIBRARY={osg}/{lib}/libosgViewer.so".format(
                lib=lib, osg=osg_path
            ),
        ]

    else:
        args = []
    return args


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
            cmd = ["dnf", "groupinstall", "-y", "development-tools"]
            out, err = execute_shell(cmd, verbose=verbose)[1]
            cmd = ["dnf", "install", "-y"] + REDHAT_PKGS
            out, err = execute_shell(cmd, verbose=verbose)[1]
        else:
            cmd = ["sudo", "dnf", "groupinstall", "-y", "development-tools"]
            out, err = execute_shell(cmd, verbose=verbose)[1]
            cmd = ["sudo", "dnf", "install", "-y"] + REDHAT_PKGS
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
        "--build-mygui",
        action="store_true",
        help="Build MyGUI, rather than use the system package.",
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
        "--force-mygui", action="store_true", help="Force build MyGUI."
    )
    options.add_argument(
        "--force-openmw", action="store_true", help="Force build OpenMW."
    )
    options.add_argument("--force-osg", action="store_true", help="Force build OSG.")
    options.add_argument(
        "--force-raknet", action="store_true", help="Force build Raknet."
    )
    options.add_argument(
        "--force-tes3mp", action="store_true", help="Force build TES3MP."
    )
    options.add_argument(
        "--force-unshield", action="store_true", help="Force build Unshield."
    )
    # options.add_argument(
    #     "--force-pkg", action="store_true", help="Force build a package."
    # )
    options.add_argument(
        "--force-all",
        action="store_true",
        help="Force build all dependencies and OpenMW.",
    )
    options.add_argument(
        "--force-all-tes3mp",
        action="store_true",
        help="Force build all dependencies and TES3MP.",
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
        "-i",
        "--make-install",
        action="store_true",
        help="Run 'make install' on OpenMW or TES3MP.",
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
    options.add_argument("-MP", "--tes3mp", action="store_true", help="Build TES3MP.")
    options.add_argument(
        "--tes3mp-server-only", action="store_true", help="Build TES3MP (server only.)"
    )
    options.add_argument(
        "--with-corescripts",
        action="store_true",
        help="Also clone down the CoreScripts repo.",
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
    build_mygui = False
    build_unshield = False
    force_bullet = False
    force_mygui = False
    force_openmw = False
    force_osg = False
    force_raknet = False
    force_tes3mp = False
    force_unshield = False
    # force_pkg = False
    install_prefix = INSTALL_PREFIX
    system_osg = False
    parsed = parse_argv()
    make_install = False
    out_dir = OUT_DIR
    patch = None
    pull = True
    skip_install_pkgs = False
    src_dir = SRC_DIR
    tes3mp = False
    tes3mp_serveronly = False
    verbose = False
    with_corescripts = False
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
        force_mygui = True
        force_openmw = True
        force_osg = True
        force_unshield = True
        # force_pkg = True
        emit_log("Force building all dependencies")
    if parsed.force_all_tes3mp:
        force_bullet = True
        force_mygui = True
        force_osg = True
        force_raknet = True
        force_tes3mp = True
        force_unshield = True
        # force_pkg = True
        emit_log("Force building all TES3MP dependencies")
    if parsed.system_bullet:
        system_bullet = True
        emit_log("Using the system LibBullet")
    if parsed.build_mygui:
        build_mygui = True
        emit_log("Building MyGUI")
    if parsed.build_unshield:
        build_unshield = True
        emit_log("Building Unshield")
    if parsed.force_bullet:
        force_bullet = True
        emit_log("Forcing build of LibBullet")
    if parsed.force_mygui:
        force_mygui = True
        emit_log("Forcing build of MyGUI")
    if parsed.force_openmw:
        force_openmw = True
        emit_log("Forcing build of OpenMW")
    if parsed.force_osg:
        force_osg = True
        emit_log("Forcing build of OSG")
    if parsed.force_raknet:
        force_raknet = True
        emit_log("Forcing build of Raknet")
    if parsed.force_tes3mp:
        force_tes3mp = True
        emit_log("Forcing build of TES3MP")
    if parsed.force_unshield:
        force_unshield = True
        emit_log("Forcing build of Unshield")
    # if parsed.force_pkg:
    #     force_pkg = True
    #     emit_log("Forcing build of package")
    if parsed.install_prefix:
        install_prefix = parsed.install_prefix
        emit_log("Using the install prefix: " + install_prefix)
    if parsed.jobs:
        cpus = parsed.jobs
        emit_log("'-j{}' will be used with make".format(cpus))
    if parsed.make_install:
        make_install = parsed.make_install
        emit_log("Make install will be ran")
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
        system_osg = False
        emit_log("The system OSG will be used.")
    if parsed.src_dir:
        src_dir = parsed.src_dir
        emit_log("Source directory set to: " + src_dir)
    if parsed.tes3mp:
        DEBIAN_PKGS.append("libluajit-5.1-dev")
        # TODO: redhat package
        UBUNTU_PKGS.append("libluajit-5.1-dev")
        VOID_PKGS.append("LuaJIT-devel")
        tes3mp = True
        emit_log("TES3MP build selected!")
    if parsed.tes3mp_server_only:
        DEBIAN_PKGS.append("libluajit-5.1-dev")
        # TODO: redhat package
        UBUNTU_PKGS.append("libluajit-5.1-dev")
        VOID_PKGS.append("LuaJIT-devel")
        tes3mp_serveronly = True
        emit_log("TES3MP server-only build selected")
    if parsed.verbose:
        verbose = parsed.verbose
        logging.getLogger().setLevel(logging.DEBUG)
        emit_log("Verbose output enabled")
    if parsed.with_corescripts:
        with_corescripts = True
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

    # This is a serious edge case, but let's
    # show a sane error when /opt doesn't exist.
    ensure_dir(os.path.join("/", "opt"))
    ensure_dir(install_prefix)
    ensure_dir(src_dir)

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
                "-DBUILD_SHARED_LIBS=on",
                "-DBULLET2_MULTITHREADING=on",
                "-DUSE_DOUBLE_PRECISION=on",
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
                install_prefix, "mygui", "lib", "libMyGUIEngine.so"
            ),
            cmake_args=[
                "-DMYGUI_BUILD_TOOLS=OFF",
                "-DMYGUI_RENDERSYSTEM=1",
                "-DMYGUI_BUILD_DEMOS=OFF",
                "-DMYGUI_BUILD_PLUGINS=OFF",
            ],
            cpus=cpus,
            force=force_mygui,
            git_url="https://github.com/MyGUI/mygui.git",
            install_prefix=install_prefix,
            src_dir=src_dir,
            verbose=verbose,
            version=MYGUI_VERSION,
        )

    if tes3mp or tes3mp_serveronly:

        build_library(
            "raknet",
            check_file=os.path.join(
                install_prefix, "src", "raknet", "build", "lib", "libRakNetLibStatic.a"
            ),
            cmake_args=[
                "-DRAKNET_ENABLE_DLL=OFF",
                "-DRAKNET_ENABLE_SAMPLES=OFF",
                "-DRAKNET_ENABLE_STATIC=ON",
                "-DRAKNET_GENERATE_INCLUDE_ONLY_DIR=ON",
            ],
            cpus=cpus,
            force=force_raknet,
            git_url="https://github.com/TES3MP/RakNet.git",
            install_prefix=install_prefix,
            make_install=False,  # Never ever make install this
            src_dir=src_dir,
            verbose=verbose,
            version=RAKNET_VERSION,
        )

        tes3mp_sha = get_repo_sha(
            src_dir, repo="tes3mp", rev=rev, pull=pull, verbose=verbose
        )

        if tes3mp_sha:
            tes3mp = "tes3mp-" + tes3mp_sha
        else:
            tes3mp = "tes3mp"
        build_env = os.environ.copy()
        # if system_osg:
        #     prefix_path = ""
        # else:
        #     prefix_path = "{0}/osg-openmw"
        prefix_path = ""

        if not system_bullet or force_bullet:
            prefix_path += ":{0}/bullet"
        if build_mygui or force_mygui:
            prefix_path += ":{0}/mygui"
        if build_unshield or force_unshield:
            prefix_path += ":{0}/unshield"

        prefix_path += ":{0}/src/raknet/build/lib"
        build_env["CMAKE_PREFIX_PATH"] = prefix_path.format(install_prefix)
        build_env["LDFLAGS"] = "-llzma -lz -lbz2"

        tes3mp_binary = "tes3mp"
        # TODO: a flag for enabling a debug build
        tes3mp_cmake_args = [
            "-Wno-dev",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DBUILD_OPENCS=OFF",
            "-DCMAKE_CXX_STANDARD=14",
            '-DCMAKE_CXX_FLAGS="-std=c++14"',
            "-DDESIRED_QT_VERSION=5",
            "-DRakNet_INCLUDES={}/raknet/include".format(SRC_DIR),
            "-DRakNet_LIBRARY_DEBUG={}/raknet/build/lib/libRakNetLibStatic.a".format(
                SRC_DIR
            ),
            "-DRakNet_LIBRARY_RELEASE={}/raknet/build/lib/libRakNetLibStatic.a".format(
                SRC_DIR
            ),
        ]

        if tes3mp_serveronly:
            # Link against the system Bullet and OSB
            tes3mp_binary = "tes3mp-server"
            server_args = [
                "-DBUILD_OPENMW_MP=ON",
                "-DBUILD_BROWSER=OFF",
                "-DBUILD_BSATOOL=OFF",
                "-DBUILD_ESMTOOL=OFF",
                "-DBUILD_ESSIMPORTER=OFF",
                "-DBUILD_LAUNCHER=OFF",
                "-DBUILD_MWINIIMPORTER=OFF",
                "-DBUILD_MYGUI_PLUGIN=OFF",
                "-DBUILD_OPENMW=OFF",
                "-DBUILD_WIZARD=OFF",
            ]
            for arg in server_args:
                tes3mp_cmake_args.append(arg)
        else:
            # Link against our built Bullet and OSB
            bullet = os.path.join(INSTALL_PREFIX, "bullet")
            if os.getenv("TES3MP_FORGE"):
                osg = "/usr/local"
                full_args = format_openmw_cmake_args(
                    bullet, osg, use_bullet=not system_bullet or force_bullet
                )

            tes3mp_cmake_args = [
                "-Wno-dev",
                "-DBUILD_OPENMW_MP=ON",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DBUILD_OPENCS=OFF",
                "-DCMAKE_CXX_STANDARD=14",
                '-DCMAKE_CXX_FLAGS="-std=c++14"',
                "-DDESIRED_QT_VERSION=5",
                "-DRakNet_INCLUDES={}/raknet/include".format(SRC_DIR),
                "-DRakNet_LIBRARY_DEBUG={}/raknet/build/lib/libRakNetLibStatic.a".format(
                    SRC_DIR
                ),
                "-DRakNet_LIBRARY_RELEASE={}/raknet/build/lib/libRakNetLibStatic.a".format(
                    SRC_DIR
                ),
            ]

        build_library(
            tes3mp,
            check_file=os.path.join(SRC_DIR, "tes3mp", "build", tes3mp_binary),
            cmake_args=tes3mp_cmake_args,
            clone_dest="tes3mp",
            cpus=cpus,
            env=build_env,
            force=force_tes3mp,
            git_url="https://github.com/TES3MP/openmw-tes3mp.git",
            install_prefix=install_prefix,
            make_install=make_install,
            patch=patch,
            src_dir=src_dir,
            verbose=verbose,
            # version=rev,
            # version="origin/0.7.0",
            version="abc4090a0fe1e0cc04cef598a598744d53f3ef6f",
        )

        tes3mp_sha = get_repo_sha(
            src_dir, repo="tes3mp", rev=rev, pull=pull, verbose=verbose
        )
        tes3mp = "-".join((tes3mp, tes3mp_sha))

        if make_install:
            os.chdir(install_prefix)
            if str(tes3mp_sha) not in tes3mp:
                os.rename("tes3mp", "tes3mp-{}".format(tes3mp_sha))
            if os.path.islink("tes3mp"):
                os.remove("tes3mp")
            os.symlink("tes3mp-" + tes3mp_sha, "tes3mp")

        if with_corescripts:
            scripts_dir = os.path.join(
                INSTALL_PREFIX, tes3mp, "etc", "openmw", "server"
            )
            tes3mp_etc_dir = os.path.join(INSTALL_PREFIX, tes3mp, "etc", "openmw")

            os.makedirs(tes3mp_etc_dir)
            os.chdir(tes3mp_etc_dir)
            execute_shell(
                ["git", "clone", "https://github.com/TES3MP/CoreScripts.git", "server"],
                verbose=verbose,
            )

            os.chdir("server")
            execute_shell(
                ["git", "checkout", TES3MP_CORESCRIPTS_VERSION], verbose=verbose
            )
            emit_log("Server core scripts installed at: " + scripts_dir)

            orig_cfg = []
            new_cfg = []
            os.chdir(tes3mp_etc_dir)
            with open("tes3mp-server-default.cfg", "r") as f:
                orig_cfg = f.readlines()

            for line in orig_cfg:
                if "home = ./server" in line:
                    new_cfg.append("home = " + scripts_dir + "\n")
                else:
                    new_cfg.append(line)

            with open("tes3mp-server-default.cfg", "w") as f:
                for line in new_cfg:
                    f.write(line)

    else:
        # OPENMW
        openmw_sha = get_repo_sha(src_dir, rev=rev, pull=pull, verbose=verbose)
        if openmw_sha:
            openmw = "openmw-{}".format(openmw_sha)
        else:
            # There's no sha yet since the source hasn't been cloned.
            openmw = "openmw"
        build_env = os.environ.copy()

        if system_osg:
            prefix_path = ""
        else:
            prefix_path = "{0}/osg-openmw"

        if not system_bullet or force_bullet:
            prefix_path += ":{0}/bullet"
        if build_mygui or force_mygui:
            prefix_path += ":{0}/mygui"
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

        if distro and "Ubuntu" in distro or "Debian" in distro:
            build_env["LDFLAGS"] = "-lz -lbz2"
        else:
            build_env["LDFLAGS"] = "-llzma -lz -lbz2"

        build_type = "Release"
        if with_debug:
            build_type = "Debug"

        build_args = [
            "-DBOOST_ROOT=/usr/include/boost",
            "-DCMAKE_BUILD_TYPE=" + build_type,
        ]

        # if build_upstream_osg:
        #     osg = os.path.join(INSTALL_PREFIX, "osg")
        if system_osg:
            osg = None
        else:
            osg = os.path.join(INSTALL_PREFIX, "osg-openmw")

        if not system_bullet or force_bullet:
            use_bullet = True
            bullet = os.path.join(INSTALL_PREFIX, "bullet")
        else:
            use_bullet = False
            bullet = ""

        full_args = build_args + format_openmw_cmake_args(
            bullet, osg, use_bullet=use_bullet
        )

        # Don't build the save importer..
        if not with_essimporter:
            full_args.append("-DBUILD_ESSIMPORTER=no")

        if without_cs:
            emit_log("NOT building the openmw-cs executable ...")
            full_args.append("-DBUILD_OPENCS=no")

        if without_iniimporter:
            emit_log("NOT building the openmw-iniimporter executable ...")
            full_args.append("-DBUILD_MWINIIMPORTER=no")

        if without_launcher:
            emit_log("NOT building the openmw-launcher executable ...")
            full_args.append("-DBUILD_LAUNCHER=no")

        if without_wizard:
            emit_log("NOT building the openmw-wizard executable ...")
            full_args.append("-DBUILD_WIZARD=no")

        if with_debug:
            full_args.append("-DOPENMW_LTO_BUILD=off")
        else:
            full_args.append("-DOPENMW_LTO_BUILD=on")

        build_library(
            openmw,
            check_file=os.path.join(install_prefix, openmw, "bin", "openmw"),
            cmake_args=full_args,
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
