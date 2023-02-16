#-*- coding:utf-8 -*-
import re, os, sys, collections, time, xlsxwriter, gzip, datetime
import pprint
from tqdm import tqdm


class ProcessMinAlanyzer():
    #!/usr/bin/env python3
    # -*- coding: utf-8 -*-
    #
    # 파일이 위치한 하위 폴더들에서 아리스타 show tech-support 자료를 분석
    # 모듈형 인터페이스 수정
    # 트랜시버 2개 시트 인터페이스 추가 안되게 수정
    # 시스템에 라우터ID ,AS 및 cvx 정보 제거
    # 2019.08.28
    # 2022.06.20 멀티케스트 카운트 오류 수정 v2.1 을 하다 만듯 하여, 이부분만 다시 수정
    # 2022.07.25 show command 변경 부분 수정
    # 2022.09.28 v3.0.0 - gz 인지 아닌지 구분 하고 gz도 실행 , cfg 수집 sheet 비활성
    # 2022.09.28 v3.0.3 tacacs 추가, 체크용 print 문 주석 print 문자들 정렬
    # 2022.09.30 v3.0.4 1) show interfaces 명령들에 all 추가, 2)bfd line 에 ms 단위 추가
    # 2022.09.30 v3.0.4 3) show logging 띄어쓰기 사라진것 반영, 4) interface count 중 load-interval default 0 일 경우 초 분 단위 없어짐
    # 2022.09.30 v3.0.4 5) bgp status 일부 수정 -- OSPF 추가시 대대적인 수정이 필요 할듯
    # 2022.09.30 v3.0.4 6) 시작 위치 상대 참조로 변경 , 인자로 폴더를 넣으면 해당 폴더부터 시작 함
    """
    2022.07.25
    command in ('show bfd neighbor detail', 'show bfd peers detail')
    command in ('show env cooling', 'show system env cooling')
    command in ('show env temperature', 'show system env temperature')
    flowcontrol - (desired|off|on|Unsupp.)
    2022.09.30
    command in ('show interfaces','show interfaces all' )
    command in ('show interfaces status','show interfaces all status')

    """


    ## 인터페이스 축양형 확장 용
    def expand(self, s, d):
        for key, val in d.items():
            if s == key:
                return val
        return None

    def alalyzer(self, showtechPath, yymmdd):
        analyzer_version = "3.0.4"
        expire_year = 2024
        now = datetime.date.today()
        strlen = 70
        
        int_dict = {"Et": "Ethernet", "Po": "Port-Channel", "Ma": "Management", "Ue": "UnconnectedEthernet", "Vx": "Vxlan",
                    "Vl": "Vlan", "Tu": "Tunnel", "Lo": "Loopback", "Re": "Recirc-Channel"}

        # 마스크 변환
        masks = ["0.0.0.0", "128.0.0.0", "192.0.0.0", "224.0.0.0", "240.0.0.0", "248.0.0.0", "252.0.0.0", "254.0.0.0",
                "255.0.0.0", "255.128.0.0", "255.192.0.0", "255.224.0.0", "255.240.0.0", "255.248.0.0", "255.252.0.0", "255.254.0.0",
                "255.255.0.0", "255.255.128.0", "255.255.192.0", "255.255.224.0", "255.255.240.0", "255.255.248.0", "255.255.252.0", "255.255.254.0",
                "255.255.255.0", "255.255.255.128", "255.255.255.192", "255.255.255.224", "255.255.255.240", "255.255.255.248", "255.255.255.252", "255.255.255.254",
                "255.255.255.255"]

        item_runconfig = ["Zone", "Model","Hostname", "EOS version",
                        "Sys MAC addr","spanning-tree","vlan 4094","interface Vlan4094","mlag configuration",
                        "router bgp","ip access-list","ip rout","ip prefix-list","route-map",
                        "interface Vxlan1",
                        "management cvx","cvx",
                        "vrf definition","management api http-commands",
                        "management console","management ssh","management telnet","management tech-support",
                        "alias","logging","ntp","snmp-server","username","monitor session","control-plane"]

        item_long_config = ["Zone", "Model","Hostname", "EOS version",
                            "Sys MAC addr","mlag configuration","router bgp","ip prefix-list","route-map",
                            "management cvx","cvx","interface Vxlan1"]


        # 시스템 정보
        item_system = ["Zone", "Model", "Hostname", "EOS version", "Model2",
                    "Sys MAC addr","mlag config",
                    "filename", "BootEOSfilename", "TerminAttr-core", "Serial number",

                    "Cur clock", "Timezone", "Clock source", "Timesynch", "Total Mac Addresses",
                    "Syslog logging", "Buffer logging", "Console logging", "Monitor logging", "Synchronous logging",
                    "Trap logging", "Loghost1", "Loghost2", "Default switchport mode",
                    "Syslog facility", "Hostname format", "Repeat logging interval", "Repeat messages",
                    "CPU % 5min", "Total memory", "Free memory", "Memory %", "Total flash", "Free flash", "Flash %",
                    "Cooling", "Ambient temperature", "Airflow", "Temperature", "Power supply slots", "Fan modules",
                    "Ports", "Transceiver slots", "Hardware version", "Uptime", "f Reload requested", "h Reload requested",
                    "Reload occurred", "Aboot"]

        item_mgmt_cvx = ["Zone","Model","Hostname", "EOS version",
                        "domain-id", "Connection count", "CVX IP", "Master", "Master since",
                        "Sys MAC addr",
                        "Status","Source interface","VRF","Hb interval","Hb timeout"," Cluster name",
                        "Connection status","Connection timestamp","Oob con","In-band con","Nego ver",
                        "Controller UUID","Last hb sent","Last hb received"]

        item_cvx = ["Zone","Model", "Hostname", "EOS version",
                    "Connection count","CVX C/S", "CVX Status", "CVX Role", "Peer IP", "Cluster name", "Peer Id", "Peer registration state", "version compatibility",
                    "Hb interval", "Hb timeout", "Master since", "Peer timeout", "UUID"]


        item_cvx_connection = ["Zone","Model", "Hostname", "EOS version",
                            "Sys MAC addr",
                            "Connection count","Switch Mac","Switch Hostname","State","Connection timestamp","Last heartbeat sent",
                            "Last heartbeat received","Out-of-band connection","In-band connection"]

        item_tacacs = ["Zone", "Model", "Hostname", "EOS version",
                    "count","TACACS server","Connection opens","Connection closes","Connection disconnects",
                    "Connection failures", "Connection timeouts","Messages sent",
                    "Messages received","Receive errors","Receive timeouts","Send timeouts"]


        item_bfd = ["Zone","Model", "Hostname", "EOS version",
                    "VRF name","LAddr","count","Peer Addr","Intf","Type","State","Registered protocols",
                    "LD/RD","Last Up","Last Down","TxInt","RxInt","Multiplier","Received RxInt","Received Multiplier","Detect Time",
                    "Uptime","Rx Count","Tx Count"]

        # 기본 설정
        item_basic = ["Zone", "Model", "Hostname", "EOS version",
                    "Sys MAC addr",
                    "Local AS","Router ID","maximum-paths","timers bgp","bgp asn notation",
                    "Terminal length", "Load-interval default", "Authorization exec", "enable secret",
                    "Logging buffered", "Logging console", "Logging monitor", "Logging host1", "Logging host2",
                    "Logging source-interface", "Logging synchronous",
                    "Ntp1", "Ntp2", "Clock timezone", "icmp redirect", "vmtracer", "banner",
                    "API cfg", "Telnet cfg", "SSH cfg", "CVX cfg", "support", "LICENSE 0", "CVX VIP shut",
                    "snmp-server source-interface", "community1", "community2","Vmac",
                    "STP mode", "STP no vlan", "STP bpduguard", "STP ins", "STP priority",
                    "unsupported-transceiver", "Ip routing","mac aging-time"]

        # mlag 정보
        item_mlag = ["Zone", "Model", "Hostname", "EOS version",
                    "domain-id",
                    "Sys MAC addr",
                    "local-interface", "peer-address", "peer-link", "peer-config",
                    "state1", "negotiation status", "peer-link status", "local-int status",
                    "system-id", "dual-primary detection", "hb-peer-address", "Disabled", "Configured", "Inactive",
                    "Active-partial", "Active-full",
                    "State2", "Peer State", "primary-priority", "Peer MAC address", "Peer MAC routing supported",
                    "Reload delay", "Non-MLAG reload delay",
                    "Configured heartbeat interval", "Effective heartbeat interval", "Heartbeat timeout",
                    "Fast MAC redirection enabled"]

        # lldp 정보
        item_lldp = ["Zone", "Model", "Hostname", "EOS version",
                    "Local interface",
                    "LLDP count", "Remote Port ID", "Remote Port ID type",
                    "Remote System Name","Remote Port Description", "Remote Chassis ID",  "Remote Chassis ID type",
                    "Remote Management Address",
                    "Remote IEEE802.1 Port VLAN ID", "Link Aggregation Status", "IEEE802.3 Maximum Frame Size",
                    "Discovered", "Last changed", "MAU Type", "Remote System Description",
                    "Sys MAC addr", "type", "number"]

        ### int runing config
        item_int_cfg = ["Zone","Model", "Hostname", "EOS version",
                        "interface",
                        "Sys MAC addr", "type", "number",
                        "description", "switchport mode", "access vlan", "allowed vlan", "portfast", "mlag id",
                        "no switchport", "shutdown",
                        "ip address", "subnet mask",
                        "Fhrp mode", "VIP", "VRRP ID",
                        "channel-group", "channel-mode",
                        "no autostate","vmtracer","storm-control broadcast","storm-control multicast",
                        "vxlan source-interface", "vxlan controller-client", "vxlan udp-port"]

        ### show interfaces
        item_int = ["Zone","Model", "Hostname", "EOS version",
                    "interface",
                    "Sys MAC addr", "type", "number","description",

                    ## show interfaces status
                    "sis Status", "sis Vlan", "sis Duplex", "sis Speed", "sis Media type",

                    "link status changes since last clear", "Last clearing",
                    "input rate", "input rate bps", "input rate %", "input packet/sec",
                    "output rate", "output rate bps", "output rate %", "output packet/sec",
                    "input packets", "input bytes",
                    "Received broadcasts", "Received multicast",
                    "runts", "giants",
                    "input errors", "CRC", "alignment", "symbol", "input discards",
                    "PAUSE input",
                    "output packets", "output bytes",
                    "Sent broadcasts", "Sent multicast",
                    "output errors", "collisions",
                    "late collision", "deferred", "output discards",
                    "PAUSE output",
                    "Tx Power", "Rx Power", "Temperature","Voltage","Current",
                    "Manufacturer", "T-Model", "T-Serial",

                    ## show FlowControl
                    "Send FlowControl admin", "Send FlowControl oper", "Receive FlowControl admin", "Receive FlowControl oper",
                    "RxPause", "TxPause",

                    "int status", "line protocol", "status",
                    "Hardware", "mac address",
                    "duplex", "speed", "auto negotiation", "uni-link",
                    "MTU", "BW",
                    "Fallback mode", "Loopback Mode", "status time",

                    "Internet address", "Mask bits", "Mask",
                    "Member of Port-Channel",
                    "Active members in this channel",
                    "member int1", "member int2", "member int3", "member int4",
                    "vxlan Source interface", "vxlan Source ip", "Flood List Source", "Remote MAC learning",

                    ## show interfaces switchport

                    "Switchport", "Administrative Mode", "Operational Mode", "MAC Address Learning",
                    "Dot1q ethertype/TPID", "Dot1q Vlan Tag Required (Administrative/Operational)",
                    "Access Mode VLAN", "Trunking Native Mode VLAN", "Administrative Native VLAN tagging",
                    "Trunking VLANs Enabled", "Static Trunk Groups", "Dynamic Trunk Groups", "Source interface filtering"]

        item_transceiver = ["Zone","Model", "Hostname", "EOS version",
                            "interface",
                            "Tx Power", "Rx Power", "Temperature","Voltage","Current",
                            "T-dBm-HA", "T-dBm-HW", "T-dBm-LA", "T-dBm-LW",
                            "R-dBm-HA", "R-dBm-HW", "R-dBm-LA", "R-dBm-LW",
                            "T-HA", "T-HW", "T-LA", "T-LW",
                            "V-HA", "V-HW", "V-LA", "V-LW",
                            "mA-HA", "mA-HW", "mA-LA", "mA-LW",
                            "Sys MAC addr", "type", "number"]

        item_transceiver_serial = ["Zone","Model", "Hostname", "EOS version",
                                "interface",
                                "Sys MAC addr", "type", "number",
                                "Manufacturer", "T-Model", "T-Serial"]



        item_bgp_stat = ["Zone","Model", "Hostname", "EOS version",
                        "local router ID","Local TCP address","VRF","Local AS","count","remote AS","BGP neighbor", "remote router ID",
                        "Remote TCP address","TCP state",
                        "link", "TTL",
                        "Local TCP port", "Remote TCP port",
                        "BGP version", "peer-group",

                        "Inbound route map","Outbound route map","Auto-Local-Addr",

                        "Last read", "last write",
                        "Hold time", "keepalive interval", "Cfg hold time", "Cfg keepalive interval",
                        "Connect timer", "Idle-restart time",
                        "BGP state", "BGP up for",
                        "Number of transitions to established", "Last state", "Last event",
                        "Last sent notification","Last rcvd notification",
                        "Multiprotocol", "Four Octet ASN", "Route Refresh", "Send End-of-RIB messages",
                        "Additional-paths recv capability", "Additional-paths send capability",
                        "GR received Restart-time", "GR received Restarting", "GR received IPv4 Unicast",
                        "GR received Forwarding State",

                        "Restart timer", "End of rib timer",

                        "InQ depth", "OutQ depth", "Sent Opens", "Rcvd Opens", "Sent Notifications", "Rcvd Notifications",
                        "Sent Updates", "Rcvd Updates", "Sent Keepalives", "Rcvd Keepalives",
                        "Sent Route-Refresh", "Rcvd Route-Refresh", "Sent Total messages", "Rcvd Total messages",

                        "Sent pfx IPv4 Unicast", "Rcvd pfx IPv4 Unicast", "Sent pfx IPv6 Unicast", "Rcvd pfx IPv6 Unicast",
                        "Sent pfx IPv4 SR-TE", "Rcvd pfx IPv4 SR-TE", "Sent pfx IPv6 SR-TE", "Rcvd pfx IPv6 SR-TE",

                        "AS path loop detection", "Enforced First AS",
                        "Originator ID matches local router ID", "Nexthop matches local IP address",
                        "Unexpected IPv6 nexthop for IPv4 routes", "Nexthop invalid for single hop eBGP",

                        "Resulting in removal of all paths in update (treat-as-withdraw)",
                        "Resulting in AFI/SAFI disable",
                        "Resulting in attribute ignore",

                        "IPv4 labeled-unicast NLRIs dropped due to excessive labels",
                        "IPv6 labeled-unicast NLRIs dropped due to excessive labels",

                        "IPv4 local address not available", "IPv6 local address not available",

                        "Recv-Q", "Send-Q", "Outgoing MSS", "TCP retransmissions",

                        "Timestamps enabled", "Selective Acknowledgments enabled",
                        "Window Scale enabled", "Explicit Congestion Notification (ECN) enabled",

                        "Window Scale (wscale)", "Retransmission Timeout (rto)", "Round-trip Time (rtt/rtvar)",
                        "Delayed Ack Timeout (ato)", "Congestion Window (cwnd)", "TCP Throughput",
                        "Recv Round-trip Time (rcv_rtt)", "Advertised Recv Window (rcv_space)"]

        item_fhrp = ["Zone","Model", "Hostname", "EOS version",
                    "fhrp mode",
                    "Interface","Group ID","VRF","VRRP Version","State",
                    "Master Router", "Master Priority","Master local",
                    "Virtual IPv4 address","Virtual MAC address","Mac Address Advertisement interval",
                    "VRRP Advertisement interval","Preemption","Preemption delay","Preemption reload delay",
                    "Priority","Authentication","Master Advertisement interval",
                    "Skew time","Master Down interval",
                    "Protocol","Mlag peer MAC address"]

        # 최종 정보 수집용
        info_system = collections.OrderedDict()
        info_mlag = collections.OrderedDict()

        info_mgmt_cvx = collections.OrderedDict()
        info_cvx = collections.OrderedDict()
        info_cvx_connection = collections.OrderedDict()
        info_bfd = collections.OrderedDict()
        info_tacacs = collections.OrderedDict()
        info_bgp_stat = collections.OrderedDict()

        info_lldp = collections.OrderedDict()
        info_int = collections.OrderedDict()
        info_fhrp = collections.OrderedDict()
        info_transceiver = collections.OrderedDict()
        info_transceiver_serial = collections.OrderedDict()

        # 관련 설정 수집용
        cfg_basic = collections.OrderedDict()
        cfg_int = collections.OrderedDict()
        cfg_runconfig = collections.OrderedDict()
        cfg_longconfig = collections.OrderedDict()
        # 변수
        start_time = time.time()  # 실행 시간 확인 용
        cur_path = os.getcwd()  # 파일 실행 위치 확인
        folderDict = collections.OrderedDict()  # Zone 별로 폴더 확인용
        pathfileDict = collections.OrderedDict()  # 위치가 포함된 파일명
        dupdevices = {}
        filecount = 0
        subfoldername = ""
        # start_folder = f'{cur_path}/2022-09-28'
        # start_folder = f'./2022-09-28'

        start_folder = showtechPath + "/showtech"
        # print(f"cur_path : {cur_path}")

        # print(f"start_folder : {start_folder}")
        if os.path.exists(f"{showtechPath}/report/{yymmdd}/arista_analysis_{yymmdd}.xlsx"):
            return False, "이미 작성된 Show Tech 분석 리포트가 있습니다."

        showCmdPatternPrefix = "------------- "
        showCmdPatternSuffix = " -------------"
        showCmdPattern = f"{showCmdPatternPrefix}(show .*?){showCmdPatternSuffix}$|{showCmdPatternPrefix}(.*?){showCmdPatternSuffix}$"

        cmdRe = re.compile(showCmdPattern)

        # 프로그램 시작
        # 실행위치 폴더 파일 이름 확인
        # files = 폴더안 파일 리스트, pathfiles = 위치포함 파일 리스트, f=최종 파일을 읽고 있는 중

        # for path, dirs, files in os.walk(cur_path):
        
        showtechList = os.listdir(start_folder)
        pathfileDict = {}
        
        if len(showtechList) == 0:
            return False, "show tech 파일이 없습니다."

        if showtechList:
            for file in sorted(showtechList):  # 오름차순 정렬순으로
                pathfileDict[os.path.join(start_folder, file)] = yymmdd  # 절대 경로 파일 과 zone 추가
                    

        try:
            
            for techfile, zone in pathfileDict.items():  # 파일 리스트에서 파일 하나씩 오픈
                if filecount > 0 and f.closed==False:
                    print(f'File close status : {f.closed}')
                    f.close()

                m = re.search("(\.gz$)", techfile)        
                if m:
                    # print(m.group(1))        # gz 정상으로 구분하는지 체크
                    f = gzip.open(techfile, mode='rt', encoding='utf8')
                else:
                    # print(techfile)        
                    f = open(techfile, "r", encoding='utf8')  # 윈도우에서 실행시 인코딩 정보 필요

                    #with gzip.open(techfile,mode="rt") as f:
                    #with open(techfile, "r", encoding='utf8') as f:  # 윈도우에서 실행시 인코딩 정보 필요
                filecount += 1
                file_num_str = "No."

                print("\n\n", os.path.basename(techfile.strip()), " 처리중\n")

                sys_mac_addr = ''  # 호스트네임이 동일 할 수 있기에 유일한 시스템 맥으로 장비 구분
                hostname = ''
                switch_model = ''
                switch_model_except_RF =''
                eos_version = ''
                serial_number =''
                mlag_domain_id = ''

                command = ''  # show tech 의 각 명령 대입용
                section = ''
                item = ''
                local_int = ''
                lldp_count = ''
                remote_int = ''
                remote_chassis_id = ''
                discovered_time = ''
                last_changed_time = ''

                # pbar = tqdm(f.readlines())
                for line in f:  # 파일에서 한줄씩 읽음
                    # print(f'{line}')    ## 어느 줄에서 중지 되었는지 확인용이지만, 파일이 많을 경우 너무 오래 걸림

                    m = cmdRe.match(line)
                    if m:
                        command = m.group().replace(showCmdPatternPrefix, "").replace(showCmdPatternSuffix, "")
                        # command = re.sub(r"([/\|\/\:\\\'\^\<\>\"\*])", "", command)
                        section = ''
                        item = ''
                        local_int = ''
                        lldp_count = ''
                        remote_int = ''
                        remote_chassis_id = ''
                        remote_int_type = ''
                        remote_chassis_id_type = ''
                        discovered_time = ''
                        last_changed_time = ''
                        z = 0
                        c_Source_interface = ''
                        c_VRF =''

                        r_spanning = []
                        r_logging = []
                        r_vlan4094 = []
                        r_interfaceVlan4094 = []
                        r_mlag = []
                        r_bgp = []
                        r_access = []
                        r_iprout = []
                        r_pfx =[]
                        r_rm = []
                        r_vx = []
                        r_mgmt_cvx = []
                        r_cvx = []
                        r_vrf = []
                        r_console = []
                        r_ssh = []
                        r_telnet = []
                        r_api = []
                        r_tech = []
                        r_alias = []
                        r_ntp = []
                        r_snmp = []
                        r_user = []
                        r_monitor = []
                        r_ctr_plane = []

                        continue  # for 구문으로 돌아가 다음 줄 읽기

                    # 한대의 스위치를 최초 인식하기 위해 시스템 맥어드레스 체크
                    #####################################################################################################################
                    if command == 'show version detail' and sys_mac_addr == '':
                        # print("show version!!")
                        m = re.match("System MAC address:\s+([\w|\.]+\w$)", line)
                        if m:
                            sys_mac_addr = m.group(1)

                            # 각 시스템 맥 어드레스로 구분자 - 즉 키 값
                            if sys_mac_addr in info_system.keys():
                                print(f'{file_num_str} {str(filecount).ljust(4)} : {techfile}  , DUP!!! system mac address is {sys_mac_addr}')
                                dupdevices[sys_mac_addr] = [info_system[sys_mac_addr]["Hostname"]]
                                break
                            if sys_mac_addr not in info_system.keys():  # 키 값에 맥이 없다면 아래 실행, show tech 별 한번으로 예상
                                info_system[sys_mac_addr] = collections.OrderedDict(zip(item_system, [''] * len(item_system)))
                                info_system[sys_mac_addr]["Sys MAC addr"] = sys_mac_addr
                                info_system[sys_mac_addr]["Zone"] = zone
                                #                     m = re.search(".*/([a-zA-Z0-9][\w-]*)$", techfile)
                                m = re.search(".*[\\\\|/]([a-zA-Z0-9].*\w)$", techfile)
                                if m:
                                    info_system[sys_mac_addr]["filename"] = m.group(1)

                            if sys_mac_addr not in cfg_basic.keys():
                                cfg_basic[sys_mac_addr] = collections.OrderedDict(zip(item_basic, [''] * len(item_basic)))
                                cfg_basic[sys_mac_addr]["Sys MAC addr"] = sys_mac_addr
                                cfg_basic[sys_mac_addr]["Zone"] = zone

                            if sys_mac_addr not in cfg_runconfig.keys():
                                cfg_runconfig[sys_mac_addr] = collections.OrderedDict(zip(item_runconfig, [''] * len(item_runconfig)))
                                cfg_runconfig[sys_mac_addr]["Sys MAC addr"] = sys_mac_addr
                                cfg_runconfig[sys_mac_addr]["Zone"] = zone

                            if sys_mac_addr not in cfg_longconfig.keys():
                                cfg_longconfig[sys_mac_addr] = collections.OrderedDict(zip(item_long_config, [''] * len(item_long_config)))
                                cfg_longconfig[sys_mac_addr]["Sys MAC addr"] = sys_mac_addr
                                cfg_longconfig[sys_mac_addr]["Zone"] = zone
                            # mlag
                            # lldp
                            if sys_mac_addr not in info_bgp_stat.keys():
                                info_bgp_stat[sys_mac_addr] = collections.OrderedDict()
                            if sys_mac_addr not in info_transceiver.keys():
                                info_transceiver[sys_mac_addr] = collections.OrderedDict()
                            if sys_mac_addr not in info_transceiver_serial.keys():
                                info_transceiver_serial[sys_mac_addr] = collections.OrderedDict()
                            if sys_mac_addr not in info_int.keys():
                                info_int[sys_mac_addr] = collections.OrderedDict()
                            if sys_mac_addr not in cfg_int.keys():
                                cfg_int[sys_mac_addr] = collections.OrderedDict()
                            
                            # pbar.position(0)
                            f.seek(0)  # 파일 초기로 이동
                            continue

                    ###########################################################################################################################
                    if command == 'show version detail' and sys_mac_addr != '':
                        
                        m = re.match("Arista\s+(.*)", line)
                        if m:
                            if "-F" == m.group(1)[-2:] or "-R" == m.group(1)[-2:]:
                                switch_model = m.group(1)[:-2]
                            else:
                                switch_model = m.group(1)                       # F 또는 R 옵션이 없는 모델은 F
                            info_system[sys_mac_addr]['Model2'] = m.group(1)
                            info_system[sys_mac_addr]['Model'] = switch_model
                            cfg_basic[sys_mac_addr]["Model"] = switch_model
                            cfg_runconfig[sys_mac_addr]["Model"] = switch_model
                            cfg_longconfig[sys_mac_addr]["Model"] = switch_model
                            continue
                        m = re.match("Hardware version:\s+([\w|\.]+)", line)
                        if m:
                            info_system[sys_mac_addr]['Hardware version'] = m.group(1)
                            continue
                        m = re.match("Serial number:\s+(\w*)", line)
                        if m:
                            serial_number = m.group(1)
                            info_system[sys_mac_addr]['Serial number'] = m.group(1)
                            continue
                        m = re.match("Software image version:\s([\w|\.]+)", line)
                        if m:
                            eos_version = m.group(1)
                            info_system[sys_mac_addr]['EOS version'] = m.group(1)
                            cfg_basic[sys_mac_addr]["EOS version"] = m.group(1)
                            cfg_runconfig[sys_mac_addr]["EOS version"] = m.group(1)
                            cfg_longconfig[sys_mac_addr]["EOS version"] = m.group(1)
                            continue
                        m = re.match("Uptime:\s+(\d.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Uptime'] = m.group(1)
                            continue
                        m = re.match("Total memory:\s+(\d*) kB", line)
                        if m:
                            info_system[sys_mac_addr]['Total memory'] = int(m.group(1))
                            continue
                        m = re.match("Free memory:\s+(\d*) kB", line)
                        if m:
                            info_system[sys_mac_addr]['Free memory'] = int(m.group(1))
                            info_system[sys_mac_addr]['Memory %'] = round(((1 - info_system[sys_mac_addr]['Free memory'] / info_system[sys_mac_addr]['Total memory']) * 100),2)
                            continue
                        m = re.match("TerminAttr-core\s+([\w|\.]+)", line)
                        if m:
                            info_system[sys_mac_addr]['TerminAttr-core'] = m.group(1)
                            continue

                        m = re.search(" (Aboot-\S+)", line)
                        if m:
                            info_system[sys_mac_addr]['Aboot'] = m.group(1)
                            continue

            #                m = re.match("Aboot\s+([\S]+)", line)
            #                if m:
            #                    info_system[sys_mac_addr]['Aboot'] = m.group(1)
            #                    continue
            #                m = re.match("Supervisor1-Aboot\s+([\S]+)", line)
            #                if m:
            #                    info_system[sys_mac_addr]['Aboot'] = m.group(1)
            #                    continue

                    ###########################################################################################################################
                    # OS 버전에 따라 full 과 history 하나가 없고 reload 문구가 다르기도 함 일단 f 과 h 접두어로 구분
                    if command == 'show reload cause full' and sys_mac_addr != '':

                        m = re.match("Reload requested by\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['f Reload requested'] = m.group(1)
                            continue
                        m = re.match("The system rebooted\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['f Reload requested'] = m.group(1)
                            continue
                        m = re.match("Reload occurred at\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Reload occurred'] = m.group(1)
                            continue

                    ###########################################################################################################################
                    if command == 'show reload cause history' and sys_mac_addr != '':

                        m = re.match("Reload requested by\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['h Reload requested'] = m.group(1)
                            continue
                        m = re.match("The system rebooted\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['h Reload requested'] = m.group(1)
                            continue
                        m = re.match("Reload occurred at\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Reload occurred'] = m.group(1)
                            continue

                    ###########################################################################################################################
                    if command == 'show running-config sanitized' and sys_mac_addr != '':
                        # info 에 파일 패스 추가
                        m = re.match("! boot system (.*)", line)
                        if m:
                            info_system[sys_mac_addr]['BootEOSfilename'] = m.group(1)
                            continue
                        # basic config
                        m = re.match("terminal length (\d*)", line)
                        if m:
                            cfg_basic[sys_mac_addr]['Terminal length'] = m.group(1)
                            continue
                        m = re.match("(logging|no logging)", line)
                        if m:
                            section = "logging"
                            r_logging.append(line)

                            m = re.match("logging buffered (.+)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['Logging buffered'] = m.group(1)
                                continue
                            m = re.match("logging console (\w*)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['Logging console'] = m.group(1)
                                continue
                            m = re.match("logging monitor (\w*)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['Logging monitor'] = m.group(1)
                                continue
                            m = re.match("logging host (\S*)", line)
                            if m:
                                if cfg_basic[sys_mac_addr]['Logging host1'] == "":
                                    cfg_basic[sys_mac_addr]['Logging host1'] = m.group(1)
                                else:
                                    cfg_basic[sys_mac_addr]['Logging host2'] = m.group(1)
                                continue

                            m = re.match("logging (vrf \S*) host (\S*)", line)
                            if m:
                                if cfg_basic[sys_mac_addr]['Logging host1'] == "":
                                    cfg_basic[sys_mac_addr]['Logging host1'] = m.group(1) +" "+m.group(2)
                                else:
                                    cfg_basic[sys_mac_addr]['Logging host2'] = m.group(1) +" "+m.group(2)
                                continue

                            m = re.match("logging source-interface (\S*)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['Logging source-interface'] = m.group(1)
                                continue
                            m = re.match("logging synchronous (.*)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['Logging synchronous'] = m.group(1)
                                continue
                            m = re.match("logging level LICENSE emergencies", line)
                            if m:
                                cfg_basic[sys_mac_addr]['LICENSE 0'] = "configured"
                                continue
                        if section == "logging":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['logging'] = ''.join(r_logging)
                                continue

                        m = re.match("ntp ", line)
                        if m:
                            section = "ntp "
                            r_ntp.append(line)
                            m = re.match("ntp server (.*)", line)
                            if m:
                                if cfg_basic[sys_mac_addr]['Ntp1'] == "":
                                    cfg_basic[sys_mac_addr]['Ntp1'] = m.group(1)
                                else:
                                    cfg_basic[sys_mac_addr]['Ntp2'] = m.group(1)
                                continue
                        if section == "ntp ":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['ntp'] = ''.join(r_ntp)
                                continue

                        m = re.match("(snmp-server|no snmp-server)", line)
                        if m:
                            section = 'snmp-server'
                            r_snmp.append(line)
                            m = re.match("snmp-server source-interface (.*)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['snmp-server source-interface'] = m.group(1)
                                continue
                            m = re.match("snmp-server community (.*)", line)
                            if m:
                                if cfg_basic[sys_mac_addr]['community1'] == "":
                                    cfg_basic[sys_mac_addr]['community1'] = "Item present"
                                else:
                                    cfg_basic[sys_mac_addr]['community2'] = "Item present"
                                continue
                        if section == 'snmp-server':
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['snmp-server'] = ''.join(r_snmp)
                                continue

                        m = re.match("(spanning-tree|no spanning-tree)", line)
                        if m:
                            section = 'spanning-tree'
                            r_spanning.append(line)
                            r_mlag.append(line)
                            m = re.match("spanning-tree mode (\S+)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['STP mode'] = m.group(1)
                                continue
                            m = re.match("no spanning-tree vlan (\d+)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['STP no vlan'] = m.group(1)
                                continue
                            m = re.match("spanning-tree portfast bpduguard default", line)
                            if m:
                                cfg_basic[sys_mac_addr]['STP bpduguard'] = "configured"
                                continue
                            m = re.match("spanning-tree (\w+\s\d+) priority (\d+)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['STP ins'] = m.group(1)
                                cfg_basic[sys_mac_addr]['STP priority'] = m.group(2)
                                continue
                        if section == 'spanning-tree':
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['spanning-tree'] = ''.join(r_spanning)
                                continue

                        m = re.match("username", line)
                        if m:
                            section = "username"
                            r_user.append(line)
                        if section == "username":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['username'] = ''.join(r_user)
                                continue

                        m = re.match("vlan 4094", line)
                        if m:
                            section = "vlan4094"
                        if section ==  "vlan4094":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['vlan 4094'] = ''.join(r_vlan4094)
                                continue
                            r_vlan4094.append(line)
                            r_mlag.append(line)
                            continue

                        m = re.match("vrf definition", line)
                        if m:
                            section = "vrf definition"
                        if section == "vrf definition":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['vrf definition'] = ''.join(r_vrf)
                                continue
                            r_vrf.append(line)
                            continue

                        m = re.match("interface Vlan4094", line)
                        if m:
                            section = "interface Vlan4094"
                        if section ==  "interface Vlan4094":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['interface Vlan4094'] = ''.join(r_interfaceVlan4094)
                                continue
                            r_interfaceVlan4094.append(line)
                            r_mlag.append(line)
                            continue

                        m = re.match("ip access-list", line)
                        if m:
                            section = "ip access-list"
                        if section ==  "ip access-list":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['ip access-list'] = ''.join(r_access)
                                continue
                            r_access.append(line)
                            continue

                        m = re.match("ip rout", line)
                        if m:
                            section = "ip rout"
                            r_iprout.append(line)
                            m = re.match("ip routing$", line)
                            if m:
                                cfg_basic[sys_mac_addr]['Ip routing'] = "ip routing"
                        if section == "ip rout":
                            if line == '!\n':
                                cfg_runconfig[sys_mac_addr]['ip rout'] = ''.join(r_iprout)
                                continue

                        m = re.match("mlag configuration", line)
                        if m:
                            section = "mlag configuration"
                        if section ==  "mlag configuration":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['mlag configuration'] = ''.join(r_mlag)
                                cfg_longconfig[sys_mac_addr]['mlag configuration'] = ''.join(r_mlag)
                                continue
                            r_mlag.append(line)
                            continue

                        m = re.match("ip prefix-list", line)
                        if m:
                            section = "ip prefix-list"
                        if section == "ip prefix-list":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['ip prefix-list'] = ''.join(r_pfx)
                                cfg_longconfig[sys_mac_addr]['ip prefix-list'] = ''.join(r_pfx)
                                continue
                            r_pfx.append(line)
                            continue

                        m = re.match("route-map", line)
                        if m:
                            section = "route-map"
                        if section == "route-map":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['route-map'] = ''.join(r_rm)
                                cfg_longconfig[sys_mac_addr]['route-map'] = ''.join(r_rm)
                                continue
                            r_rm.append(line)
                            continue

                        m = re.match("monitor session", line)
                        if m:
                            section = "monitor session"
                            r_monitor.append(line)
                        if section == "monitor session":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['monitor session'] = ''.join(r_monitor)
                                continue

                        m = re.match("alias", line)
                        if m:
                            section = "alias"
                        if section == "alias":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['alias'] = ''.join(r_alias)
                                continue
                            m = re.match("alias support", line)
                            if m:
                                cfg_basic[sys_mac_addr]['Support cfg'] = "Item present"
                            r_alias.append(line)
                            continue

                        m = re.match("control-plane", line)
                        if m:
                            section = "control-plane"
                        if section == "control-plane":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['control-plane'] = ''.join(r_ctr_plane)
                                continue
                            r_ctr_plane.append(line)
                            continue

                        m = re.match("management cvx", line)
                        if m:
                            section = "management cvx"
                            cfg_basic[sys_mac_addr]['CVX cfg'] = "Item present"
                        if section == "management cvx":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['management cvx'] = ''.join(r_mgmt_cvx)
                                cfg_longconfig[sys_mac_addr]['management cvx'] = ''.join(r_mgmt_cvx)
                                continue
                            r_mgmt_cvx.append(line)
                            continue

                        m = re.match("cvx", line)
                        if m:
                            section = "cvx"
                        if section == "cvx":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['cvx'] = ''.join(r_cvx)
                                cfg_longconfig[sys_mac_addr]['cvx'] = ''.join(r_cvx)
                                continue
                            r_cvx.append(line)
                            continue

                        m = re.match("management console", line)
                        if m:
                            section = "management console"
                        if section == "management console":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['management console'] = ''.join(r_console)
                                continue
                            r_console.append(line)
                            continue

                        m = re.match("management ssh", line)
                        if m:
                            section = "management ssh"
                            cfg_basic[sys_mac_addr]['SSH cfg'] = "Item present"
                        if section == "management ssh":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['management ssh'] = ''.join(r_ssh)
                                continue
                            r_ssh.append(line)
                            continue

                        m = re.match("management telnet", line)
                        if m:
                            section = "management telnet"
                            cfg_basic[sys_mac_addr]['Telnet cfg'] = "Item present"
                        if section == "management telnet":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['management telnet'] = ''.join(r_telnet)
                                continue
                        if section == "management telnet":
                            r_telnet.append(line)
                            continue


                        m = re.match("management api http-commands", line)
                        if m:
                            section = "management api http-commands"
                            cfg_basic[sys_mac_addr]['API cfg'] = "Item present"
                        if section == "management api http-commands":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['management api http-commands'] = ''.join(r_api)
                                continue
                        if section == "management api http-commands":
                            r_api.append(line)
                            continue

                        m = re.match("management tech-support", line)
                        if m:
                            section = "management tech-support"
                        if section == "management tech-support":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['management tech-support'] = ''.join(r_tech)
                                continue
                        if section == "management tech-support":
                            r_tech.append(line)
                            continue

                        m = re.match("no ip icmp redirect", line)
                        if m:
                            cfg_basic[sys_mac_addr]['icmp redirect'] = "no redirect"
                            continue
                        m = re.match("vmtracer session ", line)
                        if m:
                            cfg_basic[sys_mac_addr]['vmtracer'] = "Item present"
                            continue
                        m = re.match("banner login", line)
                        if m:
                            cfg_basic[sys_mac_addr]['banner'] = "Item present"
                            continue

                        m = re.match("hostname ([a-zA-Z0-9][a-zA-Z0-9_\-\.]*)", line)
                        if m:
                            hostname = m.group(1)
                            info_system[sys_mac_addr]['Hostname'] = m.group(1)
                            cfg_basic[sys_mac_addr]['Hostname'] = m.group(1)
                            cfg_runconfig[sys_mac_addr]['Hostname'] = m.group(1)
                            cfg_longconfig[sys_mac_addr]['Hostname'] = m.group(1)
                            continue

                        m = re.match("service unsupported-transceiver (.+)", line)
                        if m:
                            cfg_basic[sys_mac_addr]['unsupported-transceiver'] = "configured"
                            continue
                        m = re.match("enable secret (.+)", line)
                        if m:
                            cfg_basic[sys_mac_addr]['enable secret'] = "Item present"
                            continue
                        m = re.match("clock timezone (\S+)", line)
                        if m:
                            cfg_basic[sys_mac_addr]['Clock timezone'] = m.group(1)
                            continue
                        m = re.match("aaa authorization exec (.+)", line)
                        if m:
                            cfg_basic[sys_mac_addr]['Authorization exec'] = m.group(1)
                            continue

                        m = re.match("agent managementActive shutdown", line)
                        if m:
                            cfg_basic[sys_mac_addr]['CVX VIP shut'] = "configured"
                            continue
                        m = re.match("ip virtual-router mac-address (\S+)", line)
                        if m:
                            cfg_basic[sys_mac_addr]['Vmac'] = m.group(1)
                            continue
                        m = re.match("load-interval default (\d*)", line)
                        if m:
                            cfg_basic[sys_mac_addr]['Load-interval default'] = m.group(1)
                            continue
                        m = re.match("mac address-table aging-time (\d*)", line)
                        if m:
                            cfg_basic[sys_mac_addr]['mac aging-time'] = m.group(1)
                            continue

                        ###########################################################################################################################
                        # interfaces
                        m = re.match("interface (\S*)", line)
                        if m:
                            section = 'interface'
                            item = m.group(1)
                            if item not in cfg_int[sys_mac_addr].keys():
                                cfg_int[sys_mac_addr][item] = collections.OrderedDict(
                                    zip(item_int_cfg, [''] * len(item_int_cfg)))
                                cfg_int[sys_mac_addr][item]["Zone"] = zone
                                cfg_int[sys_mac_addr][item]["Sys MAC addr"] = sys_mac_addr
                                cfg_int[sys_mac_addr][item]['Hostname'] = hostname
                                cfg_int[sys_mac_addr][item]['Model'] = switch_model
                                cfg_int[sys_mac_addr][item]["EOS version"] = eos_version
                                cfg_int[sys_mac_addr][item]['interface'] = item
                                cfg_int[sys_mac_addr][item]['type'] = re.split('\d', item)[0]
                                cfg_int[sys_mac_addr][item]['number'] = re.split('\D+', item, 1)[1]
                                if item == "Vxlan1":
                                    r_vx.append(line)
                                continue

                        if section == 'interface' and cfg_int[sys_mac_addr][item]['interface'] == "Vxlan1":
                            m = re.search("\s+vxlan source-interface (\w+)", line)
                            if m:
                                cfg_int[sys_mac_addr]["Vxlan1"]['vxlan source-interface'] = m.group(1)
                            m = re.search("\s+(vxlan controller-client)$", line)
                            if m:
                                cfg_int[sys_mac_addr]['Vxlan1']['vxlan controller-client'] = m.group(1)
                            m = re.search("\s+vxlan udp-port (\d+)", line)
                            if m:
                                cfg_int[sys_mac_addr]["Vxlan1"]['vxlan udp-port'] = m.group(1)
                            if line == '!\n':
                                cfg_runconfig[sys_mac_addr]['interface Vxlan1'] = ''.join(r_vx)
                                cfg_longconfig[sys_mac_addr]['interface Vxlan1'] = ''.join(r_vx)
                                section = ''
                                continue
                            r_vx.append(line)
                            continue

                        if section == 'interface':
                            if line == '!\n':
                                section = ''
                                continue
                            m = re.search("\s+description (.*)", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['description'] = m.group(1)
                                continue
                            m = re.search("\s+switchport mode (\w*)", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['switchport mode'] = m.group(1)
                                continue
                            m = re.search("\s+switchport access vlan (\d+)", line)
                            if m:
                                cfg_int[sys_mac_addr][item]["access vlan"] = m.group(1)
                                continue
                            m = re.search("\s+switchport trunk allowed vlan (.*)", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['allowed vlan'] = m.group(1)
                                continue
                            m = re.search("\s+spanning-tree portfast$", line)
                            if m:
                                cfg_int[sys_mac_addr][item]["portfast"] = "auto"
                                continue
                            m = re.search("\s+spanning-tree portfast (\S+)", line)
                            if m:
                                cfg_int[sys_mac_addr][item]["portfast"] = m.group(1)
                                continue
                            m = re.search("\s+mlag (\S*)", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['mlag id'] = m.group(1)
                                continue
                            m = re.search("\s+no switchport", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['no switchport'] = "no switchport"
                                continue
                            m = re.search("\s+shutdown", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['shutdown'] = "shutdown"
                                continue
                            m = re.search("\s+ip address (\d+\.\d+\.\d+\.\d+)[/](\d+)$", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['ip address'] = m.group(1)
                                cfg_int[sys_mac_addr][item]['subnet mask'] = m.group(2)
                                continue
                            m = re.search("\s+ip virtual-router address (\d+\.\d+\.\d+\.\d+)$", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['VIP'] = m.group(1)
                                cfg_int[sys_mac_addr][item]['Fhrp mode'] = "vARP"
                                continue
                            m = re.search("\s+vrrp (\d+) ip (\d+\.\d+\.\d+\.\d+)$", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['VIP'] = m.group(2)
                                cfg_int[sys_mac_addr][item]['Fhrp mode'] = "VRRP"
                                cfg_int[sys_mac_addr][item]['VRRP ID'] = m.group(1)
                                continue
                            m = re.search("\s+channel-group (\S*) mode (\S+)", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['channel-group'] = m.group(1)
                                cfg_int[sys_mac_addr][item]['channel-mode'] = m.group(2)
                                continue
                            m = re.search("\s+no autostate$", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['no autostate'] = "no autostate"
                                continue
                            m = re.search("\s+vmtracer (.+)", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['vmtracer'] = m.group(1)
                                continue
                            m = re.search("\s+storm-control broadcast (.+)", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['storm-control broadcast'] = m.group(1)
                                continue
                            m = re.search("\s+storm-control multicast (.+)", line)
                            if m:
                                cfg_int[sys_mac_addr][item]['storm-control multicast'] = m.group(1)
                                continue

                    ###########################################################################################################################

                        m = re.match("router bgp (.*)", line)
                        if m:
                            section = "router bgp"
                            item = m.group(1)
                            r_bgp.append(line)
                            cfg_basic[sys_mac_addr]['Local AS'] = float(item)
            ###                    info_system[sys_mac_addr]['Local AS'] = float(item)
                            continue
                        if section == "router bgp":
                            if line == '!\n':
                                section = ''
                                cfg_runconfig[sys_mac_addr]['router bgp'] = ''.join(r_bgp)
                                cfg_longconfig[sys_mac_addr]['router bgp'] = ''.join(r_bgp)
                                continue
                            m = re.search("\s+router-id (.*)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['Router ID'] = m.group(1)
            ###                        info_system[sys_mac_addr]['Router ID'] = m.group(1)
                            m = re.search("\s+timers bgp (.*)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['timers bgp'] = m.group(1)
                            m = re.search("\s+maximum-(paths .*)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['maximum-paths'] = m.group(1)
                            m = re.search("\sbgp asn notation (.*)", line)
                            if m:
                                cfg_basic[sys_mac_addr]['bgp asn notation'] = m.group(1)
                            r_bgp.append(line)
                            continue

                    ###########################################################################################################################
                    if command == 'show clock' and sys_mac_addr != '':
                        m = re.search("(\S+\s\S+\s+\d+\s+\d+:\d+:\d+\s\d+)", line)
                        if m:
                            # print(m.group(1)[-4:])
                            if int(m.group(1)[-4:]) >= expire_year:
                                print("Please contact me if you want to continue using this program !! ")
                                time.sleep(10)
                                os.system('pause')
                                sys.exit()
                            info_system[sys_mac_addr]['Cur clock'] = m.group(1)
                            continue
                        m = re.match("Timezone:\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Timezone'] = m.group(1)
                            continue
                        m = re.match("Clock source:\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Clock source'] = m.group(1)
                            continue

                    ###########################################################################################################################
                    if command == 'show ntp status' and sys_mac_addr != '':
                        m = re.match("(\w*synchronised\s*.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Timesynch'] = m.group(1)
                            continue
                        m = re.match("(NTP is disabled.)", line)
                        if m:
                            info_system[sys_mac_addr]['Timesynch'] = m.group(1)
                            continue

                    ###########################################################################################################################
                    if command == 'show logging' and sys_mac_addr != '':
                        m = re.match("Syslog logging:\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Syslog logging'] = m.group(1)
                            continue
                        # m = re.search("\s+Buffer logging:\s+(.*)", line) +를 *변경
                        m = re.search("\s*Buffer logging:\s+(.*)", line)                
                        if m:
                            info_system[sys_mac_addr]['Buffer logging'] = m.group(1)
                            continue
                        m = re.search("\s*Console logging:\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Console logging'] = m.group(1)
                            continue
                        m = re.search("\s*Monitor logging:\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Monitor logging'] = m.group(1)
                            continue
                        m = re.search("\s*Synchronous logging:\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Synchronous logging'] = m.group(1)
                            continue
                        m = re.search("\s*Trap logging:\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Trap logging'] = m.group(1)
                            continue
                        m = re.search("\s*Logging to '(\d+\.\d+\.\d+\.\d+)' port (\w+) in VRF (\w+) via udp", line)
                        if m:
                            if info_system[sys_mac_addr]['Loghost1'] == "":
                                info_system[sys_mac_addr]['Loghost1'] = m.group(1) + " " + m.group(2) + " " + m.group(3)
                            else:
                                info_system[sys_mac_addr]['Loghost2'] = m.group(1) + " " + m.group(2) + " " + m.group(3)
                            continue
                        m = re.search("\s*Syslog facility:\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Syslog facility'] = m.group(1)
                            continue
                        m = re.search("\s*Hostname format:\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Hostname format'] = m.group(1)
                            continue
                        m = re.search("\s*Repeat logging interval:\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Repeat logging interval'] = m.group(1)
                            continue
                        m = re.search("\s*Repeat messages:\s+(.*)", line)
                        if m:
                            info_system[sys_mac_addr]['Repeat messages'] = m.group(1)
                            continue

                    ###########################################################################################################################
                    # if command == 'show interfaces' and sys_mac_addr != '':
                    if command in ('show interfaces','show interfaces all') and sys_mac_addr != '':
                        m = re.search("^(\S+) is ([\w|\s]+), line protocol is (\w+) \((\w+)\)", line)
                        if m:
                            item = m.group(1)
                            if item not in info_int[sys_mac_addr].keys():
                                info_int[sys_mac_addr][item] = collections.OrderedDict(
                                    zip(item_int, [''] * len(item_int)))
                                info_int[sys_mac_addr][item]["Zone"] = zone
                                info_int[sys_mac_addr][item]['Hostname'] = hostname
                                info_int[sys_mac_addr][item]["Sys MAC addr"] = sys_mac_addr
                                info_int[sys_mac_addr][item]['Model'] = switch_model
                                info_int[sys_mac_addr][item]["EOS version"] = eos_version
                                info_int[sys_mac_addr][item]['interface'] = item
                                info_int[sys_mac_addr][item]['type'] = re.split('\d', item)[0]
                                info_int[sys_mac_addr][item]['number'] = re.split('\D+', item, 1)[1]
                            info_int[sys_mac_addr][item]['int status'] = m.group(2)
                            info_int[sys_mac_addr][item]['line protocol'] = m.group(3)
                            info_int[sys_mac_addr][item]['status'] = m.group(4)
                            continue
                        m = re.search("\s+Hardware is (.+), address is ([\w|\.]+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Hardware'] = m.group(1)
                            info_int[sys_mac_addr][item]['mac address'] = m.group(2)
                            continue
                        m = re.search("\s+Description: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['description'] = m.group(1)
                            continue
                        m = re.search("\s+Internet address is ([\d|\.]+)\/(\d+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Internet address'] = m.group(1)
                            info_int[sys_mac_addr][item]['Mask bits'] = int(m.group(2))
                            info_int[sys_mac_addr][item]['Mask'] = masks[int(m.group(2))]
                            continue
                        m = re.search("\s+ Member of (.*)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Member of Port-Channel'] = m.group(1)
                            continue
                        m = re.search("\s+ Ethernet MTU (\d+) bytes , BW (\d+) kbit", line)
                        if m:
                            info_int[sys_mac_addr][item]['MTU'] = int(m.group(1))
                            info_int[sys_mac_addr][item]['BW'] = int(m.group(2))
                            continue
                        m = re.search("\s+IP MTU (\d+) bytes", line)                     # loopback , vlan 인터페이스 BW 가 없어 구분
                        if m:
                            info_int[sys_mac_addr][item]['MTU'] = int(m.group(1))
                            m = re.search("\s*bytes , BW (\d+) kbit", line)
                            if m:
                                info_int[sys_mac_addr][item]['BW'] = int(m.group(1))
                                continue
                        m = re.search("\s+(\w+)-duplex,", line)
                        if m:
                            info_int[sys_mac_addr][item]['duplex'] = m.group(1)
                            m = re.search("(\d+Gb/s),", line)
                            if m:
                                info_int[sys_mac_addr][item]['speed'] = m.group(1)
                            m = re.search("(\d+\wb/s),", line)
                            if m:
                                info_int[sys_mac_addr][item]['speed'] = m.group(1)
                            m = re.search("auto negotiation: (\w+),", line)
                            if m:
                                info_int[sys_mac_addr][item]['auto negotiation'] = m.group(1)
                            m = re.search("uni-link: (\S+)", line)
                            if m:
                                info_int[sys_mac_addr][item]['uni-link'] = m.group(1)
                                continue
                        m = re.search("\s+Active members? in this channel: (\d+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Active members in this channel'] = int(m.group(1))
                            continue
                        m = re.search("\s+\.+\s(\S+) , Full-duplex, \s*\d+\wb/s", line)
                        if m:
                            if z == 0:
                                info_int[sys_mac_addr][item]['member int1'] = m.group(1)
                            elif z == 1:
                                info_int[sys_mac_addr][item]['member int2'] = m.group(1)
                            elif z == 2:
                                info_int[sys_mac_addr][item]['member int3'] = m.group(1)
                            elif z == 3:
                                info_int[sys_mac_addr][item]['member int4'] = m.group(1)
                            else:
                                continue
                            z = z + 1
                            continue
                        m = re.search("\s+Fallback mode is: (\w+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Fallback mode'] = m.group(1)
                            z = 0
                            continue
                        m = re.search("\s+Loopback Mode : (\w+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Loopback Mode'] = m.group(1)
                            continue
                        m = re.search("\s+(\d+) link status changes since last clear", line)
                        if m:
                            info_int[sys_mac_addr][item]['link status changes since last clear'] = int(m.group(1))
                            continue
                        #                m = re.search("(^  'Up|Down' \d* days?|hours?|minutes?|seconds?.+)", line)
                        m = re.search("^  (Up .+|Down .+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['status time'] = m.group(1)
                            continue
                        m = re.search("\s+Last clearing of \"show interface\" counters? (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Last clearing'] = m.group(1)
                            continue
                        # m = re.search("\s+(\d+ minutes|\d+ seconds) input rate", line) load-interval 0 일 경우 초 분이 없음
                        m = re.search("\s+(\d+ minutes|\d+ seconds|\s+) input rate", line)
                        if m:
                            info_int[sys_mac_addr][item]['input rate'] = m.group(1)
                            m = re.search(" (minutes|seconds|\s+) input rate (.+ \w?bps)", line)
                            if m:
                                info_int[sys_mac_addr][item]['input rate bps'] = m.group(2)
                            m = re.search(" (minutes|seconds|\s+) input rate .+ \w?bps \((\d+\.\d+)%.+", line)
                            if m:
                                info_int[sys_mac_addr][item]['input rate %'] = float(m.group(2))
                            m = re.search(" (minutes|seconds|\s+) input rate .+ (\d+) packets/sec", line)
                            if m:
                                info_int[sys_mac_addr][item]['input packet/sec'] = int(m.group(2))
                                continue
                        m = re.search("\s+(\d+ minutes|\d+ seconds|\s+) output rate", line)
                        if m:
                            info_int[sys_mac_addr][item]['output rate'] = m.group(1)
                            m = re.search(" (minutes|seconds|\s+) output rate (.+ \w?bps)", line)
                            if m:
                                info_int[sys_mac_addr][item]['output rate bps'] = m.group(2)
                            m = re.search(" (minutes|seconds|\s+) output rate .+ \w?bps \((\d+\.\d+)%.+", line)
                            if m:
                                info_int[sys_mac_addr][item]['output rate %'] = float(m.group(2))
                            m = re.search(" (minutes|seconds|\s+) output rate .+ (\d+) packets/sec", line)
                            if m:
                                info_int[sys_mac_addr][item]['output packet/sec'] = int(m.group(2))
                                continue
                        m = re.search("\s+(\d+) packets input, (\d+) bytes", line)
                        if m:
                            info_int[sys_mac_addr][item]['input packets'] = int(m.group(1))
                            info_int[sys_mac_addr][item]['input bytes'] = int(m.group(2))
                        m = re.search("\s+Received (\d+) broadcasts, (\d+) multicast", line)
                        if m:
                            info_int[sys_mac_addr][item]['Received broadcasts'] = int(m.group(1))
                            info_int[sys_mac_addr][item]['Received multicast'] = int(m.group(2))
                        m = re.search("\s+(\d+) runts, (\d+) giants", line)
                        if m:
                            info_int[sys_mac_addr][item]['runts'] = int(m.group(1))
                            info_int[sys_mac_addr][item]['giants'] = int(m.group(2))
                        m = re.search("(\d+) input errors", line)
                        if m:
                            info_int[sys_mac_addr][item]['input errors'] = int(m.group(1))
                            m = re.search("(\d+) CRC", line)
                            if m:
                                info_int[sys_mac_addr][item]['CRC'] = int(m.group(1))
                            m = re.search("(\d+) alignment", line)
                            if m:
                                info_int[sys_mac_addr][item]['alignment'] = int(m.group(1))
                            m = re.search("(\d+) symbol", line)
                            if m:
                                info_int[sys_mac_addr][item]['symbol'] = int(m.group(1))
                            m = re.search("(\d+) input discards", line)
                            if m:
                                info_int[sys_mac_addr][item]['input discards'] = int(m.group(1))
                                continue
                        m = re.search("(\d+) PAUSE input", line)
                        if m:
                            info_int[sys_mac_addr][item]['PAUSE input'] = int(m.group(1))
                            continue
                        m = re.search("\s+(\d+) packets output, (\d+) bytes", line)
                        if m:
                            info_int[sys_mac_addr][item]['output packets'] = int(m.group(1))
                            info_int[sys_mac_addr][item]['output bytes'] = int(m.group(2))
                        m = re.search("\s+Sent (\d+) broadcasts, (\d+) multicast", line)
                        if m:
                            info_int[sys_mac_addr][item]['Sent broadcasts'] = int(m.group(1))
                            info_int[sys_mac_addr][item]['Sent multicast'] = int(m.group(2))
                        m = re.search("(\d+) output errors", line)
                        if m:
                            info_int[sys_mac_addr][item]['output errors'] = int(m.group(1))
                            m = re.search("(\d+) collisions", line)
                            if m:
                                info_int[sys_mac_addr][item]['collisions'] = int(m.group(1))
                            m = re.search("(\d+) output discards", line)                            ## port channel 은 output error 과 discard가 같은 줄에 있음
                            if m:
                                info_int[sys_mac_addr][item]['output discards'] = int(m.group(1))
                                continue
                        m = re.search("(\d+) late collision", line)
                        if m:
                            info_int[sys_mac_addr][item]['late collision'] = int(m.group(1))
                            m = re.search("(\d+) deferred", line)
                            if m:
                                info_int[sys_mac_addr][item]['deferred'] = int(m.group(1))
                            m = re.search("(\d+) output discards", line)
                            if m:
                                info_int[sys_mac_addr][item]['output discards'] = int(m.group(1))
                                continue
                        m = re.search("(\d+) PAUSE output", line)
                        if m:
                            info_int[sys_mac_addr][item]['PAUSE output'] = int(m.group(1))
                            continue
                        m = re.search("Source interface is (\S+) and is active with (\d+\.\d+\.\d+\.\d+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['vxlan Source interface'] = m.group(1)
                            info_int[sys_mac_addr][item]['vxlan Source ip'] = m.group(2)
                            continue
                        m = re.search("Replication/Flood Mode is headend with Flood List Source: (\S+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Flood List Source'] = m.group(1)
                            continue
                        m = re.search("Remote MAC learning via (\S+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Remote MAC learning'] = m.group(1)
                            continue

                    #####################################################################################################################
                    #if command == 'show env cooling' and sys_mac_addr != '':
                    if command in ('show env cooling', 'show system env cooling') and sys_mac_addr != '':
                        m = re.search("^System cooling status is: (\S+)", line)
                        if m:
                            info_system[sys_mac_addr]['Cooling'] = m.group(1)
                            continue
                        m = re.search("^Ambient temperature: (\S+)", line)
                        if m:
                            if "C" in m.group(1):
                                info_system[sys_mac_addr]['Ambient temperature'] = int(m.group(1).split("C")[0])
                            else:
                                info_system[sys_mac_addr]['Ambient temperature'] = m.group(1)
                            continue
                        m = re.search("^Airflow: (.+)", line)
                        if m:
                            info_system[sys_mac_addr]['Airflow'] = m.group(1)
                            continue

                    #####################################################################################################################
                    #if command == 'show env temperature' and sys_mac_addr != '':
                    if command in ('show env temperature', 'show system env temperature') and sys_mac_addr != '':
                        m = re.search("^System temperature status is: (\S+)", line)
                        if m:
                            info_system[sys_mac_addr]['Temperature'] = m.group(1)
                            continue

                    #####################################################################################################################
                    if command == 'show inventory' and sys_mac_addr != '':
                        m = re.search("^  (DCS-.+\w)  \s+\w+", line)
                        if m:
                            switch_model_except_RF = m.group(1)
                            continue
                        m = re.search("^System has (\d+) power supply slots", line)
                        if m:
                            info_system[sys_mac_addr]['Power supply slots'] = int(m.group(1))
                            continue
                        m = re.search("^System has (\d+) fan modules", line)
                        if m:
                            info_system[sys_mac_addr]['Fan modules'] = int(m.group(1))
                            continue
                        m = re.search("^System has (\d+) ports", line)
                        if m:
                            info_system[sys_mac_addr]['Ports'] = int(m.group(1))
                            continue
                        m = re.search("^System has (\d+) transceiver slots", line)
                        if m:
                            info_system[sys_mac_addr]['Transceiver slots'] = int(m.group(1))
                            continue

                        m = re.search("  ---- ---------------- ---------------- ---------------- ----", line)  # tranceiver serial
                        if m:
                            section = "transceiver_serial"
                            continue
                        if section == "transceiver_serial":
                            if line == '\n':
                                section = ''
                                continue

            #                    if serial_number == line[41:57].strip():                # UTP 포트의 경우 스위치 시리얼이 나오는듯 해당 포트 제외, EOS-4.20.11 에서는 시리얼이 안나옴
            #                        continue
                            if switch_model_except_RF == line[24:40].strip():        # UTP 포트의 경우 모델에 스위치 모델명이 나옴
                                continue

                            m = re.search("^  (\S+) ", line)
                            if m:
                                number = m.group(1)
                                item = "Ethernet"+number                            # TOR은 숫자로 Ethernet 포트넘버만 나옴, 모듈형은 슬롯/포트넘버가 나옴, breakout 포트 없음

                                if item not in info_transceiver_serial[sys_mac_addr].keys():
                                    info_transceiver_serial[sys_mac_addr][item] = collections.OrderedDict(zip(item_transceiver_serial, [''] * len(item_transceiver_serial)))
                                    info_transceiver_serial[sys_mac_addr][item]['Zone'] = zone
                                    info_transceiver_serial[sys_mac_addr][item]['Hostname'] = hostname
                                    info_transceiver_serial[sys_mac_addr][item]['Sys MAC addr'] = sys_mac_addr
                                    info_transceiver_serial[sys_mac_addr][item]['Model'] = switch_model
                                    info_transceiver_serial[sys_mac_addr][item]['EOS version'] = eos_version
                                    info_transceiver_serial[sys_mac_addr][item]['interface'] = item
                                    info_transceiver_serial[sys_mac_addr][item]['type'] = re.split('\d', item)[0]
                                    info_transceiver_serial[sys_mac_addr][item]['number'] = re.split('\D+', item, 1)[1]
                                info_transceiver_serial[sys_mac_addr][item]['Manufacturer'] = line[6:23].strip()
                                info_transceiver_serial[sys_mac_addr][item]['T-Model'] = line[24:40].strip()
                                info_transceiver_serial[sys_mac_addr][item]['T-Serial'] = line[41:57].strip()

                                if item not in info_int[sys_mac_addr].keys():               # 기본적으로 모든 포트에 "/1-4" 가 없다. 없다면 맨뒤 /1 을 추가
                                    item = item + "/1"
                                    if item not in info_int[sys_mac_addr].keys():
                                        continue
                                    info_int[sys_mac_addr][item]['Manufacturer'] = line[6:23].strip()
                                    info_int[sys_mac_addr][item]['T-Model'] = line[24:40].strip()
                                    info_int[sys_mac_addr][item]['T-Serial'] = line[41:57].strip()
                                else:
                                    info_int[sys_mac_addr][item]['Manufacturer'] = line[6:23].strip()
                                    info_int[sys_mac_addr][item]['T-Model'] = line[24:40].strip()
                                    info_int[sys_mac_addr][item]['T-Serial'] = line[41:57].strip()
                                continue

                    #####################################################################################################################
                    if command == 'dir /recursive flash:' and sys_mac_addr != '':

                        m = re.search("(\S+) bytes total [(](\S+) bytes free[)]", line)
                        if m:
                            info_system[sys_mac_addr]['Total flash'] = int(m.group(1)) / 1024
                            info_system[sys_mac_addr]['Free flash'] = int(m.group(2)) / 1024
                            info_system[sys_mac_addr]['Flash %'] = round(((1 - info_system[sys_mac_addr]['Free flash'] / info_system[sys_mac_addr]['Total flash']) * 100), 2)
                            continue

                    #####################################################################################################################
                    if command == 'show processes top once' and sys_mac_addr != '':

                        m = re.search(" load average: \S+, (\S+), \S+", line)
                        if m:
                            info_system[sys_mac_addr]['CPU % 5min'] = float(m.group(1))
                            continue


                    #####################################################################################################################
                    if command == 'show mlag detail' and sys_mac_addr != '':

                        m = re.match("domain-id \s+: (.+\w)", line)
                        if m:
                            section = "mlag"
                            if sys_mac_addr not in info_mlag.keys():
                                mlag_domain_id = m.group(1).strip()
                                info_mlag[sys_mac_addr] = collections.OrderedDict(zip(item_mlag, [''] * len(item_mlag)))
                                info_mlag[sys_mac_addr]["Sys MAC addr"] = sys_mac_addr
                                info_mlag[sys_mac_addr]["Zone"] = zone
                                info_mlag[sys_mac_addr]['Hostname'] = hostname
                                info_mlag[sys_mac_addr]['Model'] = switch_model
                                info_mlag[sys_mac_addr]['EOS version'] = eos_version
                                info_mlag[sys_mac_addr]['domain-id'] = m.group(1).strip()
                                info_system[sys_mac_addr]['mlag config'] = m.group(1).strip()
                                continue
                        if section == 'mlag':
                            m = re.match("local-interface \s+: (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['local-interface'] = m.group(1).strip()
                                continue
                            m = re.match("peer-address \s+: (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['peer-address'] = m.group(1).strip()
                                continue
                            m = re.match("peer-link \s+: (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['peer-link'] = m.group(1).strip()
                                continue
                            m = re.match("hb-peer-address \s+: (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['hb-peer-address'] = m.group(1).strip()
                                continue
                            m = re.match("peer-config \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['peer-config'] = m.group(1).strip()
                                continue
                            m = re.search("state \s+ : \s+ (.+)", line)
                            if m and z == 0:
                                z = z + 1
                                info_mlag[sys_mac_addr]['state1'] = m.group(1).strip()
                                continue
                            m = re.search("negotiation status \s+:\s+(.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['negotiation status'] = m.group(1)
                                continue
                            m = re.search("peer-link status \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['peer-link status'] = m.group(1).strip()
                                continue
                            m = re.search("local-int status \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['local-int status'] = m.group(1).strip()
                                continue
                            m = re.search("system-id \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['system-id'] = m.group(1).strip()
                                continue
                            m = re.search("dual-primary detection : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['dual-primary detection'] = m.group(1).strip()
                                continue
                            m = re.search("Disabled \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Disabled'] = int(m.group(1))
                                continue
                            m = re.search("Configured \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Configured'] = int(m.group(1))
                                continue
                            m = re.search("Inactive \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Inactive'] = int(m.group(1))
                                continue
                            m = re.search("Active-partial \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Active-partial'] = int(m.group(1))
                                continue
                            m = re.match("Active-full \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Active-full'] = int(m.group(1))
                                continue
                            m = re.match("State \s+ : (.+)", line)
                            if m and z == 1:
                                z = z + 1
                                info_mlag[sys_mac_addr]['State2'] = m.group(1).strip()
                                continue
                            m = re.match("Peer State  \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Peer State'] = m.group(1).strip()
                                continue
                            m = re.match("primary-priority \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['primary-priority'] = m.group(1).strip()
                                continue
                            m = re.match("Peer MAC address \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Peer MAC address'] = m.group(1).strip()
                                continue
                            m = re.match("Peer MAC routing supported \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Peer MAC routing supported'] = m.group(1).strip()
                                continue
                            m = re.match("Reload delay  \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Reload delay'] = m.group(1).strip()
                                continue
                            m = re.match("Non-MLAG reload delay \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Non-MLAG reload delay'] = m.group(1).strip()
                                continue
                            m = re.match("Configured heartbeat interval \s+: (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Configured heartbeat interval'] = m.group(1).strip()
                                continue
                            m = re.match("Effective heartbeat interval \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Effective heartbeat interval'] = m.group(1).strip()
                                continue
                            m = re.match("Heartbeat timeout \s+ : (.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Heartbeat timeout'] = m.group(1).strip()
                                continue
                            m = re.match("Fast MAC redirection enabled \s+ : \s+(.+)", line)
                            if m:
                                info_mlag[sys_mac_addr]['Fast MAC redirection enabled'] = m.group(1).strip()
                                continue

                    #####################################################################################################################
                    # if command == 'show interfaces status' and sys_mac_addr != '':
                    if command in ('show interfaces status','show interfaces all status') and sys_mac_addr != '':
                        m = re.match("(\S+) .+ (connected|notconnect|disabled|errdisabled)\s* (Not bridged|in \w+|\w+)\s* ([a-zA-Z0-9][\w-]*)\s* ([a-zA-Z0-9][\w-]*)\s* (\w.+)", line)
                        if m:
                            item = re.split('\d', m.group(1))[0]
                            number = re.split('\D+', m.group(1), 1)[1]
                            item = self.expand(item, int_dict)
                            if item is not None:
                                item = item + number
                                if item not in info_int[sys_mac_addr].keys():
                                    info_int[sys_mac_addr][item] = collections.OrderedDict(zip(item_int, [''] * len(item_int)))
                                    info_int[sys_mac_addr][item]["Zone"] = zone
                                    info_int[sys_mac_addr][item]['Hostname'] = hostname
                                    info_int[sys_mac_addr][item]["Sys MAC addr"] = sys_mac_addr
                                    info_int[sys_mac_addr][item]['Model'] = switch_model
                                    info_int[sys_mac_addr][item]["EOS version"] = eos_version
                                    info_int[sys_mac_addr][item]['interface'] = item
                                    info_int[sys_mac_addr][item]['type'] = re.split('\d', item)[0]
                                    info_int[sys_mac_addr][item]['number'] = re.split('\D+', item, 1)[1]
                                info_int[sys_mac_addr][item]['sis Status'] = m.group(2)
                                info_int[sys_mac_addr][item]['sis Vlan'] = m.group(3)
                                info_int[sys_mac_addr][item]['sis Duplex'] = m.group(4)
                                info_int[sys_mac_addr][item]['sis Speed'] = m.group(5)
                                info_int[sys_mac_addr][item]['sis Media type'] = m.group(6)
                                continue

                    #####################################################################################################################
                    if command == 'show mac address-table' and sys_mac_addr != '':
                        m = re.search("Total Mac Addresses for this criterion:\s*(.*)", line)
                        if m and z == 0:
                            z = z + 1
                            info_system[sys_mac_addr]['Total Mac Addresses'] = int(m.group(1))
                            continue

                    #####################################################################################################################
                    if command == 'show interfaces switchport' and sys_mac_addr != '':
                        m = re.match("Default switchport mode: (\S+)", line)
                        if m:
                            info_system[sys_mac_addr]['Default switchport mode'] = m.group(1)
                            continue
                        m = re.match("Name: (\S+)", line)
                        if m:
                            t_item = m.group(1)
                            t_type = re.split('\d', t_item)[0]
                            t_number = re.split('\D+', t_item, 1)[1]
                            item = self.expand(t_type, int_dict)
                            if item is not None:
                                item = item + t_number
                                if item not in info_int[sys_mac_addr].keys():
                                    info_int[sys_mac_addr][item] = collections.OrderedDict(
                                        zip(item_int, [''] * len(item_int)))
                                    info_int[sys_mac_addr][item]["Zone"] = zone
                                    info_int[sys_mac_addr][item]['Hostname'] = hostname
                                    info_int[sys_mac_addr][item]["Sys MAC addr"] = sys_mac_addr
                                    info_int[sys_mac_addr][item]['Model'] = switch_model
                                    info_int[sys_mac_addr][item]["EOS version"] = eos_version
                                    info_int[sys_mac_addr][item]['interface'] = item
                                    info_int[sys_mac_addr][item]['type'] = re.split('\d', item)[0]
                                    info_int[sys_mac_addr][item]['number'] = re.split('\D+', item, 1)[1]
                                    continue
                        m = re.search("Switchport: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Switchport'] = m.group(1)
                            continue
                        m = re.search("Administrative Mode: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Administrative Mode'] = m.group(1)
                            continue
                        m = re.search("Operational Mode: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Operational Mode'] = m.group(1)
                            continue
                        m = re.search("MAC Address Learning: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['MAC Address Learning'] = m.group(1)
                            continue
                        m = re.search("Dot1q ethertype/TPID: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Dot1q ethertype/TPID'] = m.group(1)
                            continue
                        m = re.search("Dot1q Vlan Tag Required \(Administrative/Operational\): (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Dot1q Vlan Tag Required (Administrative/Operational)'] = m.group(1)
                            continue
                        m = re.search("Access Mode VLAN: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Access Mode VLAN'] = m.group(1)
                            continue
                        m = re.search("Trunking Native Mode VLAN: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Trunking Native Mode VLAN'] = m.group(1)
                            continue
                        m = re.search("Administrative Native VLAN tagging: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Administrative Native VLAN tagging'] = m.group(1)
                            continue
                        m = re.search("Trunking VLANs Enabled: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Trunking VLANs Enabled'] = m.group(1)
                            continue
                        m = re.search("Static Trunk Groups: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Static Trunk Groups'] = m.group(1)
                            continue
                        m = re.search("Dynamic Trunk Groups: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Dynamic Trunk Groups'] = m.group(1)
                            continue
                        m = re.search("Source interface filtering: (.+)", line)
                        if m:
                            info_int[sys_mac_addr][item]['Source interface filtering'] = m.group(1)
                            continue

                    #####################################################################################################################
                    if command == 'show lldp neighbors detail' and sys_mac_addr != '':

                        m = re.search("Interface (\S+) detected (\d+) LLDP neighbors:", line)
                        if m:
                            local_int = m.group(1)
                            lldp_count = int(m.group(2))
                            continue
                        m = re.search("Discovered (.+ ago); Last changed (.+ ago)", line)
                        if m:
                            discovered_time = m.group(1)
                            last_changed_time = m.group(2)
                            continue
                        m = re.search("Chassis ID type: (.*)", line)
                        if m:
                            remote_chassis_id_type = m.group(1)
                            continue
                        m = re.search("Chassis ID \s+ : \"?(.*\w)\"?", line)
                        if m:
                            remote_chassis_id = m.group(1)
                            continue
                        m = re.search("Port ID type: (.*)", line)
                        if m:
                            remote_int_type = m.group(1)
                            continue
                        m = re.search("Port ID     : \"?(.*\w)\"?", line)
                        if m:
                            remote_int = m.group(1)
                            if (sys_mac_addr + local_int + remote_chassis_id) not in info_lldp.keys():
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id] = collections.OrderedDict()
                            else:
                                print(info_lldp[sys_mac_addr + local_int + remote_chassis_id].keys())

                            if remote_int not in info_lldp[sys_mac_addr + local_int + remote_chassis_id].keys():
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int] = collections.OrderedDict(zip(item_lldp, [''] * len(item_lldp)))
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Zone'] = zone
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Hostname'] = hostname
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Sys MAC addr'] = sys_mac_addr
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Model'] = switch_model
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['EOS version'] = eos_version
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['type'] = re.split('\d', local_int)[0]
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['number'] = re.split('\D+', local_int, 1)[1]

                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Local interface'] = local_int
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['LLDP count'] = lldp_count
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Remote Port ID type'] = remote_int_type
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Remote Port ID'] = remote_int
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Remote Chassis ID type'] = remote_chassis_id_type
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Remote Chassis ID'] = remote_chassis_id
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Discovered'] = discovered_time
                                info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Last changed'] = last_changed_time
                                continue
                        m = re.search("\- Port Description: \"(.+)\"", line)    # " " 묶음
                        if m:
                            info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Remote Port Description'] = m.group(1)
                            continue
                        m = re.search("\- System Name: \"(.+)\"", line)         # " " 묶음
                        if m:
                            info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int]['Remote System Name'] = m.group(1)
                            continue
                        m = re.search("Management Address \s+ : (\w[\w|\.]+\w)", line)
                        if m:
                            info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int][
                                'Remote Management Address'] = m.group(1)
                            continue
                        m = re.search("\- IEEE802.1 Port VLAN ID: (\d+)", line)
                        if m:
                            info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int][
                                'Remote IEEE802.1 Port VLAN ID'] = m.group(1)
                            continue
                        m = re.search("Link Aggregation Status: (.+)", line)
                        if m:
                            info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int][
                                'Link Aggregation Status'] = m.group(1)
                            continue
                        m = re.search("IEEE802.3 Maximum Frame Size: (\d+ bytes)", line)
                        if m:
                            info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int][
                                'IEEE802.3 Maximum Frame Size'] = m.group(1)
                            continue
                        m = re.search("Operational MAU Type   : \"?(.+)\"?", line)
                        if m:
                            info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int][
                                'MAU Type'] = m.group(1)
                            continue
                        m = re.search("\- System Description: \"(.+)\"", line)      # " " 묶음
                        if m:
                            info_lldp[sys_mac_addr + local_int + remote_chassis_id][remote_int][
                                'Remote System Description'] = m.group(1)
                            continue

                    #####################################################################################################################
                    if command == 'show interfaces transceiver detail' and sys_mac_addr != '':

                        m = re.search("-------    ------------  ----------  ----------  ----------  ----------", line)
                        if m:
                            z = z + 1
                            continue
                        if z == 1:      # Temperature
                            m = re.match("(Et\S+) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A)", line)
                            if m:
                                item = re.split('\d', m.group(1))[0]
                                number = re.split('\D+', m.group(1), 1)[1]
                                item = self.expand(item, int_dict)
                                if item is not None:
                                    item = item + number
                                    if item not in info_transceiver[sys_mac_addr].keys():
                                        info_transceiver[sys_mac_addr][item] = collections.OrderedDict(zip(item_transceiver, [''] * len(item_transceiver)))
                                        info_transceiver[sys_mac_addr][item]['Zone'] = zone
                                        info_transceiver[sys_mac_addr][item]['Hostname'] = hostname
                                        info_transceiver[sys_mac_addr][item]['Sys MAC addr'] = sys_mac_addr
                                        info_transceiver[sys_mac_addr][item]['Model'] = switch_model
                                        info_transceiver[sys_mac_addr][item]['EOS version'] = eos_version
                                        info_transceiver[sys_mac_addr][item]['interface'] = item
                                        info_transceiver[sys_mac_addr][item]['type'] = re.split('\d', item)[0]
                                        info_transceiver[sys_mac_addr][item]['number'] = re.split('\D+', item, 1)[1]

                                        if "/" in m.group(2):   # "N/A" 부분
                                            info_transceiver[sys_mac_addr][item]['Temperature'] = m.group(2)
                                        else:
                                            info_transceiver[sys_mac_addr][item]['Temperature'] = float(m.group(2))
                                        if "/" in m.group(3):
                                            info_transceiver[sys_mac_addr][item]['T-HA'] = m.group(3)
                                        else:
                                            info_transceiver[sys_mac_addr][item]['T-HA'] = float(m.group(3))
                                        if "/" in m.group(4):
                                            info_transceiver[sys_mac_addr][item]['T-HW'] = m.group(4)
                                        else:
                                            info_transceiver[sys_mac_addr][item]['T-HW'] = float(m.group(4))
                                        if "/" in m.group(5):
                                            info_transceiver[sys_mac_addr][item]['T-LA'] = m.group(5)
                                        else:
                                            info_transceiver[sys_mac_addr][item]['T-LA'] = float(m.group(5))
                                        if "/" in m.group(6):
                                            info_transceiver[sys_mac_addr][item]['T-LW'] = m.group(6)
                                        else:
                                            info_transceiver[sys_mac_addr][item]['T-LW'] = float(m.group(6))

                                    if item not in info_int[sys_mac_addr].keys():           # 기본적으로 모든 포트에 "/1-4" 가 나온다, 없다면 맨뒤 /1 등을 제외
                                        item = item[:-2]
                                        if item not in info_int[sys_mac_addr].keys():       # /1,/2,/3,/4 제외된 포트가 없다면 아래 생략, /1은 있을 것으로 생각됨
                                            continue

                                    if "/" in m.group(2):
                                        info_int[sys_mac_addr][item]['Temperature'] = m.group(2)
                                    else:
                                        info_int[sys_mac_addr][item]['Temperature'] = float(m.group(2))
                                    continue

                        if z == 2:  # Voltage
                            m = re.match("(Et\S+) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A)", line)
                            if m:
                                item = re.split('\d', m.group(1))[0]
                                number = re.split('\D+', m.group(1), 1)[1]
                                item = self.expand(item, int_dict)
                                if item is not None:
                                    item = item + number
                                    if "/" in m.group(2):
                                        info_transceiver[sys_mac_addr][item]['Voltage'] = m.group(2)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['Voltage'] = float(m.group(2))
                                    if "/" in m.group(3):
                                        info_transceiver[sys_mac_addr][item]['V-HA'] = m.group(3)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['V-HA'] = float(m.group(3))
                                    if "/" in m.group(4):
                                        info_transceiver[sys_mac_addr][item]['V-HW'] = m.group(4)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['V-HW'] = float(m.group(4))
                                    if "/" in m.group(5):
                                        info_transceiver[sys_mac_addr][item]['V-LA'] = m.group(5)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['V-LA'] = float(m.group(5))
                                    if "/" in m.group(6):
                                        info_transceiver[sys_mac_addr][item]['V-LW'] = m.group(6)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['V-LW'] = float(m.group(6))

                                    if item not in info_int[sys_mac_addr].keys():           # 기본적으로 모든 포트에 "/1-4" 가 나온다, 없다면 맨뒤 /1 등을 제외
                                        item = item[:-2]
                                        if item not in info_int[sys_mac_addr].keys():       # /1,/2,/3,/4 제외된 포트가 없다면 아래 생략, /1은 있을 것으로 생각됨
                                            continue

                                    if "/" in m.group(2):
                                        info_int[sys_mac_addr][item]['Voltage'] = m.group(2)
                                    else:
                                        info_int[sys_mac_addr][item]['Voltage'] = float(m.group(2))
                                    continue

                        if z == 3:      # Current
                            m = re.match("(Et\S+) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A)", line)
                            if m:
                                item = re.split('\d', m.group(1))[0]
                                number = re.split('\D+', m.group(1), 1)[1]
                                item = self.expand(item, int_dict)
                                if item is not None:
                                    item = item + number
                                    if "/" in m.group(2):
                                        info_transceiver[sys_mac_addr][item]['Current'] = m.group(2)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['Current'] = float(m.group(2))
                                    if "/" in m.group(3):
                                        info_transceiver[sys_mac_addr][item]['mA-HA'] = m.group(3)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['mA-HA'] = float(m.group(3))
                                    if "/" in m.group(4):
                                        info_transceiver[sys_mac_addr][item]['mA-HW'] = m.group(4)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['mA-HW'] = float(m.group(4))
                                    if "/" in m.group(5):
                                        info_transceiver[sys_mac_addr][item]['mA-LA'] = m.group(5)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['mA-LA'] = float(m.group(5))
                                    if "/" in m.group(6):
                                        info_transceiver[sys_mac_addr][item]['mA-LW'] = m.group(6)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['mA-LW'] = float(m.group(6))

                                    if item not in info_int[sys_mac_addr].keys():           # 기본적으로 모든 포트에 "/1-4" 가 나온다, 없다면 맨뒤 /1 등을 제외
                                        item = item[:-2]
                                        if item not in info_int[sys_mac_addr].keys():       # /1,/2,/3,/4 제외된 포트가 없다면 아래 생략, /1은 있을 것으로 생각됨
                                            continue

                                    if "/" in m.group(2):
                                        info_int[sys_mac_addr][item]['Current'] = m.group(2)
                                    else:
                                        info_int[sys_mac_addr][item]['Current'] = float(m.group(2))

                                    continue
                        if z == 4: # Tx Power
                            m = re.match("(Et\S+) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A)", line)
                            if m:
                                item = re.split('\d', m.group(1))[0]
                                number = re.split('\D+', m.group(1), 1)[1]
                                item = self.expand(item, int_dict)
                                if item is not None:
                                    item = item + number
                                    if "/" in m.group(2):
                                        info_transceiver[sys_mac_addr][item]['Tx Power'] = m.group(2)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['Tx Power'] = float(m.group(2))
                                    if "/" in m.group(3):
                                        info_transceiver[sys_mac_addr][item]['T-dBm-HA'] = m.group(3)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['T-dBm-HA'] = float(m.group(3))
                                    if "/" in m.group(4):
                                        info_transceiver[sys_mac_addr][item]['T-dBm-HW'] = m.group(4)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['T-dBm-HW'] = float(m.group(4))
                                    if "/" in m.group(5):
                                        info_transceiver[sys_mac_addr][item]['T-dBm-LA'] = m.group(5)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['T-dBm-LA'] = float(m.group(5))
                                    if "/" in m.group(6):
                                        info_transceiver[sys_mac_addr][item]['T-dBm-LW'] = m.group(6)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['T-dBm-LW'] = float(m.group(6))

                                    if item not in info_int[sys_mac_addr].keys():           # 기본적으로 모든 포트에 "/1-4" 가 나온다, 없다면 맨뒤 /1 등을 제외
                                        item = item[:-2]
                                        if item not in info_int[sys_mac_addr].keys():       # /1,/2,/3,/4 제외된 포트가 없다면 아래 생략, /1은 있을 것으로 생각됨
                                            continue

                                    if "/" in m.group(2):
                                        info_int[sys_mac_addr][item]['Tx Power'] = m.group(2)
                                    else:
                                        info_int[sys_mac_addr][item]['Tx Power'] = float(m.group(2))


                                    continue
                        if z == 5:      # Rx Power
                            m = re.match("(Et\S+) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A)", line)
                            if m:
                                item = re.split('\d', m.group(1))[0]
                                number = re.split('\D+', m.group(1), 1)[1]
                                item = self.expand(item, int_dict)
                                if item is not None:
                                    item = item + number
                                    if "/" in m.group(2):
                                        info_transceiver[sys_mac_addr][item]['Rx Power'] = m.group(2)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['Rx Power'] = float(m.group(2))
                                    if "/" in m.group(3):
                                        info_transceiver[sys_mac_addr][item]['R-dBm-HA'] = m.group(3)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['R-dBm-HA'] = float(m.group(3))
                                    if "/" in m.group(4):
                                        info_transceiver[sys_mac_addr][item]['R-dBm-HW'] = m.group(4)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['R-dBm-HW'] = float(m.group(4))
                                    if "/" in m.group(5):
                                        info_transceiver[sys_mac_addr][item]['R-dBm-LA'] = m.group(5)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['R-dBm-LA'] = float(m.group(5))
                                    if "/" in m.group(6):
                                        info_transceiver[sys_mac_addr][item]['R-dBm-LW'] = m.group(6)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['R-dBm-LW'] = float(m.group(6))

                                    if item not in info_int[sys_mac_addr].keys():           # 기본적으로 모든 포트에 "/1-4" 가 나온다, 없다면 맨뒤 /1 등을 제외
                                        item = item[:-2]
                                        if item not in info_int[sys_mac_addr].keys():       # /1,/2,/3,/4 제외된 포트가 없다면 아래 생략, /1은 있을 것으로 생각됨
                                            continue

                                    if "/" in m.group(2):
                                        info_int[sys_mac_addr][item]['Rx Power'] = m.group(2)
                                    else:
                                        info_int[sys_mac_addr][item]['Rx Power'] = float(m.group(2))
                                    continue

                    #####################################################################################################################
                    # old version - EOS-4.17.1.1F
                    if command == 'show interfaces transceiver' and sys_mac_addr != '':
                        m = re.search("-----     ---------  --------  --------  --------  --------  -------------------", line)
                        if m:
                            section = "transceiver"
                            continue
                        if section == "transceiver":
                            m = re.match("(Et\S+) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (\-?\w\w?\w?\.\w\w|N/A) \s+ (.+)", line)
                            if m:
                                item = re.split('\d', m.group(1))[0]
                                number = re.split('\D+', m.group(1), 1)[1]
                                item = self.expand(item, int_dict)
                                if item is not None:
                                    item = item + number
                                    if item not in info_transceiver[sys_mac_addr].keys():
                                        info_transceiver[sys_mac_addr][item] = collections.OrderedDict(zip(item_transceiver, [''] * len(item_transceiver)))
                                        info_transceiver[sys_mac_addr][item]['Zone'] = zone
                                        info_transceiver[sys_mac_addr][item]['Hostname'] = hostname
                                        info_transceiver[sys_mac_addr][item]['Sys MAC addr'] = sys_mac_addr
                                        info_transceiver[sys_mac_addr][item]['Model'] = switch_model
                                        info_transceiver[sys_mac_addr][item]['EOS version'] = eos_version
                                        info_transceiver[sys_mac_addr][item]['interface'] = item
                                        info_transceiver[sys_mac_addr][item]['type'] = re.split('\d', item)[0]
                                        info_transceiver[sys_mac_addr][item]['number'] = re.split('\D+', item, 1)[1]
                                    if "/" in m.group(2):
                                        info_transceiver[sys_mac_addr][item]['Temperature'] = m.group(2)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['Temperature'] = float(m.group(2))
                                    if "/" in m.group(3):
                                        info_transceiver[sys_mac_addr][item]['Voltage'] = m.group(3)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['Voltage'] = float(m.group(3))
                                    if "/" in m.group(4):
                                        info_transceiver[sys_mac_addr][item]['Current'] = m.group(4)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['Current'] = float(m.group(4))
                                    if "/" in m.group(5):
                                        info_transceiver[sys_mac_addr][item]['Tx Power'] = m.group(5)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['Tx Power'] = float(m.group(5))
                                    if "/" in m.group(6):
                                        info_transceiver[sys_mac_addr][item]['Rx Power'] = m.group(6)
                                    else:
                                        info_transceiver[sys_mac_addr][item]['Rx Power'] = float(m.group(6))

                                if item not in info_int[sys_mac_addr].keys():  # 기본적으로 모든 포트에 "/1-4" 가 나온다, 없다면 맨뒤 /1 등을 제외
                                    item = item[:-2]
                                    if item not in info_int[sys_mac_addr].keys():  # /1,/2,/3,/4 제외된 포트가 없다면 아래 생략, /1은 있을 것으로 생각됨
                                        continue

                                if "/" in m.group(2):
                                    info_int[sys_mac_addr][item]['Temperature'] = m.group(2)
                                else:
                                    info_int[sys_mac_addr][item]['Temperature'] = float(m.group(2))
                                if "/" in m.group(3):
                                    info_int[sys_mac_addr][item]['Voltage'] = m.group(3)
                                else:
                                    info_int[sys_mac_addr][item]['Voltage'] = float(m.group(3))
                                if "/" in m.group(4):
                                    info_int[sys_mac_addr][item]['Current'] = m.group(4)
                                else:
                                    info_int[sys_mac_addr][item]['Current'] = float(m.group(4))
                                if "/" in m.group(5):
                                    info_int[sys_mac_addr][item]['Tx Power'] = m.group(5)
                                else:
                                    info_int[sys_mac_addr][item]['Tx Power'] = float(m.group(5))
                                if "/" in m.group(6):
                                    info_int[sys_mac_addr][item]['Rx Power'] = m.group(6)
                                else:
                                    info_int[sys_mac_addr][item]['Rx Power'] = float(m.group(6))

                                continue

                    #####################################################################################################################
                    if command == 'show flowcontrol' and sys_mac_addr != '':
                        m = re.search("----------  -------- -------- -------- --------    ------------- -------------", line)
                        if m:
                            section = "flowcontrol"
                            continue
                        if section == "flowcontrol":
                            m = re.match("(\S+) \s+(desired|off|on|Unsupp\.) \s+(desired|off|on|Unsupp\.) \s+(desired|off|on) \s+(desired|off|on) \s+(\d+) \s+(\d+)", line)
                            if m:
                                item = re.split('\d', m.group(1))[0]
                                number = re.split('\D+', m.group(1), 1)[1]
                                item = self.expand(item, int_dict)
                                if item is not None:
                                    item = item + number
                                    if item not in info_int[sys_mac_addr].keys():
                                        info_int[sys_mac_addr][item] = collections.OrderedDict(zip(item_int, [''] * len(item_int)))
                                        info_int[sys_mac_addr][item]['Zone'] = zone
                                        info_int[sys_mac_addr][item]['Hostname'] = hostname
                                        info_int[sys_mac_addr][item]['Sys MAC addr'] = sys_mac_addr
                                        info_int[sys_mac_addr][item]['Model'] = switch_model
                                        info_int[sys_mac_addr][item]['EOS version'] = eos_version
                                        info_int[sys_mac_addr][item]['interface'] = item
                                        info_int[sys_mac_addr][item]['type'] = re.split('\d', item)[0]
                                        info_int[sys_mac_addr][item]['number'] = re.split('\D+', item, 1)[1]
                                    info_int[sys_mac_addr][item]['Send FlowControl admin'] = m.group(2)
                                    info_int[sys_mac_addr][item]['Send FlowControl oper'] = m.group(3)
                                    info_int[sys_mac_addr][item]['Receive FlowControl admin'] = m.group(4)
                                    info_int[sys_mac_addr][item]['Receive FlowControl oper'] = m.group(5)
                                    info_int[sys_mac_addr][item]['RxPause'] = int(m.group(6))
                                    info_int[sys_mac_addr][item]['TxPause'] = int(m.group(7))
                                    continue

                    #####################################################################################################################
                    if command == 'show management cvx' and sys_mac_addr != '':

                        m = re.search(" Status: (\w+)", line)
                        if m:
                            c_Status = m.group(1)
                            continue
                        m = re.search("Source interface: (.+)", line)
                        if m:
                            c_Source_interface = m.group(1)
                            continue
                        m = re.search("VRF: (.+)", line)
                        if m:
                            c_VRF = m.group(1)
                            continue
                        m = re.search("Heartbeat interval: (.+)", line)
                        if m:
                            c_interval = m.group(1)
                            continue
                        m = re.search("Heartbeat timeout: (.+)", line)
                        if m:
                            c_timeout = m.group(1)
                            continue
                        m = re.search("Controller cluster name: (.+)", line)
                        if m:
                            cluster_name = m.group(1)
                            continue
                        m = re.search("Controller status for (.+)", line)
                        if m:
                            cvx_ip = m.group(1)
                            if sys_mac_addr not in info_mgmt_cvx.keys():
                                info_mgmt_cvx[sys_mac_addr] = collections.OrderedDict()

                            if cvx_ip not in info_mgmt_cvx[sys_mac_addr].keys():
                                info_mgmt_cvx[sys_mac_addr][cvx_ip] = collections.OrderedDict(zip(item_mgmt_cvx, [''] * len(item_mgmt_cvx)))
                                info_mgmt_cvx[sys_mac_addr][cvx_ip]['Zone'] = zone
                                info_mgmt_cvx[sys_mac_addr][cvx_ip]['Hostname'] = hostname
                                info_mgmt_cvx[sys_mac_addr][cvx_ip]['Sys MAC addr'] = sys_mac_addr
                                info_mgmt_cvx[sys_mac_addr][cvx_ip]['Model'] = switch_model
                                info_mgmt_cvx[sys_mac_addr][cvx_ip]['EOS version'] = eos_version
                                info_mgmt_cvx[sys_mac_addr][cvx_ip]['domain-id'] = mlag_domain_id
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Status'] = c_Status
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Source interface'] = c_Source_interface
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['VRF'] = c_VRF
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Hb interval'] = c_interval
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Hb timeout'] = c_timeout
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Cluster name'] = cluster_name
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['CVX IP'] = cvx_ip
                            continue
                        m = re.search("Master since (.+)", line)
                        if m:
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Master'] = cvx_ip
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Master since'] = m.group(1)
                            continue
                        m = re.search("Connection status: (.+)", line)
                        if m:
                            z = z + 1
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Connection status'] = m.group(1)
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Connection count'] = z
                            continue
                        m = re.search("Connection timestamp: (.+)", line)
                        if m:
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Connection timestamp'] = m.group(1)
                            continue
                        m = re.search("Out-of-band connection: (.+)", line)
                        if m:
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Oob con'] = m.group(1)
                            continue
                        m = re.search("In-band connection: (.+)", line)
                        if m:
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['In-band con'] = m.group(1)
                            continue
                        m = re.search("Negotiated version: (.+)", line)
                        if m:
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Nego ver'] = m.group(1)
                            continue
                        m = re.search("Controller UUID: (.+)", line)
                        if m:
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Controller UUID'] = m.group(1)
                            continue
                        m = re.search("Last heartbeat sent: (.+)", line)
                        if m:
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Last hb sent'] = m.group(1)
                            continue
                        m = re.search("Last heartbeat received: (.+)", line)
                        if m:
                            info_mgmt_cvx[sys_mac_addr][cvx_ip]['Last hb received'] = m.group(1)
                            continue

                    #####################################################################################################################
                    if command == 'show cvx connections all' and sys_mac_addr != '':

                        m = re.search("^Switch (.+)", line)
                        if m:
                            item = m.group(1)
                            z = z + 1
                            if sys_mac_addr not in info_cvx_connection.keys():
                                info_cvx_connection[sys_mac_addr] = collections.OrderedDict()
                            if item not in info_cvx_connection[sys_mac_addr].keys():
                                info_cvx_connection[sys_mac_addr][item] = collections.OrderedDict(
                                    zip(item_cvx_connection, [''] * len(item_cvx_connection)))
                                info_cvx_connection[sys_mac_addr][item]["Zone"] = zone
                                info_cvx_connection[sys_mac_addr][item]['Hostname'] = hostname
                                info_cvx_connection[sys_mac_addr][item]["Sys MAC addr"] = sys_mac_addr
                                info_cvx_connection[sys_mac_addr][item]['Model'] = switch_model
                                info_cvx_connection[sys_mac_addr][item]["EOS version"] = eos_version
                                info_cvx_connection[sys_mac_addr][item]['Switch Mac'] = item
                                info_cvx_connection[sys_mac_addr][item]['Connection count'] = z
                            continue
                        m = re.search("\s+Hostname: (.+)", line)
                        if m:
                            info_cvx_connection[sys_mac_addr][item]['Switch Hostname'] = m.group(1)
                            continue
                        m = re.search("\s+State: (.+)", line)
                        if m:
                            info_cvx_connection[sys_mac_addr][item]['State'] = m.group(1)
                            continue
                        m = re.search("\s+Connection timestamp: (.+)", line)
                        if m:
                            info_cvx_connection[sys_mac_addr][item]['Connection timestamp'] = m.group(1)
                            continue
                        m = re.search("\s+Last heartbeat sent: (.+)", line)
                        if m:
                            info_cvx_connection[sys_mac_addr][item]['Last heartbeat sent'] = m.group(1)
                            continue
                        m = re.search("\s+Last heartbeat received: (.+)", line)
                        if m:
                            info_cvx_connection[sys_mac_addr][item]['Last heartbeat received'] = m.group(1)
                            continue
                        m = re.search("\s+Out-of-band connection: (.+)", line)
                        if m:
                            info_cvx_connection[sys_mac_addr][item]['Out-of-band connection'] = m.group(1)
                            continue
                        m = re.search("\s+In-band connection: (.+)", line)
                        if m:
                            info_cvx_connection[sys_mac_addr][item]['In-band connection'] = m.group(1)
                            continue


                    #####################################################################################################################
                    if command == 'show cvx' and sys_mac_addr != '':
                        m = re.search(" Status: (\w+)", line)
                        if m:
                            c_Status = m.group(1)
                            continue
                        m = re.search(" UUID: (.+)", line)
                        if m:
                            c_UUID = m.group(1)
                            continue
                        m = re.search(" Mode: (\w+)", line)
                        if m:
                            c_Mode = m.group(1)
                            continue
                        m = re.search("Heartbeat interval: (.+)", line)
                        if m:
                            c_interval = m.group(1)
                            continue
                        m = re.search("Heartbeat timeout: (.+)", line)
                        if m:
                            c_timeout = m.group(1)
                            continue
                        m = re.search("^    Name: (.+)", line)
                        if m:
                            cluster_name = m.group(1)
                            continue
                        m = re.search("^    Role: (.+)", line)
                        if m:
                            c_role = m.group(1)
                            continue
                        m = re.search("^    Peer timeout: (.+)", line)
                        if m:
                            c_Peer_timeout = m.group(1)
                            continue
                        m = re.search("^    Last leader switchover timestamp: (.+)", line)
                        if m:
                            c_Master_since = m.group(1)
                            continue
                        m = re.search("Peer Status for (.+)", line)
                        if m:
                            cvx_ip = m.group(1)

                            if sys_mac_addr not in info_cvx.keys():
                                info_cvx[sys_mac_addr] = collections.OrderedDict()

                            if cvx_ip not in info_cvx[sys_mac_addr].keys():
                                info_cvx[sys_mac_addr][cvx_ip] = collections.OrderedDict(zip(item_cvx, [''] * len(item_cvx)))
                                info_cvx[sys_mac_addr][cvx_ip]['Zone'] = zone
                                info_cvx[sys_mac_addr][cvx_ip]['Hostname'] = hostname
                                info_cvx[sys_mac_addr][cvx_ip]['Sys MAC addr'] = sys_mac_addr
                                info_cvx[sys_mac_addr][cvx_ip]['Model'] = switch_model
                                info_cvx[sys_mac_addr][cvx_ip]['EOS version'] = eos_version
                            info_cvx[sys_mac_addr][cvx_ip]["CVX C/S"] = "Server"
                            info_cvx[sys_mac_addr][cvx_ip]['CVX Status'] = c_Status
                            info_cvx[sys_mac_addr][cvx_ip]['UUID'] = c_UUID
                            info_cvx[sys_mac_addr][cvx_ip]['Mode'] = c_Mode
                            info_cvx[sys_mac_addr][cvx_ip]['Hb interval'] = c_interval
                            info_cvx[sys_mac_addr][cvx_ip]['Hb timeout'] = c_timeout
                            info_cvx[sys_mac_addr][cvx_ip]['Cluster name'] = cluster_name
                            info_cvx[sys_mac_addr][cvx_ip]['CVX Role'] = c_role
                            info_cvx[sys_mac_addr][cvx_ip]['Peer timeout'] = c_Peer_timeout
                            info_cvx[sys_mac_addr][cvx_ip]['Master since'] = c_Master_since
                            info_cvx[sys_mac_addr][cvx_ip]['Peer IP'] = cvx_ip

                            continue
                        m = re.search("Peer Id : (.+)", line)
                        if m:
                            info_cvx[sys_mac_addr][cvx_ip]['Peer Id'] = m.group(1)
                            continue
                        m = re.search("Peer registration state: (.+)", line)
                        if m:
                            z = z + 1
                            info_cvx[sys_mac_addr][cvx_ip]['Peer registration state'] = m.group(1)
                            info_cvx[sys_mac_addr][cvx_ip]['Connection count'] = z
                            continue
                        m = re.search("Peer service version compatibility : (.+)", line)
                        if m:
                            info_cvx[sys_mac_addr][cvx_ip]['version compatibility'] = m.group(1)
                            continue

                    #####################################################################################################################
                    if command == 'show cvx service' and sys_mac_addr != '':

                        m = re.search("^BugAlert", line)
                        if m:
                            section = "BugAlert"
                            continue
                        if section == "BugAlert":
                            m = re.search("^  Status: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["BugAlert"] = m.group(1)
                                continue
                        if section == "BugAlert":
                            m = re.search("^  Supported versions: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["BugAlert ver"] = m.group(1)
                                continue
                        m = re.search("^CliRelay", line)
                        if m:
                            section = "CliRelay"
                            continue
                        if section == "CliRelay":
                            m = re.search("^  Status: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["CliRelay"] = m.group(1)
                                continue
                        if section == "CliRelay":
                            m = re.search("^  Supported versions: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["CliRelay ver"] = m.group(1)
                                continue
                        m = re.search("^ControllerDebug", line)
                        if m:
                            section = "ControllerDebug"
                            continue
                        if section == "ControllerDebug":
                            m = re.search("^  Status: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["CtrDebug"] = m.group(1)
                                continue
                        m = re.search("^Crt", line)
                        if m:
                            section = "Crt"
                            continue
                        if section == "Crt":
                            m = re.search("^  Status: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["Crt"] = m.group(1)
                                continue
                        m = re.search("^Hsc", line)
                        if m:
                            section = "Hsc"
                            continue
                        if section == "Hsc":
                            m = re.search("^  Status: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["Hsc"] = m.group(1)
                                continue
                        if section == "Hsc":
                            m = re.search("^  Supported versions: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["Hsc ver"] = m.group(1)
                                continue
                        m = re.search("^Mss", line)
                        if m:
                            section = "Mss"
                            continue
                        if section == "Mss":
                            m = re.search("^  Status: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["Mss"] = m.group(1)
                                continue
                        m = re.search("^NetworkTopology", line)
                        if m:
                            section = "NetworkTopology"
                            continue
                        if section == "NetworkTopology":
                            m = re.search("^  Status: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["NetTopo"] = m.group(1)
                                continue
                        if section == "NetworkTopology":
                            m = re.search("^  Supported versions: (.+)", line)
                            if m:
                                info_system[sys_mac_addr]["NetTopo ver"] = m.group(1)
                                continue
                        m = re.search("^OpenStack", line)
                        if m:
                            section = "OpenStack"
                            continue
                        if section == "OpenStack":
                            m = re.search("^  Status: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["OpenStack"] = m.group(1)
                                continue
                        m = re.search("^Vxlan", line)
                        if m:
                            section = "Vxlan"
                            continue
                        if section == "Vxlan":
                            m = re.search("^  Status: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["Vxlan"] = m.group(1)
                                continue
                        if section == "Vxlan":
                            m = re.search("^  Supported versions: (\w+)", line)
                            if m:
                                info_system[sys_mac_addr]["Vxlan ver"] = m.group(1)
                                continue


                    ###########################################################################################################################
                    if command == 'show tacacs' and sys_mac_addr != '':
                        m = re.search("^TACACS\+ server            : ([\w|\.]+)\/49", line)
                        if m:
                            z = z + 1
                            item = m.group(1)
                            # print(m.group(1))    # tacacs 서버 IP 체크
                            if sys_mac_addr not in info_tacacs.keys():
                                info_tacacs[sys_mac_addr] = collections.OrderedDict()

                            if item not in info_tacacs[sys_mac_addr].keys():
                                info_tacacs[sys_mac_addr][item] = collections.OrderedDict(zip(item_tacacs, [''] * len(item_tacacs)))
                                info_tacacs[sys_mac_addr][item]["Zone"] = zone
                                info_tacacs[sys_mac_addr][item]['Hostname'] = hostname
                                info_tacacs[sys_mac_addr][item]['Model'] = switch_model
                                info_tacacs[sys_mac_addr][item]["EOS version"] = eos_version
                            info_tacacs[sys_mac_addr][item]['TACACS server'] = m.group(1)
                            info_tacacs[sys_mac_addr][item]['count'] = z
                            continue
                        m = re.search("Connection opens: \s+(\d+)", line)
                        if m:
                            info_tacacs[sys_mac_addr][item]['Connection opens'] = int(m.group(1))
                            continue
                        m = re.search("Connection closes: \s+(\d+)", line)
                        if m:
                            info_tacacs[sys_mac_addr][item]['Connection closes'] = int(m.group(1))
                            continue 
                        m = re.search("Connection disconnects: \s+(\d+)", line)
                        if m:
                            info_tacacs[sys_mac_addr][item]['Connection disconnects'] = int(m.group(1))
                            continue      
                        m = re.search("Connection failures: \s+(\d+)", line)
                        if m:
                            info_tacacs[sys_mac_addr][item]['Connection failures'] = int(m.group(1))
                            continue      
                        m = re.search("Connection timeouts: \s+(\d+)", line)
                        if m:
                            info_tacacs[sys_mac_addr][item]['Connection timeouts'] = int(m.group(1))
                            continue
                        m = re.search("Messages sent: \s+(\d+)", line)
                        if m:
                            info_tacacs[sys_mac_addr][item]['Messages sent'] = int(m.group(1))
                            continue 
                        m = re.search("Messages received: \s+(\d+)", line)
                        if m:
                            info_tacacs[sys_mac_addr][item]['Messages received'] = int(m.group(1))
                            continue      
                        m = re.search("Receive errors: \s+(\d+)", line)
                        if m:
                            info_tacacs[sys_mac_addr][item]['Receive errors'] = int(m.group(1))
                            continue    
                        m = re.search("Receive timeouts: \s+(\d+)", line)
                        if m:
                            info_tacacs[sys_mac_addr][item]['Receive timeouts'] = int(m.group(1))
                            continue      
                        m = re.search("Send timeouts: \s+(\d+)", line)
                        if m:
                            info_tacacs[sys_mac_addr][item]['Send timeouts'] = int(m.group(1))
                            continue    
                    ###########################################################################################################################
                    # if command == 'show bfd neighbor detail' and sys_mac_addr != '':
                    if command in ('show bfd neighbor detail', 'show bfd peers detail')and sys_mac_addr != '':
                        m = re.search("^Peer Addr ([\w|\.]+), Intf (\S*), Type (\S+), State (\w+)", line)
                        if m:
                            z = z + 1
                            item = m.group(1)
                            if sys_mac_addr not in info_bfd.keys():
                                info_bfd[sys_mac_addr] = collections.OrderedDict()

                            if item not in info_bfd[sys_mac_addr].keys():
                                info_bfd[sys_mac_addr][item] = collections.OrderedDict(zip(item_bfd, [''] * len(item_bfd)))
                                info_bfd[sys_mac_addr][item]["Zone"] = zone
                                info_bfd[sys_mac_addr][item]['Hostname'] = hostname
                                info_bfd[sys_mac_addr][item]['Model'] = switch_model
                                info_bfd[sys_mac_addr][item]["EOS version"] = eos_version
                            info_bfd[sys_mac_addr][item]['Peer Addr'] = m.group(1)
                            info_bfd[sys_mac_addr][item]['Intf'] = m.group(2)
                            info_bfd[sys_mac_addr][item]['Type'] = m.group(3)
                            info_bfd[sys_mac_addr][item]['State'] = m.group(4)
                            info_bfd[sys_mac_addr][item]['count'] = z
                            continue
                        m = re.search("^VRF (\S+), LAddr ([\w|\.]+), LD\/RD (.+\d)", line)
                        if m:
                            info_bfd[sys_mac_addr][item]['VRF name'] = m.group(1)
                            info_bfd[sys_mac_addr][item]['LAddr'] = m.group(2)
                            info_bfd[sys_mac_addr][item]['LD/RD'] = m.group(3)
                            continue
                        m = re.search("^Last Up (.+)", line)
                        if m:
                            info_bfd[sys_mac_addr][item]['Last Up'] = m.group(1)
                        m = re.search("^Last Down (.+)", line)
                        if m:
                            info_bfd[sys_mac_addr][item]['Last Down'] = m.group(1)
                        m = re.search("^TxInt: (\d+)\s*\w*, RxInt: (\d+)\s*\w*, Multiplier: (\d+)", line)
                        # m = re.search("^TxInt: (\d+)*, RxInt: (\d+), Multiplier: (\d+)", line)
                        if m:
                            info_bfd[sys_mac_addr][item]['TxInt'] = int(m.group(1))
                            info_bfd[sys_mac_addr][item]['RxInt'] = int(m.group(2))
                            info_bfd[sys_mac_addr][item]['Multiplier'] = int(m.group(3))
                            continue
                        # m = re.search("^Received RxInt: (\d+), Received Multiplier: (\d+)", line)
                        m = re.search("^Received RxInt: (\d+)\s*\w*, Received Multiplier: (\d+)", line)
                        if m:
                            info_bfd[sys_mac_addr][item]['Received RxInt'] = int(m.group(1))
                            info_bfd[sys_mac_addr][item]['Received Multiplier'] = int(m.group(2))
                            continue
                        m = re.search("^Rx Count: (.+)", line)
                        if m:
                            info_bfd[sys_mac_addr][item]['Rx Count'] = m.group(1)
                            continue
                        m = re.search("^Tx Count: (.+)", line)
                        if m:
                            info_bfd[sys_mac_addr][item]['Tx Count'] = m.group(1)
                            continue
                        # m = re.search("^Detect Time: (.+)", line)
                        m = re.search("^Detect Time: (\d+)\s*\w*", line)
                        if m:
                            info_bfd[sys_mac_addr][item]['Detect Time'] = int(m.group(1))
                            continue
                        m = re.search("^Registered protocols: (\S+)", line)
                        if m:
                            info_bfd[sys_mac_addr][item]['Registered protocols'] = m.group(1)
                            continue
                        m = re.search("^Uptime: (.+)", line)
                        if m:
                            info_bfd[sys_mac_addr][item]['Uptime'] = m.group(1)
                            continue

                    ###########################################################################################################################
                    if command == 'show ip bgp neighbor vrf all' and sys_mac_addr != '':
                        m = re.search("^BGP neighbor is ([\w|\.]+), remote AS (.+), (\w+) link", line)
                        if m:
                            item = m.group(1)
                            z = z + 1
                            if item not in info_bgp_stat[sys_mac_addr].keys():
                                info_bgp_stat[sys_mac_addr][item] = collections.OrderedDict(zip(item_bgp_stat, [''] * len(item_bgp_stat)))
                                info_bgp_stat[sys_mac_addr][item]["Zone"] = zone
                                info_bgp_stat[sys_mac_addr][item]['Hostname'] = hostname
                                info_bgp_stat[sys_mac_addr][item]['Model'] = switch_model
                                info_bgp_stat[sys_mac_addr][item]["EOS version"] = eos_version
                            info_bgp_stat[sys_mac_addr][item]['BGP neighbor'] = m.group(1)
                            info_bgp_stat[sys_mac_addr][item]['remote AS'] = float(m.group(2))
                            info_bgp_stat[sys_mac_addr][item]['link'] = m.group(3)
                            info_bgp_stat[sys_mac_addr][item]['count'] = z
                            continue
                        m = re.search("^  (BGP version \d+), remote router ID ([\w|\.]+), VRF (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['BGP version'] = m.group(1)
                            info_bgp_stat[sys_mac_addr][item]['remote router ID'] = m.group(2)
                            info_bgp_stat[sys_mac_addr][item]['VRF'] = m.group(3)
                            continue
                        m = re.search("^  Inherits configuration from and member of peer-group (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['peer-group'] = m.group(1)
                            continue
                        m = re.search("^  Last read (\S+), last write (\S+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Last read'] = m.group(1)
                            info_bgp_stat[sys_mac_addr][item]['last write'] = m.group(2)
                            continue
                        m = re.search("^  Hold time is (\d+), keepalive interval is (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Hold time'] = int(m.group(1))
                            info_bgp_stat[sys_mac_addr][item]['keepalive interval'] = int(m.group(2))
                            continue
                        m = re.search("^  Configured hold time is (\d+), keepalive interval is (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Cfg hold time'] = int(m.group(1))
                            info_bgp_stat[sys_mac_addr][item]['Cfg keepalive interval'] = int(m.group(2))
                            continue
                        m = re.search("^  Connect timer is (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Connect timer'] = m.group(1)
                            continue
                        m = re.search("^  Idle-restart timer is (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Idle-restart time'] = m.group(1)
                            continue
                        m = re.search("^  BGP state is (\S+), up for \s*(.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['BGP state'] = m.group(1)
                            info_bgp_stat[sys_mac_addr][item]['BGP up for'] = m.group(2)
                            continue
                        m = re.search("^  Number of transitions to established: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Number of transitions to established'] = int(m.group(1))
                            continue
                        m = re.search("^  Last state was (\S+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Last state'] = m.group(1)
                            continue
                        m = re.search("^  Last event was (\S+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Last event'] = m.group(1)
                            continue
                        m = re.search("^  Last sent notification:(.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Last sent notification'] = m.group(1)
                            continue
                        m = re.search("^  Last rcvd notification:(.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Last rcvd notification'] = m.group(1)
                            continue
                        # m = re.search("Multiprotocol IPv4 Unicast: (.+)", line)
                        m = re.search("Multiprotocol (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Multiprotocol'] = m.group(1)
                            continue
                        m = re.search("Four Octet ASN: (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Four Octet ASN'] = m.group(1)
                            continue
                        m = re.search("^    Route Refresh: (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Route Refresh'] = m.group(1)
                            continue
                        m = re.search("Send End-of-RIB messages: (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Send End-of-RIB messages'] = m.group(1)
                            continue
                        m = re.search("Additional-paths recv capability:", line)
                        if m:
                            section ="Additional-paths recv capability"
                            continue
                        if section == "Additional-paths recv capability":
                            # m = re.search("(IPv4 Unicast: .+)", line)
                            m = re.search("(IPv4 Unicast: .+|VPN EVPN: .+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Additional-paths recv capability'] = m.group(1)
                                continue
                        m = re.search("Additional-paths send capability:", line)
                        if m:
                            section ="Additional-paths send capability"
                            continue
                        if section == "Additional-paths send capability":
                            # m = re.search("(IPv4 Unicast: .+)", line)
                            m = re.search("(IPv4 Unicast: .+|VPN EVPN: .+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Additional-paths send capability'] = m.group(1)
                                continue
                        m = re.search("Graceful Restart received:", line)
                        if m:
                            section ="Graceful Restart received"
                            continue
                        if section == "Graceful Restart received":
                            m = re.search("(Restart-time is \d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['GR received Restart-time'] = m.group(1)
                                continue
                            m = re.search("(Restarting: \w+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['GR received Restarting'] = m.group(1)
                                continue
                            m = re.search("(IPv4 Unicast is \S+), Forwarding State is (.+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['GR received IPv4 Unicast'] = m.group(1)
                                info_bgp_stat[sys_mac_addr][item]['GR received Forwarding State'] = m.group(2)
                                continue
                        m = re.search("Restart timer is (.+)", line)
                        if m:
                            section = ""
                            info_bgp_stat[sys_mac_addr][item]['Restart timer'] = m.group(1)
                            continue
                        m = re.search("End of rib timer is (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['End of rib timer'] = m.group(1)
                            continue
                        m = re.search("Message \wtatistics:", line)
                        if m:
                            section ="Message Statistics"
                            continue
                        if section == "Message Statistics":
                            m = re.search("InQ depth is (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['InQ depth'] = int(m.group(1))
                                continue
                            m = re.search("OutQ depth is (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['OutQ depth'] = int(m.group(1))
                                continue
                            m = re.search("Opens: \s+ (\d+) \s+ (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Sent Opens'] = int(m.group(1))
                                info_bgp_stat[sys_mac_addr][item]['Rcvd Opens'] = int(m.group(2))
                                continue
                            m = re.search("Notifications: \s+ (\d+) \s+ (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Sent Notifications'] = int(m.group(1))
                                info_bgp_stat[sys_mac_addr][item]['Rcvd Notifications'] = int(m.group(2))
                                continue
                            m = re.search("Updates: \s* (\d+) \s* (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Sent Updates'] = int(m.group(1))
                                info_bgp_stat[sys_mac_addr][item]['Rcvd Updates'] = int(m.group(2))
                                continue
                            m = re.search("Keepalives: \s* (\d+) \s* (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Sent Keepalives'] = int(m.group(1))
                                info_bgp_stat[sys_mac_addr][item]['Rcvd Keepalives'] = int(m.group(2))
                                continue
                            m = re.search("Route-Refresh: \s* (\d+) \s* (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Sent Route-Refresh'] = int(m.group(1))
                                info_bgp_stat[sys_mac_addr][item]['Rcvd Route-Refresh'] = int(m.group(2))
                                continue
                            m = re.search("Total messages: \s* (\d+) \s* (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Sent Total messages'] = int(m.group(1))
                                info_bgp_stat[sys_mac_addr][item]['Rcvd Total messages'] = int(m.group(2))
                                continue
                        m = re.search("Prefix \wtatistics:", line)
                        if m:
                            section = "Prefix Statistics"
                            continue
                        if section == "Prefix Statistics":
                            m = re.search("IPv4 Unicast: \s* (\d+) \s* (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Sent pfx IPv4 Unicast'] = int(m.group(1))
                                info_bgp_stat[sys_mac_addr][item]['Rcvd pfx IPv4 Unicast'] = int(m.group(2))
                                continue
                            m = re.search("IPv6 Unicast: \s* (\d+) \s* (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Sent pfx IPv6 Unicast'] = int(m.group(1))
                                info_bgp_stat[sys_mac_addr][item]['Rcvd pfx IPv6 Unicast'] = int(m.group(2))
                                continue
                            m = re.search("IPv4 SR-TE: \s* (\d+) \s* (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Sent pfx IPv4 SR-TE'] = int(m.group(1))
                                info_bgp_stat[sys_mac_addr][item]['Rcvd pfx IPv4 SR-TE'] = int(m.group(2))
                                continue
                            m = re.search("IPv6 SR-TE: \s* (\d+) \s* (\d+)", line)
                            if m:
                                info_bgp_stat[sys_mac_addr][item]['Sent pfx IPv6 SR-TE'] = int(m.group(1))
                                info_bgp_stat[sys_mac_addr][item]['Rcvd pfx IPv6 SR-TE'] = int(m.group(2))
                                continue
                        m = re.search("Inbound updates dropped by reason:", line)
                        if m:
                            section = ""
                            continue
                        m = re.search("AS path loop detection: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['AS path loop detection'] = int(m.group(1))
                            continue
                        m = re.search("Enforced First AS: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Enforced First AS'] = int(m.group(1))
                            continue
                        m = re.search("Originator ID matches local router ID: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Originator ID matches local router ID'] = int(m.group(1))
                            continue
                        m = re.search("Nexthop matches local IP address: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Nexthop matches local IP address'] = int(m.group(1))
                            continue
                        m = re.search("Unexpected IPv6 nexthop for IPv4 routes: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Unexpected IPv6 nexthop for IPv4 routes'] = int(m.group(1))
                            continue
                        m = re.search("Nexthop invalid for single hop eBGP: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Nexthop invalid for single hop eBGP'] = int(m.group(1))
                            continue
                        m = re.search("Resulting in removal of all paths in update \(treat-as-withdraw\): (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Resulting in removal of all paths in update (treat-as-withdraw)'] = int(m.group(1))
                            continue
                        m = re.search("Resulting in AFI/SAFI disable: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Resulting in AFI/SAFI disable'] = int(m.group(1))
                            continue
                        m = re.search("Resulting in attribute ignore: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Resulting in attribute ignore'] = int(m.group(1))
                            continue
                        m = re.search("IPv4 labeled-unicast NLRIs dropped due to excessive labels: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['IPv4 labeled-unicast NLRIs dropped due to excessive labels'] = int(m.group(1))
                            continue
                        m = re.search("IPv6 labeled-unicast NLRIs dropped due to excessive labels: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['IPv6 labeled-unicast NLRIs dropped due to excessive labels'] = int(m.group(1))
                            continue
                        m = re.search("IPv4 local address not available: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['IPv4 local address not available'] = int(m.group(1))
                            continue
                        m = re.search("IPv6 local address not available: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['IPv6 local address not available'] = int(m.group(1))
                            continue
                        m = re.search("Inbound route map is (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Inbound route map'] = m.group(1)
                            continue
                        m = re.search("Outbound route map is (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Outbound route map'] = m.group(1)
                            continue
                        m = re.search("Local AS is (.+), local router ID ([\w|\.]+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Local AS'] = float(m.group(1))
                            info_bgp_stat[sys_mac_addr][item]['local router ID'] = m.group(2)
                            continue
                        m = re.search("TTL is (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['TTL'] = int(m.group(1))
                            continue
                        m = re.search("Local TCP address is ([\w|\.]+), local port is (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Local TCP address'] = m.group(1)
                            info_bgp_stat[sys_mac_addr][item]['Local TCP port'] = int(m.group(2))
                            continue
                        m = re.search("Remote TCP address is ([\w|\.]+), remote port is (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Remote TCP address'] = m.group(1)
                            info_bgp_stat[sys_mac_addr][item]['Remote TCP port'] = int(m.group(2))
                            continue
                        m = re.search("Auto-Local-Addr is (\S+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Auto-Local-Addr'] = m.group(1)
                            continue
                        m = re.search("TCP state is (\S+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['TCP state'] = m.group(1)
                            continue
                        m = re.search("Recv-Q: (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Recv-Q'] = m.group(1)
                            continue
                        m = re.search("Send-Q: (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Send-Q'] = m.group(1)
                            continue
                        m = re.search("Outgoing Maximum Segment Size \(MSS\): (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Outgoing MSS'] = int(m.group(1))
                            continue
                        m = re.search("Total Number of TCP retransmissions: (\d+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['TCP retransmissions'] = int(m.group(1))
                            continue
                        m = re.search("Timestamps enabled: (\w+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Timestamps enabled'] = m.group(1)
                            continue
                        m = re.search("Selective Acknowledgments enabled: (\w+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Selective Acknowledgments enabled'] = m.group(1)
                            continue
                        m = re.search("Window Scale enabled: (\w+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Window Scale enabled'] = m.group(1)
                            continue
                        m = re.search("Explicit Congestion Notification \(ECN\) enabled: (\w+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Explicit Congestion Notification (ECN) enabled'] = m.group(1)
                            continue
                        m = re.search("Window Scale \(wscale\): (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Window Scale (wscale)'] = m.group(1)
                            continue
                        m = re.search("Retransmission Timeout \(rto\): (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Retransmission Timeout (rto)'] = m.group(1)
                            continue
                        m = re.search("Round-trip Time \(rtt/rtvar\): (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Round-trip Time (rtt/rtvar)'] = m.group(1)
                            continue
                        m = re.search("Delayed Ack Timeout \(ato\): (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Delayed Ack Timeout (ato)'] = m.group(1)
                            continue
                        m = re.search("Congestion Window \(cwnd\): (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Congestion Window (cwnd)'] = m.group(1)
                            continue
                        m = re.search("TCP Throughput: (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['TCP Throughput'] = m.group(1)
                            continue
                        m = re.search("Recv Round-trip Time \(rcv_rtt\): (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Recv Round-trip Time (rcv_rtt)'] = m.group(1)
                            continue
                        m = re.search("Advertised Recv Window \(rcv_space\): (.+)", line)
                        if m:
                            info_bgp_stat[sys_mac_addr][item]['Advertised Recv Window (rcv_space)'] = m.group(1)
                            continue



                    #####################################################################################################################
                    if command == 'show vrrp vrf all all' and sys_mac_addr != '':

                        m = re.search("(\S+) - Group (\d+)", line)
                        if m:
                            item = m.group(1)
                            if sys_mac_addr not in info_fhrp.keys():
                                info_fhrp[sys_mac_addr] = collections.OrderedDict()

                            if item not in info_fhrp[sys_mac_addr].keys():
                                info_fhrp[sys_mac_addr][item] = collections.OrderedDict(zip(item_fhrp, [''] * len(item_fhrp)))
                                info_fhrp[sys_mac_addr][item]['Zone'] = zone
                                info_fhrp[sys_mac_addr][item]['Hostname'] = hostname
                                info_fhrp[sys_mac_addr][item]['Model'] = switch_model
                                info_fhrp[sys_mac_addr][item]['EOS version'] = eos_version
                            info_fhrp[sys_mac_addr][item]['Interface'] = item
                            info_fhrp[sys_mac_addr][item]['Group ID'] = int(m.group(2))
                            info_fhrp[sys_mac_addr][item]['fhrp mode'] = "VRRP"
                            continue
                        m = re.search("VRF is (.+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['VRF'] = m.group(1)
                            continue
                        m = re.search("VRRP Version (\d+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['VRRP Version'] = int(m.group(1))
                            continue
                        m = re.search("State is (\S+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['State'] = m.group(1)
                            continue
                        m = re.search("Virtual IPv4 address is (\d+\.\d+\.\d+\.\d+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Virtual IPv4 address'] = m.group(1)
                            continue
                        m = re.search("Virtual MAC address is ([\w|\.]+\w)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Virtual MAC address'] = m.group(1)
                            continue
                        m = re.search("Mac Address Advertisement interval is (\S+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Mac Address Advertisement interval'] = m.group(1)
                            continue
                        m = re.search("VRRP Advertisement interval is (\S+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['VRRP Advertisement interval'] = m.group(1)
                            continue
                        m = re.search("Preemption is (\S+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Preemption'] = m.group(1)
                            continue
                        m = re.search("Preemption delay is (\S+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Preemption delay'] = m.group(1)
                            continue
                        m = re.search("Preemption reload delay is (\S+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Preemption reload delay'] = m.group(1)
                            continue
                        m = re.search("Priority is (\S+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Priority'] = int(m.group(1))
                            continue
                        m = re.search("Authentication (.+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Authentication'] = m.group(1)
                            continue
                        m = re.search("Master Router is (\d+\.\d+\.\d+\.\d+), priority is (\d+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Master Router'] = m.group(1)
                            info_fhrp[sys_mac_addr][item]['Master Priority'] = int(m.group(2))
                            continue
                        m = re.search("Master Router is (\d+\.\d+\.\d+\.\d+) \((local)\), priority is (\d+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Master Router'] = m.group(1)
                            info_fhrp[sys_mac_addr][item]['Master Priority'] = int(m.group(3))
                            info_fhrp[sys_mac_addr][item]['Master local'] = m.group(2)
                            continue
                        m = re.search("Master Advertisement interval is (\S+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Master Advertisement interval'] = m.group(1)
                            continue
                        m = re.search("Skew time is (.+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Skew time'] = m.group(1)
                            continue
                        m = re.search("Master Down interval is (.+)", line)
                        if m:
                            info_fhrp[sys_mac_addr][item]['Master Down interval'] = m.group(1)
                            continue



                    #####################################################################################################################
                    if command == 'show ip virtual-router vrf all' and sys_mac_addr != '':
                        m = re.search("IP virtual router is configured with MAC address: ([\w|\.]+\w)", line)
                        if m:
                            vmac = m.group(1)
                            continue
                        m = re.search("IP router is (.+) with Mlag peer MAC address", line)
                        if m:
                            mlag_peer_mac = m.group(1)
                            continue
                        m = re.search("MAC address advertisement interval: (\d+)", line)
                        if m:
                            mac_ad_interval = m.group(1)
                            continue
                        m = re.search("(\S+\d) \s+ (\S+) \s+ (\d+\.\d+\.\d+\.\d+) \s+ (U|D|T|UN|NP|LLD) \s+ (\w+)", line)
                        if m:
                            item = re.split('\d', m.group(1))[0]
                            number = re.split('\D+', m.group(1), 1)[1]
                            item = self.expand(item, int_dict)
                            if item is not None:
                                item = item + number

                                if sys_mac_addr not in info_fhrp.keys():
                                    info_fhrp[sys_mac_addr] = collections.OrderedDict()

                                if item not in info_fhrp[sys_mac_addr].keys():
                                    info_fhrp[sys_mac_addr][item] = collections.OrderedDict(zip(item_fhrp, [''] * len(item_fhrp)))
                                    info_fhrp[sys_mac_addr][item]['Zone'] = zone
                                    info_fhrp[sys_mac_addr][item]['Hostname'] = hostname
                                    info_fhrp[sys_mac_addr][item]['Model'] = switch_model
                                    info_fhrp[sys_mac_addr][item]['EOS version'] = eos_version
                                info_fhrp[sys_mac_addr][item]['Interface'] = item
                                info_fhrp[sys_mac_addr][item]['VRF'] = m.group(2)
                                info_fhrp[sys_mac_addr][item]['Virtual IPv4 address'] = m.group(3)
                                info_fhrp[sys_mac_addr][item]['Protocol'] = m.group(4)
                                info_fhrp[sys_mac_addr][item]['State'] = m.group(5)
                                info_fhrp[sys_mac_addr][item]['fhrp mode'] = "vARP"

                                info_fhrp[sys_mac_addr][item]['Virtual MAC address'] = vmac
                                info_fhrp[sys_mac_addr][item]['Mlag peer MAC address'] = mlag_peer_mac
                                info_fhrp[sys_mac_addr][item]['Mac Address Advertisement interval'] = mac_ad_interval
                                # print(f.name)
                                continue
                # pbar.close()
                # print(f.closed)
                f.close()
            
        except:
            print("\n")
            print("#" * strlen)
            print("Error during analysis")
            print("Please Check whether the tech-support file is normal or not.")
            print("\n")
            print(f" hostname : {hostname}, show command : {command }, system mac address : {sys_mac_addr}")
            print(f"{line}")
            # print(f.closed)
            # f.close()
            # os.system('pause')
        finally:
            print("\n")
            print("#" * strlen)
            print("Analysis is complete. Start saving as an Excel file.".center(strlen))
            print(f'Excel file name : min-arista-v{analyzer_version}{subfoldername}_{now}.xlsx'.center(strlen))
            print("#" * strlen)
            print("\n\n")
            print("Analysis Summary".center(strlen))
            print("-" * strlen)
            # os.system('pause')

        #####################################################################################################################

        col_hide_item = ["Sys MAC addr", "type", "number"]

        #####################################################################################################################
        # 엑셀 저장 프로세스

        def write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes):
            c = len(info_dict)
            row = 0
            if c > 0:
                ws = wb.add_worksheet(ws_name)
                for key in info_dict:
                    if 'Sys MAC addr' in info_dict[key].keys():                                         # 시스템 기준 정보 수집
                        for col, key2 in enumerate(item_list):                                          # col 만 사용
                            ws.write(row + 1, col, info_dict[key][item_list[col]], style_data)
                        row = row + 1
                    else:
                        for item in info_dict[key]:                                                     # 시스템 하단 키가 추가된 정보 수집
                            for col, key2 in enumerate(item_list):
                                ws.write(row + 1, col, info_dict[key][item][item_list[col]], style_data)
                            row = row + 1
                if row != 0:
                    a = list(map(lambda x: {"header": x, 'header_format': style_header}, item_list))  # xlsxwriter 사용시 시트의 테이블 헤더 값을 정리
                    options = {'columns': a}
                    ws.add_table(0, 0, row, col, options)
                    ws.freeze_panes(1, freeze_panes)  # 틀 고정

                    for col, key in enumerate(item_list):
                        if key in col_hide_item:
                            ws.set_column(col, col, None, None, {'hidden': True})
                print(f'{str(row).ljust(11)} :  {ws_name}')
            else:
                print(f'{str(row).ljust(11)} :  {ws_name}')
                return None

        #### 장비가 열로 가게 수정되는 부분

        # def write_ws2(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes):
        #     c = len(info_dict)
        #     col = 0
        #     if c > 0:
        #         ws = wb.add_worksheet(ws_name)
        #         for key in info_dict:
        #             for row, key2 in enumerate(item_list):
        #                 ws.write(row , col + 1 , info_dict[key][item_list[row]], style_data)
        #             col = col + 1

        #         if col != 0:
        #             ws.add_table(0, 0, row, col)
        #             ws.freeze_panes(4, freeze_panes)  # 틀 고정

        #         print(col, "  :  " + ws_name)

        #     else:
        #         print(col, "  :  " + ws_name)
        #         return None

        # 장비가 1개 이상이면 저장 시작
        try:
            if len(info_system) > 0:
                #### 엑셀 워크 북 생성 및 스타일 포맷 설정
                directory = f"./pm/report/{yymmdd}"
                if not os.path.exists(directory):
                    os.makedirs(directory)
   
                savefilename = f'{directory}/arista_analysis_{yymmdd}.xlsx'

                with xlsxwriter.Workbook(savefilename) as wb:
                    style_header = wb.add_format({'bold': True, 'font_size': 10 ,'align': 'center'})
                    style_data = wb.add_format({'font_size': 10 })
                    style_data2 = wb.add_format({'font_size': 10 ,'text_wrap': True })

                    #### 1. System info 저장
                    ws_name = 'System'
                    freeze_panes = 4
                    info_dict = info_system
                    item_list = item_system
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    #### 2. mlag info 저장
                    ws_name = 'mlag'
                    info_dict = info_mlag
                    item_list = item_mlag
                    freeze_panes = 6
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    #### 5. LLDP info 저장
                    ws_name = 'lldp'
                    info_dict = info_lldp
                    item_list = item_lldp
                    freeze_panes = 7
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    #### 6. int info 저장
                    ws_name = 'interfaces'
                    info_dict = info_int
                    item_list = item_int
                    freeze_panes = 5
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    #### 7. bgp session 저장
                    ws_name = 'bgp'
                    info_dict = info_bgp_stat
                    item_list = item_bgp_stat
                    freeze_panes = 5
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    # #### int config 저장
                    # ws_name = 'cfg_int'
                    # info_dict = cfg_int
                    # item_list = item_int_cfg
                    # freeze_panes = 5
                    # write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    # ####  basic config 저장
                    # ws_name = 'cfg_basic'
                    # info_dict = cfg_basic
                    # item_list = item_basic
                    # freeze_panes = 4
                    # write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    # ####  runconfig 저장
                    # ws_name = 'runconfig'
                    # info_dict = cfg_runconfig
                    # item_list = item_runconfig
                    # freeze_panes = 6
                    # write_ws(info_dict, item_list, wb, ws_name, style_header, style_data2, freeze_panes)

                    # ########
                    # ws_name = 'longconfig'
                    # info_dict = cfg_longconfig
                    # item_list = item_long_config
                    # freeze_panes = 1
                    # write_ws2(info_dict, item_list, wb, ws_name, style_header, style_data2, freeze_panes)

                    ########
                    ws_name = 'fhrp'
                    info_dict = info_fhrp
                    item_list = item_fhrp
                    freeze_panes = 6
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    #### 11. bfd session 저장
                    ws_name = 'bfd'
                    info_dict = info_bfd
                    item_list = item_bfd
                    freeze_panes = 7
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    #### 11. bfd session 저장
                    ws_name = 'tacacs'
                    info_dict = info_tacacs
                    item_list = item_tacacs
                    freeze_panes = 6
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    #### 3. transceiver 저장
                    ws_name = 'transceiver'
                    info_dict = info_transceiver
                    item_list = item_transceiver
                    freeze_panes = 10
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    #### 4. transceiver serial 저장
                    ws_name = 'transceiver_serial'
                    info_dict = info_transceiver_serial
                    item_list = item_transceiver_serial
                    freeze_panes = 5
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    ########
                    ws_name = 'cvx_con'
                    info_dict = info_cvx_connection
                    item_list = item_cvx_connection
                    freeze_panes = 6
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    #### 3. management cvx 저장
                    ws_name = 'mgmt_cvx'
                    info_dict = info_mgmt_cvx
                    item_list = item_mgmt_cvx
                    freeze_panes = 5
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

                    #### 4. cvx 저장
                    ws_name = 'cvx'
                    info_dict = info_cvx
                    item_list = item_cvx
                    freeze_panes = 4
                    write_ws(info_dict, item_list, wb, ws_name, style_header, style_data, freeze_panes)

            else:
                print("\n")
                print("#" * strlen)
                print("No switches analyzed")

        except IOError as e:
            print("\n")
            print("#" * strlen)
            print("Could not write " + savefilename + " \nError: ", e)

        finally:
            print("\n")
            print("#" * strlen)
            print(f"Total times :  {round((time.time() - start_time),4)} seconds")
            print("#" * strlen)
            print(f"dup_devices :  {str(len(dupdevices))}")
            print("#" * strlen)
            pprint.pprint(dupdevices)
            print("#" * strlen)
            # os.system('pause')
            # sys.exit()
            
        return True, ""