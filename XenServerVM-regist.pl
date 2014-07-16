#!/usr/bin/perl

use strict;
use warnings;
use Data::Dumper;

use ZabbixAPI;

use RPC::XML;
use RPC::XML::Client;
use Data::Dumper;

use Getopt::Long;
use Pod::Usage 'pod2usage';


my $DEBUG = 0;

# for Zabbix API
my $user    = 'zabbix';
my $pass    = 'zabbix';
my $api_url = 'http://localhost/zabbix/';


# Master server of XenServer pool.
my $master = '192.0.2.1';
my $xen_user = 'root';
my $xen_pass = 'pass';

{
    my $za = ZabbixAPI->new("$api_url");
    $za->login( "$user", "$pass" );

    # Establish the XEN API connection
    my $xen = RPC::XML::Client->new("http://$master");
    my $session = extractvalue($xen->simple_request("session.login_with_password",
                          $xen_user,$xen_pass));
   
    if (! $session)
    {
        print "connection failure : $master\n" if $DEBUG > 0;
        exit; # or NEXT;
    }

    # Template_Citrix_Trap_VM
    my $template_name = 'Template_Citrix_Trap_VM';
    my $templateid_citrix_trap_vm =  $za->template_get( {filter=>{host=>$template_name}})->[0]->{templateid};
   
    #$host_ref = extractvalue($xen->simple_request("session.get_this_host",
    #            $session,$session));
    # Get the reference for all the VMs on the xen dom0 host.
    #$domU_ref = extractvalue($xen->simple_request("host.get_resident_VMs",
    #            $session, $host_ref));
    my $pool_hosts = extractvalue($xen->simple_request("host.get_all", $session));

    foreach my $host (@$pool_hosts) {
	my $hostname = extractvalue($xen->simple_request("host.get_hostname", $session,$host));
	my $hostgroup_exist = $za->hostgroup_exists( { name => $hostname });

	if ( $hostgroup_exist ) {
    		print "$hostname : exist : True\n" if $DEBUG > 0;

	} else {
		my $create_hostgroup = $za->hostgroup_create(
						{
							'name'	=> $hostname,
						}
					);
	}

	my @groups = undef;
	push(@groups , $hostname);
	my $groupids = $za->hostgroup_get( { filter => { name => \@groups } });
	print Dumper $groupids if $DEBUG > 0;
	my $vms = extractvalue($xen->simple_request("host.get_resident_VMs", $session,$host));
        foreach my $vm_ref (@$vms) {
	    my $record = extractvalue($xen->simple_request("VM.get_record", $session, $vm_ref));
	    next if $record->{is_control_domain} == 1;

	    my $hostname = $record->{uuid};

	    my $hostname_exist = $za->host_exists( { host => $hostname });
	    print "HOST: $hostname\n" if $DEBUG > 0;

	    my @templates;
            push (@templates, {templateid => $templateid_citrix_trap_vm});

            my $vif_record = extractvalue($xen->simple_request("VM.get_VIFs", $session, $vm_ref));
	    foreach my $vif_ref (@$vif_record) {
			my $vifs = extractvalue($xen->simple_request("VIF.get_record", $session, $vif_ref));
			my $template_name = 'Template_Citrix_Trap_Network_vif_' . $vifs->{device};
			my $templateid =  $za->template_get( {filter=>{host=>$template_name}})->[0]->{templateid};
			push(@templates, {templateid => $templateid});
 	    }
	    my $vbd_record = extractvalue($xen->simple_request("VM.get_VBDs", $session, $vm_ref));
	    foreach my $vbd_ref (@$vbd_record) {
			my $vbd = extractvalue($xen->simple_request("VBD.get_record", $session, $vbd_ref));
			next if $vbd->{type} eq 'CD';
			my $template_name = 'Template_Citrix_Trap_Disk_' . $vbd->{device};
			my $templateid =  $za->template_get( {filter=>{host=>$template_name}})->[0]->{templateid};
			push (@templates, { templateid => $templateid});
   	    }
	    if ($hostname_exist) {
		print "$hostname true\n" if $DEBUG > 0;
 		my @hosts =  undef;
		push (@hosts, $hostname);
		my $hostid = $za->host_get( { filter => { host => \@hosts}} );

		print Dumper $hostid if $DEBUG > 0;
		print Dumper $groupids if $DEBUG > 0;
		print Dumper @templates if $DEBUG > 0;
		print $record->{name_label} . "\n" if $DEBUG > 0;
		print $hostid->[0]->{hostid} . "\n" if $DEBUG > 0;
		$hostid = $za->host_update(
				 {
					hostid => $hostid->[0]->{hostid},
					name => $record->{name_label},
					interfaces => [ {
						type => 1,
						main => 1,
						useip => 1,
						dns => '',
						ip => '127.0.0.1',
						port => '10050',
					},],
					groups => $groupids,
					templates => \@templates,
				}
				);
	         print Dumper $hostid if $DEBUG > 0;
 	    } else {
		my $hostid = $za->host_create(
				 {
					host => $hostname,
					name => $record->{name_label},
					interfaces => [ {
						type => 1,
						main => 1,
						useip => 1,
						dns => '',
						ip => '127.0.0.1',
						port => '10050',
					},],
					groups => $groupids,
					templates => \@templates,
				}
				);
		print Dumper $hostid if $DEBUG > 0;

	    } 

        }
    }
    #my $all_vm = $xen->simple_request("VM.get_all", $session);
    #print Dumper($all_vm);

exit;
}

sub extractvalue
{
    my ($val) = @_;
    if ($val->{'Status'} eq "Success")
    {
        print "Success?\n" if $DEBUG > 0;
        return $val->{'Value'};
    }
    else
    {
        print "fail?\n" if $DEBUG > 0;
        return undef;
    }
}

