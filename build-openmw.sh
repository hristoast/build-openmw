#!/bin/bash -e

# TODO: add updater script?
# https://wiki.openmw.org/index.php?title=Development_Environment_Setup

build_cpus=5
install_prefix=/opt/morrowind
source_dir=${HOME}/src

bullet3_version=2.86.1
ffmpeg_version=2.8.11
mygui_version=3.2.2
unshield_version=1.4.2

function error-and-die
{
    if ! [ -z "${1}" ]; then
        echo "${1}"
    fi
    exit 1
}

function help_text
{
    cat <<EOF

Usage: build-openmw [-h] [-J] [-N] [-s SHA] [-t TAG] [--with-mygui] [--with-unshield]

Build OpenMW!

Optional Arguments:
  -h, --help            Show this help message and exit
  -J, --just-openmw     Only package OpenMW
  -N, --no-tar          Don't package anything
  -s SHA, --sha SHA     Build the specified git revision (sha1)
  -t TAG, --tag TAG     Build the specified git tag
  --with-mygui          Build MyGUI and link against it
  --with-unshield       Build Unshield and link against it

EOF
    exit 1
}

function install-pkgs-centos
{
    echo CENTOS
    distro=centos
    exit 1
}

function install-pkgs-debian
{
    echo DEBIAN
    distro=debian
    sudo apt install -y --force-yes build-essential cmake git libboost-dev libboost-filesystem-dev libboost-program-options-dev libboost-system-dev libbz2-dev libfreetype6-dev libgl1-mesa-dev libopenal-dev libqt4-dev libsdl2-dev nasm zlib1g-dev
}

function install-pkgs-void
{
    echo VOID
    distro=void
    # TODO: need MUCH better error handling here... maybe check xbps-install's output
    sudo xbps-install -y boost-devel cmake freetype-devel gcc git libmygui-devel libopenal-devel libtxc_dxtn libunshield-devel libXt-devel make nasm ois-devel python-devel python3-devel qt-devel SDL2-devel zlib-devel \
        || echo "DIDN'T INSTALL PACKAGES -- DO WE EVEN NEED THEM??"
}

function install-pkgs
{
    if [ -f /etc/os-release ] && grep void /etc/os-release >/dev/null; then
        install-pkgs-void
    elif [ -f /etc/os-release ] && grep CentOS /etc/os-release >/dev/null; then
        install-pkgs-centos
    elif [ -f /etc/os-release ] && (grep Debian /etc/os-release >/dev/null || grep Devuan /etc/os-release >/dev/null); then
        install-pkgs-debian
    fi
}

function fix-libs
{
    # TODO: find out why this fails...
    # -- Installing: /opt/morrowind/openmw-cb32f1d60/share/games/openmw/resources/shaders/objects_vertex.glsl
    # -- Installing: /opt/morrowind/openmw-cb32f1d60/share/games/openmw/resources/shaders/parallax.glsl
    # -- Installing: /opt/morrowind/openmw-cb32f1d60/share/games/openmw/resources/shaders/water_nm.png
    # -- Installing: /opt/morrowind/openmw-cb32f1d60/share/games/openmw/resources/shaders/lighting.glsl
    # -- Installing: /opt/morrowind/openmw-cb32f1d60/share/games/openmw/resources/defaultfilters
    # -- Installing: /opt/morrowind/openmw-cb32f1d60/share/games/openmw/data
    # chmod: cannot access '/opt/morrowind/openmw-cb32f1d60/bin/*': No such file or directory
    sudo find ${install_prefix} -type d -exec chmod 0755 {} \; 2>/dev/null
    sudo find ${install_prefix} -type f -exec chmod 0644 {} \; 2>/dev/null
}

