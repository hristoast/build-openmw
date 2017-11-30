#!/usr/bin/env python3
import argparse
import datetime
import logging
import os
import shutil
import subprocess
import sys

BULLET_VERSION = "2.86.1"
FFMPEG_VERSION = "n2.8.13"
MYGUI_VERSION = "3.2.2"
UNSHIELD_VERSION = "1.4.2"

CPUS = os.cpu_count() + 1
INSTALL_PREFIX = os.path.join("/", "opt", "morrowind")
DESC = "Build OpenMW for your system, install it all to {}.  Also builds OSG, libBullet, Unshield, and MyGUI, and links against those builds.".format(INSTALL_PREFIX)
LOGFMT = '|-> %(message)s'
OUT_DIR = os.getenv("HOME")
SRC_DIR = os.path.join(INSTALL_PREFIX, "src")

DEBIAN_PKGS = "git libopenal-dev libsdl2-dev libqt4-dev libboost-filesystem-dev libboost-thread-dev libboost-program-options-dev libboost-system-dev libavcodec-dev libavformat-dev libavutil-dev libswscale-dev libswresample-dev libbullet-dev libmygui-dev libunshield-dev cmake build-essential libqt4-opengl-dev".split()
REDHAT_PKGS = "openal-devel SDL2-devel qt4-devel boost-filesystem git boost-thread boost-program-options boost-system ffmpeg-devel ffmpeg-libs bullet-devel gcc-c++ mygui-devel unshield-devel tinyxml-devel cmake".split()
UBUNTU_PKGS = DEBIAN_PKGS
VOID_PKGS = "boost-devel cmake ffmpeg-devel freetype-devel gcc git libavformat libavutil libmygui-devel libopenal-devel libopenjpeg2-devel libswresample libswscale libtxc_dxtn liblzma-devel libXt-devel make nasm ois-devel python-devel python3-devel qt-devel SDL2-devel zlib-devel".split()

PROG = 'build-openmw'
VERSION = "1.1"


def emit_log(msg: str, level=logging.INFO, quiet=False, *args, **kwargs) -> None:
    """Logging wrapper."""
    if not quiet:
        if level == logging.DEBUG:
            logging.debug(msg, *args, **kwargs)
        elif level == logging.INFO:
            logging.info(msg, *args, **kwargs)
        elif level == logging.WARN:
            logging.warn(msg, *args, **kwargs)
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
                execute_shell(["sudo", "chown", '{}:'.format(os.getlogin()), path])[1]
            emit_log("{} now exists!".format(path))
        else:
            emit_log("Does {0} exist? {1}".format(path), os.path.isdir(path))
            return os.path.isdir(path)
    else:
        emit_log("{} exists!".format(path))


def error_and_die(msg: str) -> SystemExit:
    sys.stderr.write("ERROR: " + msg + " Exiting ..." + "\n")
    sys.exit(1)


def execute_shell(cli_args: list, env=None, verbose=False) -> tuple:
    """Small convenience wrapper around subprocess.Popen."""
    if verbose:
        p = subprocess.Popen(cli_args, env=env)
    else:
        p = subprocess.Popen(cli_args, stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE, env=env)
    c = p.communicate()
    return p.returncode, c


