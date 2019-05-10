import argparse
import dockerfile
import sys
import os
import time
import tempfile
import re
import wget
import glob

from pprint import pprint
from shutil import copyfile

# Openstack
from keystoneauth1 import loading
from keystoneauth1 import session
from glanceclient import Client
from novaclient import client

# SSH
import base64
import paramiko

class Systemd:

    #def generate_file : ! Generate and env at the beginning and at the end et get the difference + Get de CWD at the end of the script (Use a var DTV_CWD)

    def __init__(self):
        self.env = []
        self.entrypoint = None
        self.user = 'root'
        self.group = 'root'
        self.workdir = ''
        self.entrypoint = ""
        self.cmd = ""




class Cloud:

    def os_build_vm(self, os_image):

        if os.getenv('OS_REGION_NAME') is None:
            nova = client.Client('2', session=self.cloud_sess)
        else:
            nova = client.Client('2', session=self.cloud_sess, region_name=os.getenv('OS_REGION_NAME'))

        # Look for the asked flavor id in nova
        print("Try to find openstack flavor id %s ... " % (args.flavor), end=" ")
        found = 0
        for flavor in nova.flavors.list():
            if flavor.name == args.flavor:
                found = 1
                break
    
        if found == 0:
            raise Exception("ko : Flavor %s does not exist" % (args.flavor))
        else:
            print("done")

        # Create a temporary keypair to connect to the instance
        print("Try to create a temporary keypair ... ", end =" ")
        try:
            nova.keypairs.delete(key='temp_docker')         # In case a previously build failed without deleting the keypair
        except:
            pass
        
        keypair = nova.keypairs.create(name='temp_docker')
        self.ssh_key = keypair.private_key

        print("done")


        # Temporary instance creation
        print("Try to create instance ... ", end =" ")
        sys.stdout.flush()

            # Get image ID
        image = nova.glance.find_image('in:"' + os_image + '"')
        os_image_id = image.id

            # Get flavor-id
        for flavor in nova.flavors.list():
            if flavor.name == args.flavor:
                os_flavor_id = flavor.id
                break

            # Get Network name
        network_id = nova.neutron.find_network(args.network)

            # Instance creation
        try:
            my_server = nova.servers.create( name=args.tag, image=os_image_id, flavor=os_flavor_id, nics = [{'net-id':network_id.id}], key_name='temp_docker' )
        except:
            raise Exception("ko : Could not create the instance")

        print("done")

        # Wait until instance is up and running
        print("Wait for the instance to be up and running ... ", end =" ")
        sys.stdout.flush()

        server = nova.servers.find(id=my_server.id)
        while server.status != 'ACTIVE':
            time.sleep(10)
            server = nova.servers.find(id=my_server.id)

        time.sleep(30)                                     #  TODO Wait sshd is really up and running. 

        print("done")

        # Get ip address of the instance
        print("Get ip adress ... ", end =" ")
        for addr in server.addresses[args.network]:
            if addr['version'] == 4:
                my_address = addr['addr']
                break

        self.ip = my_address
        print("done : IPv4 is %s" % (self.ip))

    def ssh_init(self):
        # Create the private key file
        f = open(self.tempdir.name + "/.keyfile", "w")
        f.write(self.ssh_key)
        f.close()
        os.chmod(self.tempdir.name + "/.keyfile", 0o400)

        try:
            # Create SSH connexion
            client = paramiko.SSHClient()
            #client.get_host_keys().add(self.ip, 'ssh-rsa', key)
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.ip, username=args.user, key_filename=self.tempdir.name + '/.keyfile')
            ftp_client = client.open_sftp()
        except:
            raise Exception("ko")
        
        # Delete private keyfile
        copyfile(self.tempdir.name + "/.keyfile", '/tmp/my_key')            # For debug only
        os.remove(self.tempdir.name + "/.keyfile")

        return client, ftp_client


    def create_vm(self, image):

        if args.provider == 'openstack':
            self.os_build_vm(image)
        
        # Create ssh cxion
        print("Create ssh and scp connection to instance ... ", end=" ")
        self.ssh, self.scp = self.ssh_init()
        print("ok")



    def __init__(self, provider):

        self.ip = None
        self.ssh = None
        self.scp = None
        self.images = []
        self.provider = provider
        self.cloud_sess = None
        self.ssh_key = None
        self.tempdir = None
        self.buildfile = None

        if provider == 'openstack':

            # Initiate the connection
            print("Connecting to Openstack ... ", end=" ")
            try:
                loader = loading.get_plugin_loader('password')
                auth = loader.load_from_options(auth_url=os.getenv('OS_AUTH_URL'),
                                                username=os.getenv('OS_USERNAME'),
                                                password=os.getenv('OS_PASSWORD'),
                                                project_id=os.getenv('OS_TENANT_ID'),
                                                user_domain_name=os.getenv('OS_USER_DOMAIN_NAME'))
                self.cloud_sess = session.Session(auth=auth)
            except:
                print("error")
                print("Could not connect to your openstack. Be sure to have all theses environment vars set : ")
                print("  OS_AUTH_URL ")
                print("  OS_USERNAME ")
                print("  OS_PASSWORD ")
                print("  OS_TENANT_ID ")
                print("  OS_USER_DOMAIN_NAME ")
                print("  (Optional) OS_REGION_NAME ")
                sys.exit(1)

            print("done")

            # List all available images
            print("Gathering images list ... ", end=" ")

            if os.getenv('OS_REGION_NAME') is None:
                glance = Client('2', session=self.cloud_sess)
            else:
                glance = Client('2', session=self.cloud_sess, region_name=os.getenv('OS_REGION_NAME'))

            for image in glance.images.list():
                self.images.append(image.name)
            
            print("done - Found %d images" % (len(self.images)))

        elif provider == 'aws':
            sys.exit('AWS not implemented yet! Coming soon')
        elif provider == 'gcp':
            sys.exit('Google cloud not implemented yet! Coming soon')
        elif provider == 'azure':
            sys.exit('Azure cloud not implemented yet! Coming soon')
        else:
            raise Exception('Unknown cloud provider')

        self.tempdir = tempfile.TemporaryDirectory()
        os.mkdir(self.tempdir.name + '/download')
        self.buildfile = open(self.tempdir.name + "/build.sh", "w")
        self.buildfile.write("#!/bin/bash\n\n")
        self.buildfile.write("cd\n\n")
        self.buildfile.write("set > /tmp/dtv-init.start\n\n")


