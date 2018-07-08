FROM grimkriegor/tes3mp-forge

RUN apt-get update && apt-get install -y --force-yes lsb-release python3

ADD build-openmw.py /root/

ENV TES3MP_FORGE true

ENTRYPOINT /root/build-openmw.py --skip-install-pkgs --force-pkg --make-pkg --tes3mp --verbose --branch 0.6.3 --out /opt