function build-ffmpeg2
{
    # TODO: --force-ffmpeg option to force rebuild?
    printf "Checking for ffmpeg... "
    if ! [ -f ${install_prefix}/ffmpeg-${ffmpeg_version}/bin/ffmpeg ]; then
        echo "NOT found!  building..."
        if ! [ -d ${source_dir}/FFmpeg ]; then
            cd ${source_dir}
            git clone https://github.com/FFmpeg/FFmpeg.git
        fi
        cd ${source_dir}/FFmpeg
        git checkout -- .
        git clean -df
        git checkout n${ffmpeg_version}
        ./configure --prefix=${install_prefix}/ffmpeg-${ffmpeg_version}
        make -j${build_cpus}
        sudo make install
        fix-libs
    else
        echo "FOUND!"
    fi
}

function build-osg-openmw
{
    printf "Checking for osg-openmw... "
    if ! [ -f ${install_prefix}/osg-openmw/lib64/libosg.so ]; then
        echo "NOT found!  building..."
        if ! [ -d ${source_dir}/osg-openmw ]; then
            cd ${source_dir}
            git clone https://github.com/OpenMW/osg.git osg-openmw
        fi
        [ -d ${source_dir}/osg-openmw/build ] && rm -rf ${source_dir}/osg-openmw/build
        mkdir -p ${source_dir}/osg-openmw/build
        cd ${source_dir}/osg-openmw/build
        git checkout -- ..
        git clean -df
        git pull  # we always want the bleeding edge for this one.
        cmake -D CMAKE_INSTALL_PREFIX=${install_prefix}/osg-openmw ..
        make -j${build_cpus}
        sudo make install
        fix-libs
    else
        echo "FOUND!"
    fi
}

function build-bullet
{
    printf "Checking for bullet... "
    if ! [ -f ${install_prefix}/bullet3-${bullet3_version}/lib/libLinearMath.a ]; then
        echo "NOT found!  building..."
        if ! [ -d ${source_dir}/bullet3 ]; then
            cd ${source_dir}
            git clone https://github.com/bulletphysics/bullet3.git
        fi
        mkdir -p ${source_dir}/bullet3/build
        cd ${source_dir}/bullet3/build
        git checkout -- ..
        git clean -df
        git checkout ${bullet3_version}
        cmake -D CMAKE_INSTALL_PREFIX=${install_prefix}/bullet3-${bullet3_version} \
              -D BUILD_CPU_DEMOS=false \
              -D BUILD_OPENGL3_DEMOS=false \
              -D BUILD_BULLET2_DEMOS=false \
              -D BUILD_UNIT_TESTS=false \
              ..
        make -j${build_cpus}
        sudo make install
        fix-libs
    else
        echo "FOUND!"
    fi
}