def send_file(src, dest, user, grp):
    file_name = os.path.basename(src)
    dir_name = os.path.dirname(src)
    send_cmd("sudo mkdir -p /tmp/dtv-file/" + dir_name)
    send_cmd("sudo chmod -R ugo+rwX /tmp/dtv-file")
    my_cloud.scp.put(src, '/tmp/dtv-file/' + src)

    my_cloud.buildfile.write("cp -rf /tmp/dtv-file/" + src + " " + dest)

    if user is not None:
        send_cmd("sudo chown " + user + ":" + grp + " " + dest)

def send_cmd(cmd):
    try:
        my_cloud.ssh.exec_command(cmd)
    except:
        raise Exception("ko : Could not execute %s" % (cmd))



# Done  !!! First copy in a temporary directory in the server, then add a copy command to the build.sh
def func_add( docker_cmd ):


    remote = re.compile('http://|https://|ftp://')

    dest_dir = my_systemd.workdir + docker_cmd.value[-1]

    if not dest_dir.endswith("/"):
        dest_dir = dest_dir + '/'

    for i in range(0,len(docker_cmd.value)-1):  # Doesn't work with ["file1", ...]
   
        ref_src = docker_cmd.value[i]

        if remote.match(ref_src):
            ref_src = wget.download(ref_src, my_cloud.tempdir.name + '/download/' )

        src_files = glob.glob(ref_src)

        for src_file in src_files:
            file_name = os.path.basename(src_file)
            dest_file = dest_dir + file_name
        
            if docker_cmd.flags:
                    splitted_flags = re.split(r'\W+', docker_cmd.flags[0])
                    file_user = splitted_flags[2]
                    file_group = splitted_flags[3]
                    send_file(src_file, dest_file, file_user, file_group)
            else:
                    send_file(src_file, dest_file, None, None)

        # Clean download directory
        files = glob.glob(my_cloud.tempdir.name + '/download/*')
        for f in files:
            os.remove(f)

# Done
def func_arg( docker_cmd ):

    my_val = []

    # Set default value "" if not set or the value itself
    for value in docker_cmd.value:
        if re.search("=", value):
            my_val = re.split("=", value)
        else:
            my_val.append(value)
            my_val.append("")

        # If it is in the args then change the value
        if args.arguments is not None:
            searched_value = re.compile(my_val[0] + '=')
            for argument in args.arguments:
                if searched_value.match(argument):
                    val_start = searched_value.match(argument).end()
                    my_val[1] = argument[val_start:]

    # Set env vars in docker_run.sh
    my_cloud.buildfile.write("export " + my_val[0] + '=' + my_val[1] + "\n\n")

    # Append env to my_systemd.env
    my_systemd.env.append((my_val[0],my_val[1]))

                

# Done
def func_copy( docker_cmd ):
    func_add( docker_cmd )

# TODO
def func_entrypoint( docker_cmd ):
    print("entrypoint")

# Done
def func_env( docker_cmd ):

    # Set env vars in docker_run.sh
    my_cloud.buildfile.write("export " + docker_cmd.value[0] + '=' + docker_cmd.value[1] + "\n\n")

    # Append env to my_systemd.env
    my_systemd.env.append((docker_cmd.value[0],docker_cmd.value[1]))


# Done
def func_from( docker_cmd ):
    
    os_image = docker_cmd.value[0]

    if os_image not in my_cloud.images:
        raise Exception("Base image %s not found" % (os_image))

    my_cloud.create_vm(os_image)

