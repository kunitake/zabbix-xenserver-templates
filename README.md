zabbix-xenserver-templates
==================================

Zabbix templates for Citrix XenServer and zabbix-sender for monitoring.

This templates and programs inspire by following programs of Emir Imamagic.

 Citrix XenAPI/RRDs monitoring
 https://www.zabbix.com/forum/showthread.php?t=25121

Usage
----------------
TBD
- import templates.
- /usr/libexec/zabbix-agentd
- cp zabbix-agentd/*.py /usr/libexec/zabbix-agentd
- cp citrix.conf /etc/zabbix/agent-conf.d
- edit XenServerVM-regist.pl
- exec XenServerVM-regist.pl

## TODO
- Rewrite by perl or python..
- code cleanup.
- Write "Usage"

