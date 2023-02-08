from multiprocessing.sharedctypes import Value
import re, ipaddress
import yaml, json, sys, platform
from generators.BlankNone import *
from openpyxl import load_workbook
from operator import eq
import pandas as pd
from jinja2 import Template

def resource_path(relative_path):
	try:
		# PyInstaller에 의해 임시폴더에서 실행될 경우 임시폴더로 접근하는 함수
		base_path = sys._MEIPASS
	except Exception:
		base_path = os.path.abspath(".")
	return os.path.join(base_path, relative_path)

def defaultDirRoot():
	if eq(platform.system().lower(), "windows"):
		path = "./"
	else:
		path = os.path.sep.join(sys.argv[0].split(os.path.sep)[:-1]) + "/"

	return path


def generateInventory(inventory_file, excelVar):
	"""
	엑셀에서 데이터를 읽어 inventory 정보 처리
	d1.yml, all.yml 파일 생성
  toplogy 이미지 생성
	"""
	info = pd.read_excel(inventory_file, sheet_name="Var").fillna("")

	mgmtVrf = info.loc[[6], ["Variables Value"]].values[0][0]
	mgmtInterface = "Management1"
	mgmtGw = info.loc[[7],["Variables Value"]].values[0][0]
	macAging = info.loc[[16],["Variables Value"]].values[0][0]
	arpAging = info.loc[[17],["Variables Value"]].values[0][0]
	clockTimeZone = info.loc[[9],["Variables Value"]].values[0][0]
	adminName = info.loc[[11],["Variables Value"]].values[0][0]
	adminPassword = info.loc[[12],["Variables Value"]].values[0][0]
	admin_privilege = info.loc[[13],["Variables Value"]].values[0][0]
	spanningTreeMode = info.loc[[5],["Variables Value"]].values[0][0]
	terminalLength = info.loc[[1],["Variables Value"]].values[0][0]
	terminalWidth = info.loc[[2],["Variables Value"]].values[0][0]
	logginBuffered = info.loc[[3],["Variables Value"]].values[0][0]
	p2pSubnet = info.loc[[14],["Prefix & Define Value"]].values[0][0]
	spineBGPAsn = info.loc[[3],["Prefix & Define Value"]].values[0][0]
	spinePrefix = info.loc[[9],["Prefix & Define Value"]].values[0][0]
	leafPrefix = info.loc[[10],["Prefix & Define Value"]].values[0][0]

	##### port map 정보 로드 S #####
	sheetName = excelVar["pd"]["portMap"]["sheetName"]
	headerRow = excelVar["pd"]["portMap"]["header"]
	spineCol = excelVar["pd"]["portMap"]["spine"]
	spinePortCol = excelVar["pd"]["portMap"]["spinePort"]
	spineIpCol = excelVar["pd"]["portMap"]["spineIp"]
	leafCol = excelVar["pd"]["portMap"]["leaf"]
	leafPortCol = excelVar["pd"]["portMap"]["leafPort"]
	leafIpCol = excelVar["pd"]["portMap"]["leafIp"]

	switches = pd.read_excel(inventory_file, header=headerRow, sheet_name=sheetName)[[spineCol, spinePortCol, spineIpCol, leafCol, leafPortCol, leafIpCol]].dropna(axis=0)

	portMap = {}
	topologyInterfaces = {} ##### eve-ng, pnetlab 포톨로지파일 생성용 데이터

	for idx, switch in switches.iterrows():
		id = idx + 1
		###### 포트값에서 숫자 추출, 
		sPortID = re.sub(r'[^0-9]', '', switch[spinePortCol])
		ePortID = re.sub(r'[^0-9]', '', switch[leafPortCol])
		topologyInterfaces.setdefault(id, 
			{
				"START": switch[spineCol],
				"SPORT": switch[spinePortCol],
				"S_IP": switch[spineIpCol], 
				"S_ID": int(sPortID),
				"END": switch[leafCol],
				"EPORT": switch[leafPortCol],
				"E_IP": switch[leafIpCol],
				"E_ID": int(ePortID)
			}
		)
  
		##### P2P S #####  
		## spine switch 정리
		p = re.compile(spinePrefix)
		if (p.match(str(switch[spineCol]))):
			spine = switch[spineCol]
			if not spine in portMap:
				portMap.setdefault(
					spine,  {
						"INTERFACES": [{ "ETHERNET": switch[spinePortCol], "IP": switch[spineIpCol] }],
						"ETC_PORTS": { "IP": "", "INTERFACES": [] }
					}
				)
			else:
				portMap[spine]["INTERFACES"].append({ "ETHERNET": switch[spinePortCol], "IP": switch[spineIpCol] })
				
		## leaf switch 정리
		p = re.compile(leafPrefix)
		leaf = switch[spineCol]
		if (p.match(str(switch[leafCol])) and not p.match(leaf)):
			leaf = switch[leafCol]
			if not leaf in portMap:
				portMap.setdefault(
					leaf,  {
						"INTERFACES": [{ "ETHERNET": switch[leafPortCol], "IP": switch[leafIpCol] }],
						"ETC_PORTS": { "IP": "", "INTERFACES": [] }
					}
				)
			else:
				portMap[leaf]["INTERFACES"].append({ "ETHERNET": switch[leafPortCol], "IP": switch[leafIpCol] })
    ##### P2P E ##### 
    
    ##### port channell S #####
		p = re.compile(leafPrefix)
		# print(switch[spineCol], switch[leafCol])
		if (p.match(str(switch[leafCol])) and p.match(str(switch[spineCol]))):

			leaf = switch[leafCol]
			portMap[leaf]["ETC_PORTS"]["IP"] = switch[leafIpCol]
			portMap[leaf]["ETC_PORTS"]["INTERFACES"].append({ "ETHERNET": switch[leafPortCol] })

			leaf = switch[spineCol]
			portMap[leaf]["ETC_PORTS"]["IP"] = switch[spineIpCol]
			portMap[leaf]["ETC_PORTS"]["INTERFACES"].append({ "ETHERNET": switch[spinePortCol] })
   
		##### port channell E #####	
    
	# print(topologyInterfaces)
	##### eve-ng, pnetlab 포톨로지파일 생성용 데이터 생성 S ######
	with BlankNone(), open(defaultDirRoot() + "inventory/topologyInterfaces.yml", "w") as inv:
		inv.write(yaml.dump(topologyInterfaces, sort_keys=False))
	inv.close()
  ##### eve-ng, pnetlab 포톨로지파일 생성용 데이터 생성 E ######
  
	##### port map 정보 로드 E #####

	## 기본변수 로드
	with open(resource_path("./excelEnvriment.json"), "r", encoding='utf8') as f:
		excelVar = json.load(f)
	f.close()
  
	sheetName = excelVar["pd"]["switchIpInfo"]["sheetName"]
	headerRow = excelVar["pd"]["switchIpInfo"]["header"]
	hostNameCol = excelVar["pd"]["switchIpInfo"]["hostName"]
	mgmtCol = excelVar["pd"]["switchIpInfo"]["mgmt"]
	loopback0Col = excelVar["pd"]["switchIpInfo"]["loopback0"]
	bgpAsnCol = excelVar["pd"]["switchIpInfo"]["bgpAsn"]
	typeCol = excelVar["pd"]["switchIpInfo"]["type"]
	idCol = excelVar["pd"]["switchIpInfo"]["id"]
	loop1Col = excelVar["pd"]["switchIpInfo"]["loopback1"]
	
 
	## Switch 정보 로드
	switches = pd.read_excel(inventory_file, header=headerRow, sheet_name=sheetName)[[hostNameCol, mgmtCol, loopback0Col, bgpAsnCol, typeCol, idCol, loop1Col]].fillna("")
	
	config = {"hosts": None}

	data = {}
	## spine, leaf, bl 개수 체크
	topologySwitches = { "spine": 0, "leaf": 0, "bl": 0 }

	for idx, switch in switches.iterrows():
		hostname = switch[hostNameCol]
		mgmt = switch[mgmtCol]
		loop0 = switch[loopback0Col]
		spinePrefix = excelVar["spine"]["prefix"]

		##### spine ip 체크 , leaf 일때 bgp underlay ip ??
		spines = []
		# print(topologyInterfaces)
		if switch[typeCol] != "Spine":
			for id in topologyInterfaces:
				p = re.compile(spinePrefix)
				if hostname == topologyInterfaces[id]["END"] and (p.match(str(topologyInterfaces[id]["START"]))):
					hn = topologyInterfaces[id]["START"]
					ip = topologyInterfaces[id]["S_IP"] if "/" not in topologyInterfaces[id]["S_IP"] else topologyInterfaces[id]["S_IP"].split("/")[0]
					spines.append({ "HOSTNAME": hn, "IP": ip })
		
		data.setdefault(
			hostname,  {
					"hostname": mgmt,
					"port": 22,
					"username": "admin",
					"password": "admin",
					"platform": "eos",
					"data": {
						"HOSTNAME": hostname,
						"HOST_IP": mgmt,
						"LOOPBACK0": loop0,
						"LOOPBACK1": str(switch[loop1Col]) + "/32" if switch[loop1Col] != "" else "",
						"PERMIT_IP": str(ipaddress.IPv4Interface(str(switch[loop1Col]) + "/24").network) if switch[loop1Col] != "" else "",					
						"INTERFACES": portMap[hostname]["INTERFACES"] if hostname in portMap else "",
						"ETC_PORTS": portMap[hostname]["ETC_PORTS"] if hostname in portMap else "",
						"BGP_ASN": int(switch[bgpAsnCol]) if switch[typeCol] == "Spine" else switch[bgpAsnCol],
						"SPINE_BGP_ASN": spineBGPAsn,
						"SPINES": spines,
						"ID": switch[idCol],
						"TYPE": switch[typeCol],
						"P2P_SUBNET": p2pSubnet
					}
			}
		)
  
		## spine, leaf, bl 갯수 체크
		v = topologySwitches[str(switch[typeCol]).lower()]
		topologySwitches[str(switch[typeCol]).lower()] = v + 1

	config = data

	with BlankNone(), open(defaultDirRoot() + "inventory/hosts.yml", "w") as inv:
		inv.write(yaml.dump(config, sort_keys=False))
	inv.close()
  
  # Group Vars all.yml 파일 생성
	data = {
		"TERMINAL_LENGTH": terminalLength,
		"TERMINAL_WIDTH": terminalWidth,
		"LOGGIN_BUFFERED": logginBuffered,
		"SPANNING_TREE_MODE": spanningTreeMode,
		"ADMIN_USER_NAME": adminName,
		"ADMIN_USER_PW": adminPassword,
		"CLOCK_TIMEZONE": clockTimeZone,
		"ARP_AGING": arpAging,
		"MAC_AGING": macAging,
		"ADMIN_PRIVILEGE": admin_privilege,
		"MGMT_VRF": mgmtVrf,
		"MGMT_INTERFACE": mgmtInterface,
		"MGMT_GW": mgmtGw,
		"BACKUP_FILENAME": "{{ inventory_hostname }}_{{ lookup('pipe', 'date +%Y%m%d%H%M%S') }}"
	}

	with open(defaultDirRoot() + 'inventory/templates/inventory/defaults.j2') as f:
		template = Template(f.read())
	f.close()
 
	with open(defaultDirRoot() + "inventory/defaults.yml", "w") as reqs:
		reqs.write(template.render(**data))
	reqs.close()