def build_library(libname, check_file=None, clone_dest=None, cmake=True,
                  cmake_args=None, cpus=None, env=None,
                  force=False, install_prefix=INSTALL_PREFIX, git_url=None,
                  quiet=False, src_dir=SRC_DIR, verbose=False, version='master'):

    def _cmake():
        emit_log("{} building with cmake!".format(libname))
        build_dir = os.path.join(src_dir, clone_dest, "build")
        if os.path.isdir(build_dir):
            shutil.rmtree(build_dir)
        os.mkdir(build_dir)
        os.chdir(build_dir)

        emit_log("{} running cmake ...".format(libname))
        build_cmd = ["cmake", "-DCMAKE_INSTALL_PREFIX={}/{}"
                     .format(install_prefix, libname)]
        if cmake_args:
            build_cmd += cmake_args
        build_cmd += ["..", ]
        exitcode, output = execute_shell(build_cmd, env=env, verbose=verbose)
        if exitcode != 0:
            emit_log(output[1])
            error_and_die("cmake exited nonzero!")

        emit_log("{} running make (this will take a while) ...".format(libname))
        exitcode, output = execute_shell(["make", "-j{}".format(cpus)],
                                         env=env, verbose=verbose)
        if exitcode != 0:
            emit_log(output[1])
            error_and_die("make exited nonzero!")

        emit_log("{} running make install ...".format(libname))
        out, err = execute_shell(["make", "install"],
                                 env=env, verbose=verbose)[1]
        if err:
            error_and_die(err.decode("utf-8"))

        emit_log("{} installed successfully!".format(libname))

    def _configure_make():
        emit_log("{} building with configure and make!".format(libname))

        emit_log("{} running make clean ...".format(libname))
        out, err = execute_shell(["make", "clean"], verbose=verbose)[1]
        # if err:
        #     error_and_die(err.decode("utf-8"))

        emit_log("{} running configure ...".format(libname))
        out, err = execute_shell(["./configure",
                                  "--prefix={0}/{1}".format(install_prefix,
                                                            libname)],
                                 verbose=verbose)[1]
        if err:
            error_and_die(err.decode("utf-8"))

        emit_log("{} running make (this will take a while) ...".format(libname))
        exitcode, output = execute_shell(["make", "-j{}".format(cpus)],
                                         verbose=verbose)
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
        emit_log("{} executing source clean!".format(libname))
        execute_shell(["git", "checkout", "--", "."], verbose=verbose)
        execute_shell(["git", "clean", "-df"], verbose=verbose)
        emit_log("{} resetting source to the desired rev ({rev})".format(
            libname, rev=version))
        execute_shell(["git", "checkout", version], verbose=verbose)
        execute_shell(["git", "reset", "--hard", "origin/{}".format(version)],
                      verbose=verbose)

    if not clone_dest:
        clone_dest = libname
    if os.path.exists(check_file) and os.path.isfile(check_file) and not force:
        emit_log("{} found!".format(libname))
    else:
        emit_log("{} building now ...".format(libname))
        if not os.path.exists(os.path.join(src_dir, clone_dest)):
            emit_log("{} source directory not found, cloning...".format(clone_dest))
            os.chdir(src_dir)
            execute_shell(["git", "clone", git_url, clone_dest], verbose=verbose)[1]
            if not os.path.exists(os.path.join(src_dir, libname)):
                error_and_die("Could not clone {} for some reason!".format(clone_dest))

        if force and os.path.exists(os.path.join(install_prefix, libname)):
            emit_log("{} forcing removal of previous install!".format(libname))
            shutil.rmtree(os.path.join(install_prefix, libname))

        _git_clean_src()

        os.chdir(os.path.join(src_dir, clone_dest))
        if cmake:
            _cmake()
        else:
            _configure_make()


def get_distro() -> tuple:
    """Try to run 'lsb_release -d' and return the output."""
    return execute_shell(["lsb_release", "-d"])[1]


def get_openmw_sha(src_dir: str, version: str, pull=True) -> str:
    try:
        os.chdir(os.path.join(src_dir, "openmw"))
    except FileNotFoundError:
        return False
    if pull:
        emit_log("Fetching latest sources ...")
        execute_shell(["git", "fetch", "--all"])[1][0]

    if '/' not in version:
        rev = "origin/{}".format(version)
    else:
        rev = "{}".format(version)

    execute_shell(["git", "checkout", rev])[1][0]
    execute_shell(["git", "reset", "--hard", rev])[1][0]

    out = execute_shell(["git", "rev-parse", "--short", "HEAD"])[1][0]
    return out.decode().strip()


