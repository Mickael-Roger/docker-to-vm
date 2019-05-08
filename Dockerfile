FROM bastion

ADD toto /tmp/
ADD tt* /tmp/
ADD dd ff /tmp/
ADD --chown=user:grp toto /tmp/
ADD --chown=user:grp toto* /tmp/
ADD ["toto", "/tmp"/]
ADD ["tot o", "/tmp"/]
ADD --chown=user:grp ["tot o", "/tmp"/]
ADD https://www.free.fr/index.html fff 

