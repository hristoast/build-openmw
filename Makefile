.DEFAULT_GOAL:= install

install:
	sudo ln -fs ${CURDIR}/build-openmw.py /usr/bin/build-openmw
