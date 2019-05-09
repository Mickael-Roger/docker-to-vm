FROM bastion

ADD toto /root/
ADD tt* /root/
ADD dd ff /usr/
ADD --chown=centos:centos toto /var/
ADD https://www.free.fr/index.html /home/centos/ 