function build-unshield
{
    printf "Checking for unshield... "
    if ! [ -f ${install_prefix}/unshield-${unshield_version}/lib64/libunshield.so ]; then
        echo "NOT found!  building..."
        if ! [ -d ${source_dir}/unshield ]; then
            cd ${source_dir}
            git clone https://github.com/twogood/unshield.git
        fi
        [ -d ${source_dir}/unshield/build ] && rm -rf ${source_dir}/unshield/build
        mkdir -p ${source_dir}/unshield/build
        cd ${source_dir}/unshield/build
        git checkout -- ..
        git clean -df
        git checkout ${unshield_version}
        # cp ../../unshield/build/libunshield.pc /usr/local/lib/pkgconfig/
        cmake -D CMAKE_INSTALL_PREFIX=${install_prefix}/unshield-${unshield_version} ..
        make -j${build_cpus}
        sudo make install
        fix-libs
    else
        echo "FOUND!"
    fi
    sudo chmod 0755 ${install_prefix}/unshield-${unshield_version}/bin/*
}

function build-mygui
{
    printf "Checking for mygui... "
    if ! [ -f ${install_prefix}/mygui-${mygui_version}/lib/libMyGUIEngine.so ]; then
        echo "NOT found!  building..."
        if ! [ -d ${source_dir}/mygui ]; then
            cd ${source_dir}
            git clone https://github.com/MyGUI/mygui.git
        fi
        [ -d ${source_dir}/mygui/build ] && rm -rf ${source_dir}/mygui/build
        mkdir -p ${source_dir}/mygui/build
        cd ${source_dir}/mygui/build
        git checkout -- ..
        git clean -df
        git checkout MyGUI${mygui_version}
        cmake -D CMAKE_INSTALL_PREFIX=${install_prefix}/mygui-${mygui_version} \
              -D MYGUI_RENDERSYSTEM=1 \
              -D MYGUI_BUILD_DEMOS=OFF \
              -D MYGUI_BUILD_TOOLS=OFF \
              -D MYGUI_BUILD_PLUGINS=OFF \
              ..
        make -j${build_cpus}
        sudo make install
        fix-libs
    else
        echo "FOUND!"
    fi
}

function export-openmw-sha
{
    cd ${source_dir}/openmw
    export openmw_sha=$(git rev-parse HEAD)
    export openmw_sha_short=$(git rev-parse --short HEAD)
}

function build-openmw
{
    printf "Checking for openmw... "
    cd ${source_dir}/openmw
    git checkout master
    git checkout -- .
    git clean -df
    git pull --rebase
    if ! [ -z "${1}" ]; then
        git checkout "${1}"
    fi
    # Re-export the sha in case upstream changes have been pulled down
    export-openmw-sha
    if ! [ -f ${install_prefix}/openmw-${openmw_sha_short}/bin/openmw ]; then
        if ! [ -d ${source_dir}/openmw ]; then
            cd ${source_dir}
            git clone https://github.com/OpenMW/openmw.git
        fi
        if ! [ -d ${install_prefix}/openmw-${openmw_sha_short} ]; then
            echo "NOT found!  building..."
            ls -d ${install_prefix}/openmw-* &> /dev/null || code=$?; echo OK  # There are no current installs...
            [ -z ${code} ] && code=$?  # A current install was found...
            if [ ${code} -eq 0 ] && [ "${current_install}" != "openmw-${openmw_sha_short}" ]; then
                # We are building a new sha, so remove the old one
                current_install=$(ls -1d ${install_prefix}/openmw-* | awk -F/ '{ print $4 }' 2>/dev/null)
                sudo rm -rf /opt/morrowind/${current_install}
            fi
            [ -d ${source_dir}/openmw/build ] && rm -rf ${source_dir}/openmw/build
            mkdir -p ${source_dir}/openmw/build
            cd ${source_dir}/openmw/build
            if ${with_mygui} && ${with_unshield}; then
                export CMAKE_PREFIX_PATH=${install_prefix}/ffmpeg-${ffmpeg_version}:${install_prefix}/osg-openmw:${install_prefix}/unshield-${unshield_version}:${install_prefix}/mygui-${mygui_version}:${install_prefix}/bullet3-${bullet3_version}
            elif ${with_mygui}; then
                export CMAKE_PREFIX_PATH=${install_prefix}/ffmpeg-${ffmpeg_version}:${install_prefix}/osg-openmw:${install_prefix}/mygui-${mygui_version}:${install_prefix}/bullet3-${bullet3_version}
            elif ${with_unshield}; then
                export CMAKE_PREFIX_PATH=${install_prefix}/ffmpeg-${ffmpeg_version}:${install_prefix}/osg-openmw:${install_prefix}/unshield-${unshield_version}:${install_prefix}/bullet3-${bullet3_version}
            else
                export CMAKE_PREFIX_PATH=${install_prefix}/ffmpeg-${ffmpeg_version}:${install_prefix}/osg-openmw:${install_prefix}/bullet3-${bullet3_version}
            fi
            export LDFLAGS="-lz -lbz2"
            # -D CMAKE_BUILD_TYPE=Release ????
            cmake -D CMAKE_INSTALL_PREFIX=${install_prefix}/openmw-${openmw_sha_short} ..
            make -j${build_cpus}
            sudo make install
            fix-libs
            sudo sh -c "echo ${openmw_sha} > ${install_prefix}/openmw-${openmw_sha_short}/REVISION"
        else
            echo "FOUND!"
        fi
    else
        echo "FOUND!"
    fi
    if [ -h ${install_prefix}/openmw ]; then
        /bin/rm -f ${install_prefix}/openmw
    fi
    _user=$(whoami)
    sudo chown -R ${_user}: ${install_prefix}
    cd ${install_prefix}
    ln -s openmw-${openmw_sha_short} openmw
}

function make-bins-executable
{
    sudo chmod 0755 ${install_prefix}/ffmpeg-${ffmpeg_version}/bin/*
    sudo chmod 0755 ${install_prefix}/osg-openmw/bin/*
    sudo find ${install_prefix}/openmw-${openmw_sha_short}/bin -exec chmod 0755 {} \;
}

function tar-it-up
{
    version="${1}"
    filename=morrowind-${distro}-${version}.tar.bzip2
    printf "Creating ${filename} ... "
    cd /opt
    [ -f ${filename} ] && sudo rm -rf ${filename}
    sudo tar cjpf ${filename} morrowind
    sudo chown $(whoami): ${filename}
    sudo mv ${filename} ${HOME}/
    echo 'DONE!'
}

function tar-the-thing
{
    filename="${1}"
    [[ -z ${filename} ]] && error-and-die "Need to specify a file name for 'tar-the-thing'!"
    tarname=${filename}.tar.bzip2
    printf "Creating ${tarname} ... "
    cd ${install_prefix}
    [ -f ${tarname} ] && sudo rm -rf ${tarname}
    sudo tar cjpf ${tarname} ${filename}
    sudo chown $(whoami): ${tarname}
    sudo mv ${tarname} ${HOME}/
    echo 'DONE!'
}

function main
{
    just_openmw=false
    notar=false
    sha=false
    tag=false
    export with_mygui=false
    export with_unshield=false
    opts=$(getopt -o JNhs:t: --longoptions help,just-openmw,notar,sha:,tag:,with-mygui,with-unshield -n build-openmw -- "${@}")

    eval set -- "$opts"

    while true; do
        case "$1" in
            -h | --help ) help_text; shift;;
            -s | --sha ) sha=true; openmw_build_sha="$2"; shift; shift ;;
            -t | --tag ) tag=true; openmw_build_tag="$2"; shift; shift ;;
            # -L | --just-lib ) just_lib="${2}"; shift; shift ;;
            -J | --just-openmw ) just_openmw=true; shift ;;
            -N | --notar ) notar=true; shift ;;
            --with-mygui ) with_mygui=true; shift ;;
            --with-unshield ) with_unshield=true; shift ;;
            -- ) shift; break ;;
            * ) break ;;
        esac
    done

    mkdir -p ${source_dir}
    install-pkgs

    build-ffmpeg2
    build-osg-openmw
    build-bullet
    if ${with_mygui}; then
        echo WITH UNSHIELD ----------
        build-unshield
    fi
    if ${with_unshield}; then
        echo WITH MYGUI ----------
        build-mygui
    fi

    # First check for a tag
    if ${tag}; then
        version="${openmw_build_tag}"
        build-openmw "${openmw_build_tag}"
    # If there's no tag then build a sha
    elif ${sha}; then
        version="${openmw_build_sha}"
        build-openmw "${openmw_build_sha}"
    # No tag or sha specified; build master
    else
        export-openmw-sha
        build-openmw
        version="${openmw_sha_short}"
    fi

    make-bins-executable
    # Don't create any package
    if ${notar}; then
        echo 'No-tar option specified; not tarring!'
    # Only package OpenMW
    elif ${just_openmw}; then
        echo 'Just OpenMW option specified; packaging just that!'
        tar-the-thing openmw-${version}
    # Create the full runtime package
    else
        tar-it-up ${version}
    fi
}

main "${@}"