def install_packages(distro: str, **kwargs) -> bool:
    quiet = kwargs.pop("quiet", "")

    emit_log("Attempting to install dependency packages, please enter your sudo password as needed...",
             quiet=quiet)
    if 'void' in distro.lower():
        emit_log("Distro detected as 'Void Linux'!")
        cmd = ["sudo", "xbps-install", "--yes"] + VOID_PKGS
        out, err = execute_shell(cmd)[1]
        msg = "Package installation completed!"
    elif 'debian' in distro.lower():
        emit_log("Distro detected as 'Debian'!")
        cmd = ["sudo", "apt-get", "install", "-y", "--allow-downgrades",
               "--allow-remove-essential", "--allow-change-held-packages"] + DEBIAN_PKGS
        out, err = execute_shell(cmd)[1]
        msg = "Package installation completed!"
    elif 'devuan' in distro.lower():
        emit_log("Distro detected as 'Devuan'!")
        # Debian packages should just work in this case.
        cmd = ["sudo", "apt-get", "install", "-y", "--force-yes"] + DEBIAN_PKGS
        out, err = execute_shell(cmd)[1]
        msg = "Package installation completed!"
    elif 'ubuntu' in distro.lower():
        emit_log("Distro detected as 'Ubuntu'!")
        cmd = ["sudo", "apt-get", "install", "-y", "--allow-downgrades",
               "--allow-remove-essential", "--allow-change-held-packages"] + UBUNTU_PKGS
        out, err = execute_shell(cmd)[1]
        msg = "Package installation completed!"
    elif 'fedora' in distro.lower():
        emit_log("Distro detected as 'Fedora'!")
        cmd = ["sudo", "dnf", "groupinstall", "-y", "development-tools"]
        out, err = execute_shell(cmd)[1]
        cmd = ["sudo", "dnf", "install", "-y"] + REDHAT_PKGS
        out, err = execute_shell(cmd)[1]
        msg = "Package installation completed!"
    else:
        error_and_die("Your OS is not yet supported!  If you think you know what you are doing, you can use '-S' to continue anyways.")

    emit_log(msg)
    return out, err


def parse_argv(_argv: list) -> None:
    """Set up args ('_argv', a list) and parse them."""
    parser = argparse.ArgumentParser(description=DESC, prog=PROG)
    parser.add_argument("--version", action="version", version=VERSION, help=argparse.SUPPRESS)
    options = parser.add_argument_group("Options")
    options.add_argument("--force-bullet", action="store_true", help="Force build LibBullet.")
    options.add_argument("--force-ffmpeg", action="store_true", help="Force build FFMpeg.")
    options.add_argument("--force-mygui", action="store_true", help="Force build MyGUI.")
    options.add_argument("--force-openmw", action="store_true", help="Force build OpenMW.")
    options.add_argument("--force-osg", action="store_true", help="Force build OSG.")
    options.add_argument("--force-unshield", action="store_true", help="Force build Unshield.")
    options.add_argument("--force-all", action="store_true", help="Force build all dependencies and OpenMW.")
    options.add_argument("--install-prefix", help="Set the install prefix. Default: {}".format(INSTALL_PREFIX))
    options.add_argument("-r", "--rev", "--sha", "--tag",
                         help="The git revision of OpenMW to build.  This can be any valid git rev object.")
    options.add_argument("-j", "--jobs",
                         help="How many cores to use with make.  Default: {}".format(CPUS))
    options.add_argument("-J", "--just-openmw", action="store_true",
                         help="If packaging, include just OpenMW.")
    options.add_argument("-N", "--no-pull", action="store_true",
                         help="Don't do a 'git fetch --all' on the OpenMW sources.")
    options.add_argument("-n", "--no-pkg", "--no-tar", action="store_true",
                         help="Don't create a package.")
    options.add_argument("-o", "--out", metavar="DIR",
                         help="Where to write the package to.  Default: {}".format(OUT_DIR))
    options.add_argument("-S", "--skip-install-pkgs", action="store_true",
                         help="Don't try to install dependencies.")
    options.add_argument("--src-dir", help="Set the source directory. Default: {}".format(SRC_DIR))
    options.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")

    return parser.parse_args()


