FROM bastion

ADD toto /root/
ADD tt* /root/
ADD dd ff /usr/
ADD --chown=centos:centos toto /var/
ADD https://www.free.fr/index.html /home/centos/ 

ENV otot tutut
ENV gg 12345


ARG toto

ARG tutu=33444

ARG ggg=456

