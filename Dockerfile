FROM debian:9.8-slim

RUN apt-get update && apt-get install -y --force-yes lsb-release python3 git libopenal-dev libsdl2-dev qt5-default libfreetype6-dev libboost-filesystem-dev libboost-thread-dev libboost-program-options-dev libboost-system-dev libavcodec-dev libavformat-dev libavutil-dev libswscale-dev cmake build-essential libqt5opengl5-dev liblzma-dev libbz2-dev libluajit-5.1-dev libopenscenegraph-3.4-dev

ADD build-openmw.py /root/

ENTRYPOINT [ "/root/build-openmw.py", "--make-pkg", "--skip-install-pkgs", "--tes3mp", "--tes3mp-server-only", "--verbose", "--sha", "292536439eeda58becdb7e441fe2e61ebb74529e", "--out", "/opt" ]