def main() -> None:
    # TODO: option to skip a given dependency?
    logging.basicConfig(format=LOGFMT, level=logging.INFO, stream=sys.stdout)
    start = datetime.datetime.now()
    emit_log("BEGIN {0} run at {1}".format(
        PROG, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    cpus = CPUS
    distro = None
    force_bullet = False
    force_ffmpeg = False
    force_mygui = False
    force_openmw = False
    force_osg = False
    force_unshield = False
    install_prefix = INSTALL_PREFIX
    parsed = parse_argv(sys.argv[1:])
    rev = "master"
    just_openmw = False
    no_pkg = False
    out_dir = OUT_DIR
    pull = True
    skip_install_pkgs = False
    src_dir = SRC_DIR
    verbose = False

    if parsed.force_all:
        force_bullet = True
        force_ffmpeg = True
        force_mygui = True
        force_openmw = True
        force_osg = True
        force_unshield = True
        emit_log("Force building all dependencies!")
    if parsed.force_bullet:
        force_bullet = True
        emit_log("Forcing build of LibBullet!")
    if parsed.force_ffmpeg:
        force_ffmpeg = True
        emit_log("Forcing build of FFMPEG!")
    if parsed.force_mygui:
        force_mygui = True
        emit_log("Forcing build of MyGUI!")
    if parsed.force_openmw:
        force_openmw = True
        emit_log("Forcing build of OpenMW!")
    if parsed.force_osg:
        force_osg = True
        emit_log("Forcing build of OSG!")
    if parsed.force_unshield:
        force_unshield = True
        emit_log("Forcing build of Unshield!")
    if parsed.install_prefix:
        install_prefix = parsed.install_prefix
        emit_log("Using the install prefix: {}".format(install_prefix))
    if parsed.rev:
        rev = parsed.rev
        emit_log("Rev specified: {}".format(rev))
    if parsed.jobs:
        cpus = parsed.jobs
        emit_log("'-j{}' will be used with make!".format(cpus))
    if parsed.just_openmw:
        just_openmw = parsed.just_openmw
        emit_log(just_openmw, level=logging.DEBUG)  # TODO: remove this
        emit_log("Just OpenMW enabled!")
    if parsed.no_pkg:
        no_pkg = parsed.no_pkg
        emit_log(no_pkg, level=logging.DEBUG)  # TODO: remove this
        emit_log("No package will be made!")
    if parsed.no_pull:
        pull = False
        emit_log("git fetch will not be ran!")
    if parsed.out:
        out_dir = parsed.out
        emit_log("Out dir set to: {}".format(out_dir))
    if parsed.skip_install_pkgs:
        skip_install_pkgs = parsed.skip_install_pkgs
        emit_log("Package installs will be skipped!")
    if parsed.src_dir:
        src_dir = parsed.src_dir
        emit_log("Source directory set to: {}".format(src_dir))
    if parsed.verbose:
        verbose = parsed.verbose
        emit_log("Verbose output enabled!")

    openmw_sha = get_openmw_sha(src_dir, rev, pull=pull)

    try:
        out, err = get_distro()
    except FileNotFoundError:
        error_and_die("Unable to determine your distro to install dependencies!  Try again and use '-S' if you know what you are doing.")
    if err:
        error_and_die(err.decode())
    else:
        distro = out.decode().split(":")[1].strip()

    if not skip_install_pkgs:
        out, err = install_packages(distro)
        if err:
            error_and_die(err.decode())

    ensure_dir(install_prefix)
    ensure_dir(src_dir)

    # FFMPEG
    build_library("ffmpeg",
                  check_file=os.path.join(install_prefix, "ffmpeg", "bin", "ffmpeg"),
                  cmake=False,
                  cpus=cpus,
                  force=force_ffmpeg,
                  git_url='https://github.com/FFmpeg/FFmpeg.git',
                  install_prefix=install_prefix,
                  src_dir=src_dir,
                  verbose=verbose,
                  version=FFMPEG_VERSION)

    # OSG-OPENMW
    build_library("osg-openmw",
                  check_file=os.path.join(install_prefix, "osg-openmw", "lib64", "libosg.so"),
                  cmake_args=["-DBUILD_OSG_PLUGINS_BY_DEFAULT=0", "-DBUILD_OSG_PLUGIN_OSG=1",
                              "-DBUILD_OSG_PLUGIN_DDS=1", "-DBUILD_OSG_PLUGIN_TGA=1",
                              "-DBUILD_OSG_PLUGIN_BMP=1", "-DBUILD_OSG_PLUGIN_JPEG=1",
                              "-DBUILD_OSG_PLUGIN_PNG=1", "-DBUILD_OSG_DEPRECATED_SERIALIZERS=0"],
                  cpus=cpus,
                  force=force_osg,
                  git_url='https://github.com/OpenMW/osg.git',
                  install_prefix=install_prefix,
                  src_dir=src_dir,
                  verbose=verbose)

    # BULLET
    build_library("bullet",
                  check_file=os.path.join(install_prefix, "bullet", "lib", "libLinearMath.so"),
                  cmake_args=["-DBUILD_CPU_DEMOS=false", "-DBUILD_OPENGL3_DEMOS=false",
                              "-DBUILD_BULLET2_DEMOS=false", "-DBUILD_UNIT_TESTS=false",
                              "-DINSTALL_LIBS=on", "-DBUILD_SHARED_LIBS=on"],
                  cpus=cpus,
                  force=force_bullet,
                  git_url='https://github.com/bulletphysics/bullet3.git',
                  install_prefix=install_prefix,
                  src_dir=src_dir,
                  verbose=verbose,
                  version=BULLET_VERSION)

    # UNSHIELD
    build_library("unshield",
                  check_file=os.path.join(install_prefix, "unshield", "lib64", "libunshield.so"),
                  cpus=cpus,
                  force=force_unshield,
                  git_url='https://github.com/twogood/unshield.git',
                  install_prefix=install_prefix,
                  src_dir=src_dir,
                  verbose=verbose,
                  version=UNSHIELD_VERSION)

    # MYGUI
    build_library("mygui",
                  check_file=os.path.join(install_prefix, "mygui", "lib", "libMyGUIEngine.so"),
                  cmake_args=["-DMYGUI_BUILD_TOOLS=OFF", "-DMYGUI_RENDERSYSTEM=1",
                              "-DMYGUI_BUILD_DEMOS=OFF", "-DMYGUI_BUILD_PLUGINS=OFF"],
                  cpus=cpus,
                  force=force_mygui,
                  git_url='https://github.com/MyGUI/mygui.git',
                  install_prefix=install_prefix,
                  src_dir=src_dir,
                  verbose=verbose,
                  version=MYGUI_VERSION)

    # OPENMW
    if openmw_sha:
        openmw = "openmw-{}".format(openmw_sha)
    else:
        # There's no sha yet since the source hasn't been cloned.
        openmw = "openmw"
    build_env = os.environ.copy()
    build_env["CMAKE_PREFIX_PATH"] = "{0}/ffmpeg:{0}/osg-openmw:{0}/unshield:{0}/mygui:{0}/bullet".format(
        install_prefix)
    build_env["LDFLAGS"] = "-llzma -lz -lbz2"
    build_library(openmw,
                  check_file=os.path.join(install_prefix, openmw, "bin", "openmw"),
                  clone_dest="openmw",
                  cpus=cpus,
                  env=build_env,
                  force=force_openmw,
                  git_url='https://github.com/OpenMW/openmw.git',
                  install_prefix=install_prefix,
                  src_dir=src_dir,
                  verbose=verbose,
                  version=rev)
    os.chdir(install_prefix)
    # Don't fetch updates since new ones might exist
    openmw_sha = get_openmw_sha(src_dir, rev, pull=False)
    if str(openmw_sha) not in openmw:
        os.chdir(install_prefix)
        os.rename("openmw", "openmw-{}".format(openmw_sha))
    if os.path.islink("openmw"):
        os.remove("openmw")
    os.symlink("openmw-{}".format(openmw_sha), "openmw")

    # TODO: Create tar file
    # ⌜
    # ∟
    emit_log("END {0} run at {1}".format(
        PROG, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    end = datetime.datetime.now()
    duration = end - start
    minutes = int(duration.total_seconds() // 60)
    seconds = int(duration.total_seconds() % 60)
    emit_log("Took {m} minutes, {s} seconds.".format(m=minutes, s=seconds))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        error_and_die("Ctrl-c recieved!")