# TODO
def func_healthcheck( docker_cmd ):
    print("healthcheck")                # Has to be had to crontab and execute restart on the service

# Done
def func_label( docker_cmd ):
    print("Labels not implemented yet")

# Done
def func_maintainer( docker_cmd ):
    print("Maintainer is %s" % (docker_cmd.value))

# TODO
def func_onbuild( docker_cmd ):
    print("Onbuild not implemented yet")        # A script somewhere

# Done TO TEST
def func_run( docker_cmd ):
    my_cloud.buildfile.write(docker_cmd.value[0] + "\n\n")
    return

# Done
def func_shell( docker_cmd ):
    func_run( docker_cmd )                          # Sorry Windows !!!

# Done
def func_stopsignal( docker_cmd ):
    print("Do you really need to specify a specific signal when you use systemd ?")

# Done TO TEST
def func_user( docker_cmd ):
    my_cloud.buildfile.write("sudo su " + docker_cmd.value[0] + "\n\n")
    return

# Done
def func_cmd( docker_cmd ):
    my_systemd.cmd = docker_cmd.value[0]
    return

# Done
def func_expose( docker_cmd ):
    print("No needed while firewalld is not implemented in the source os image. Please use security group instead")

# Done
def func_volume( docker_cmd ):
    return

# Done TO TEST
def func_workdir( docker_cmd ):
    my_cloud.buildfile.write("cd " + docker_cmd.value[0] + "\n\n")
    return

# Done
def execute_dockercmd( dockercmd ):
    "For each Dockerfile command, execute/generate the equivalent in an VM"

    switcher = {
        'add': func_add,
        'arg': func_arg,
        'copy': func_copy,
        'entrypoint': func_entrypoint,
        'env': func_env,
        'from': func_from,
        'healthcheck': func_healthcheck,
        'label': func_label,
        'maintainer': func_maintainer,
        'onbuild': func_onbuild,
        'run': func_run,
        'shell': func_shell,
        'stopsignal': func_stopsignal,
        'user': func_user,
        'volume': func_volume,
        'expose': func_expose,
        'cmd': func_cmd,
        'workdir': func_workdir
    }

    func = switcher.get(dockercmd.cmd, lambda: "Invalid Docker command")
    func(dockercmd)


if __name__ == "__main__":

    # Check arguments

    parser = argparse.ArgumentParser( description='Build a cloud image from de dockerfile' )

    parser.add_argument('--provider', '-p', required=True, choices=('openstack', 'aws', 'gcp', 'azure'), help='Cloud provider : openstack, aws, gcp, azure')
    parser.add_argument('--dockerfile', '-f', required=True, help='Dockerfile to use')
    parser.add_argument('--tag', '-t', required=True, help='Tag of the image. ex: tomcat:1.0')
    parser.add_argument('--flavor', '-s', required=True, help='Instance flavor tu use')
    parser.add_argument('--user', '-u', required=True, help='Flavor default user. For ex: centos for CentOS / ec2-user for aws Linux, ...')
    parser.add_argument('--arguments', '-a', nargs='*', required=False, help='Args passed to the docker build in the form : <varname>=<value> <varname1>=<value2> ...')
    parser.add_argument('--network', '-n', required=False, help='For Openstack only : External network name to use')


    args = parser.parse_args()

    if args.provider == 'openstack' and (args.network is None):
        parser.error("--provider=openstack requires --network=NET_NAME")


    # Create the cloud object. This is where cloud session is initialized
    my_cloud = Cloud(args.provider)

    # Create systemd object
    my_systemd = Systemd()

    # For each line in the Dockerfile execute the correspondant operation on the instance
    for elem in dockerfile.parse_file(args.dockerfile):
        execute_dockercmd(elem)


    my_cloud.buildfile.write("pwd > /tmp/dtv-cwd\n\n")
    my_cloud.buildfile.write("set > /tmp/dtv-init.end\n\n")

    my_cloud.buildfile.close()

    send_cmd("chmod +x /root/build.sh")

    my_cloud.scp.put(my_cloud.tempdir.name + "/build.sh", "/tmp/build.sh")
    send_cmd("sudo mv /tmp/build.sh /root/build.sh")
    send_cmd("sudo chmod +x /root/build.sh")
    send_cmd("sudo /root/build.sh")

    send_cmd("sudo sdiff /tmp/dtv-init.start /tmp/dtv-init.end | grep '  >' | awk {' print $2 '} > /tmp/new_env")
    send_cmd("sudo chmod 666 /tmp/new_env /tmp/dtv-cwd")

    my_cloud.scp.get('/tmp/new_env','./new_env')
    my_cloud.scp.get('/tmp/dtv-cwd','./dtv-cwd')

    print("Next is coming ...")


    # Generate the systemd file
    # Install and enable systemd

    # Make a glance image

    # TODO later : Generate the onbuild file + Generate the script file used when this image is used as FROM