#!/usr/bin/python
#
# Probe for extracting storage information from 
# XenServer. 
#   by Emir Imamagic (eimamagi@srce.hr)
#
# The following info is extracted:
#   vbd_xvda_size - total size of VDIs (B)
#   sr_size_Local_storage - total size of SR (B)
#   sr_virt_alloc_Local_storage - allocated space on SR (B)
#
# Data is stored to <filename> in zabbix_sender 
# friendly format:
#   hostname metric value
#   vmname metric value
#   ...
#
# If the parameter vmfilename is defined VM date
# will be stored into vmfilename instead of filename.

import urllib2
import xml.dom.minidom
import sys, time
import itertools
import re
import shutil

sys.path.append('/usr/local/lib/python')
import XenAPI

def printStats(hostname, username, password, filename, vmfilename):
    virtual = False

    f=open(filename, 'w')

    if (vmfilename != ""):
        vf = open(vmfilename, 'w')
        virtual = True
    else:
        vf = f

    url = 'https://%s' % hostname
    session = XenAPI.Session(url)
    try:
        session.login_with_password(username,password)
    except XenAPI.Failure, e:
        if (e.details[0] == 'HOST_IS_SLAVE'):
            session=XenAPI.Session("https://" + e.details[1])
            session.login_with_password(username,password)
        else:
            raise
    sx = session.xenapi
    retval = False

    for host in sx.host.get_all():
        hostname = sx.host.get_hostname(host)
        for pbd in sx.host.get_PBDs(host):
            sr = sx.PBD.get_SR(pbd)
            name = sx.SR.get_name_label(sr).replace(' ','_')
            if (re.match(r"(DVD_drives|Removable_storage|XenServer_Tools)", name)):
                continue
            if (sr != 'OpaqueRef:NULL'):
                f.write("%s sr_size_%s %s\n" % (hostname, name, sx.SR.get_physical_size(sr)))
                f.write("%s sr_virt_alloc_%s %s\n" % (hostname, name, sx.SR.get_virtual_allocation(sr)))

        for vm in sx.host.get_resident_VMs(host):
            hostname = sx.VM.get_name_label(vm)
	    vm_uuid = sx.VM.get_uuid(vm)

            # skip control domain
            if ('Control domain on host' in hostname):
                continue

            for vbd in sx.VM.get_VBDs(vm):
                vdi = sx.VBD.get_VDI(vbd)
                if (vdi != 'OpaqueRef:NULL'):
                    sr = sx.VDI.get_SR(vdi)
                    type = sx.SR.get_type(sr)
                    if (re.match(r"iso", type)):
                        continue
                    #vf.write("%s vbd_%s_size %s\n" % (hostname, sx.VBD.get_device(vbd), sx.VDI.get_virtual_size(vdi)))
                    vf.write("%s vbd_%s_size %s\n" % (vm_uuid, sx.VBD.get_device(vbd), sx.VDI.get_virtual_size(vdi)))

    sx.logout()    
    f.close()
    if (virtual):
        vf.close()


def main(hostname, username, password, filename, vmfilename = ""):
    tmpfilename = filename + '.tmp'
    tmpvmfilename = ""

    if (vmfilename != ""):
        tmpvmfilename = vmfilename + '.tmp'

    printStats(hostname, username, password, tmpfilename, tmpvmfilename)

    shutil.move(tmpfilename, filename)
    if (vmfilename != ""):
        shutil.move(tmpvmfilename, vmfilename)

    
if __name__ == "__main__":
    if   len(sys.argv) >= 5:
        main(*sys.argv[1:])
    elif len(sys.argv) == 1:
        main("xenserver", "root", "XXX", "/var/tmp/zabbixCitrixFile")
    else:
        print "Usage:"
        print sys.argv[0], " <hostname> <username> <password> <filename> [vmfilename]"
        sys.exit(1)

