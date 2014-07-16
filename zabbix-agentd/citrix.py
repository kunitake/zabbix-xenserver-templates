#!/usr/bin/python
#
# Probe for extracting performance data from 
# XAPI RRDs. 
#   by Emir Imamagic (eimamagi@srce.hr)
# 
# For more info on RRDs see:
#   http://wiki.xensource.com/xenwiki/XAPI_RRDs
# 
# In addition to VM performance data probe aggregates
# CPU usage over all CPUs (metric cpu) and counts 
# number of CPUs (metric cpu_count) on hosts and VMs.
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

def getHostsVms(hostname, username, password, hosts, vms):
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
        hosts[sx.host.get_uuid(host)] = sx.host.get_hostname(host)

        for vm in sx.host.get_resident_VMs(host):
            vms[sx.VM.get_uuid(vm)] = sx.VM.get_name_label(vm)
      
        retval = True

    sx.logout()

    return retval

def getStatsXML(hostname, username, password, delay):
    start = int(time.time()) - 2 * int(delay)
    theurl = 'http://%s/rrd_updates?start=%s&host=true&cf=ave&interval=%s' % (hostname, start, delay)

    # taken from:
    #   http://www.voidspace.org.uk/python/articles/authentication.shtml
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, theurl, username, password)
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)
    pagehandle = urllib2.urlopen(theurl)

    return pagehandle.read()

def getStats(hosts, username, password, delay):
    legendArr = []
    valueArr = []

    for hostname in hosts.itervalues():
        page = getStatsXML(hostname, username, password, delay)

        dom = xml.dom.minidom.parseString(page)
        legends = dom.getElementsByTagName("legend")[0]
        for legend in legends.getElementsByTagName("entry"):
            legendArr.append(legend.childNodes[0].data)

        values = dom.getElementsByTagName("row")[0]
        for v in values.getElementsByTagName("v"):
            valueArr.append(v.childNodes[0].data)

    # taken from:
    #   http://stackoverflow.com/questions/209840/map-two-lists-into-a-dictionary-in-python
    return dict(itertools.izip(legendArr,valueArr))

def printMetric(f, host, hostsCpu, hostsCpuCount, metric, value):
    # summarize cpu usage (TODO: make optional)
    if (re.match(r"cpu\d+", metric)):
        if (hostsCpu.has_key(host)):
            hostsCpuCount[host] += 1
            hostsCpu[host] += float(value)
        else:
            hostsCpuCount[host] = 1
            hostsCpu[host] = float(value)
    else:
        f.write("%s %s %s\n" % (host, metric, value))

def printHostCpu(f, hostsCpu, hostsCpuCount):
    for key, value in hostsCpu.iteritems():
        f.write("%s cpu %s\n" % (key, value))

    for key, value in hostsCpuCount.iteritems():
        f.write("%s cpu_count %s\n" % (key, value))

def printStats(values, hosts, vms, filename, vmfilename):
    hostsCpu = dict()
    vmsCpu = dict()
    hostsCpuCount = dict()
    vmsCpuCount = dict()
    virtual = False

    f=open(filename, 'w')

    if (vmfilename != ""):
        vf = open(vmfilename, 'w')
        virtual = True
    else:
        vf = f

    for key, value in values.iteritems(): 
        match = re.match(r"(\S+)\:(\S+)\:(\S+)\:(\S+)", key)
        # TODO: enable selecting type
        if (match.group(1) == 'AVERAGE'):
            metric = match.group(4)

            # find hostname
            if (match.group(2) == 'host'):
                if (hosts.has_key(match.group(3))):
                    host = hosts[match.group(3)]
                else:
                    continue
                printMetric(f, host, hostsCpu, hostsCpuCount, metric, value)
            elif (match.group(2) == 'vm'):
                if (vms.has_key(match.group(3))):
                    host = vms[match.group(3)]
                else:
                    continue
                # skip control domain
                if ('Control domain on host' in host):
                    continue
                printMetric(vf, host, vmsCpu, vmsCpuCount, metric, value)
            else:
                continue

    printHostCpu(f, hostsCpu, hostsCpuCount)
    printHostCpu(vf, vmsCpu, vmsCpuCount)

    f.close()
    if (virtual):
        vf.close()

def main(hostname, username, password, filename, vmfilename = ""):
    hosts = dict()
    vms = dict()
    delay = 60
    tmpfilename = filename + '.tmp'
    tmpvmfilename = ""

    if (vmfilename != ""):
        tmpvmfilename = vmfilename + '.tmp' 

    if (not getHostsVms(hostname, username, password, hosts, vms) ):
        print "ERROR: host not found"
    
    values = getStats(hosts, username, password, delay)
 
    printStats(values, hosts, vms, tmpfilename, tmpvmfilename)

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
        print sys.argv[0], " <master> <username> <password> <filename> [vmfilename]"
        sys.exit(1)

