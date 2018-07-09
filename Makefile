.DEFAULT_GOAL:= install

install:
	sudo ln -fs ${CURDIR}/build-openmw.py /usr/bin/build-openmw

image:
	sudo docker build -t build-openmw $(CURDIR)

tes3mp-package:
	sudo docker run --name build-openmw --rm -v $$HOME/backups/build-openmw:/opt build-openmw $(ARGS)
