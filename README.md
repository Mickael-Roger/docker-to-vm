# DTV for Dockerfile To VM

### *How to use Dockerfile to build a golden VM Image*

Because most of developpers use Dockerfile but unfortunatly it's not always the case for production environment, DTV tries to reconciliate theses two world by avoiding technological breakthrough.

Why making the job twice ? 

Developpers want to use Dockerfile and ops has to deploy the application inside a VM, so these use Ansible (Or Terraform, Chef, puppet, or wathever ...)

DTV is the solution. It takes a Dockerfile then generates a VM image (Openstack for now, but AWS, GCP, Azure, ... are in progress). This image is self-sufficient and respect the docker image name and tags


### *Principles*

### *Quick start*

### *Features*

### *Usage*
