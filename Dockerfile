FROM debian:10.3-slim

RUN apt-get update && apt-get install -y --force-yes lsb-release python3 cmake git libopenal-dev libbullet-dev libsdl2-dev qt5-default libfreetype6-dev libavcodec-dev libavformat-dev libavutil-dev libswscale-dev cmake build-essential libqt5opengl5-dev libunshield-dev libmygui-dev libbullet-dev libboost-filesystem1.67-dev libboost1.67-dev libboost-thread1.67-dev libboost-program-options1.67-dev libboost-system1.67-dev libboost-iostreams1.67-dev libbz2-dev

ADD build-openmw.py /root/

ENTRYPOINT [ "/root/build-openmw.py", "--skip-install-pkgs", "--verbose" ]
