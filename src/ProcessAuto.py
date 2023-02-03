import yaml, json, base64, asyncio, os, sys
from nornir import InitNornir
from nornir.plugins import *
from nornir.plugins.inventory import *
from nornir.plugins.runners import *
from nornir.plugins.functions import *
from nornir.plugins.processors import *
from nornir.plugins.tasks import *
from nornir.plugins.connections import *
from nornir_netmiko.tasks import netmiko_send_config, netmiko_send_command
from nornir.core.task import Task, Result
from jinja2 import Template
from datetime import datetime
from openpyxl import load_workbook
from generators.BlankNone import *
from generators.generateInventory import generateInventory 
from operator import eq
import zipfile, collections, shutil, platform
from nornir.core.plugins.connections import ConnectionPluginRegister
from nornir_netmiko.connections import Netmiko


###### pyinstaller 에서 netmiko 플러그인없이 빌드되는 경우가 있는듯
ConnectionPluginRegister.register("netmiko", Netmiko)

class ProcessAuto():
	def __init__(self):
  
		if eq(platform.system().lower(), "windows"):
			self.path = "./"
		else:
			self.path = os.path.sep.join(sys.argv[0].split(os.path.sep)[:-1])

		self.db = self.path + "db/db.xlsx"
		self.inventory = self.path + "inventory.xlsx"
		self.lastConfigGen = "" ## 마지막으로 실행한 config 생성 session
		self.fullSession = {"fullv4":["init", "base", "loop0", "p2pip", "bgpv4", "etcport", "vxlan"] , "fullv6": ["init", "base", "loop0", "p2pipv6", "bgpv6", "etcport", "vxlan"]}
		self.sessions = list(set(self.fullSession["fullv4"] + self.fullSession["fullv6"]))
  
		self.ymlInit()
		self.norInit()
  
	def resource_path(self, relative_path):
		try:
			# PyInstaller에 의해 임시폴더에서 실행될 경우 임시폴더로 접근하는 함수
			base_path = sys._MEIPASS
		except Exception:
			base_path = os.path.abspath(".")
		return os.path.join(base_path, relative_path)

	def ymlInit(self):
		file_location = self.inventory

	
		with open(self.resource_path("excelEnvriment.json"), "r") as f:
			excelVar = json.load(f)
			f.close()

		workbook = load_workbook(filename=file_location, read_only=False, data_only=True)
		fabric_name = getExcelSheetValue(workbook, excelVar["all"]["fabricName"])

		avd = {
			"inventory": None,
			"group_vars": {
				fabric_name: None
			}
		}

		avd["inventory"] = generateInventory(file_location, excelVar)

		with BlankNone(), open("./inventory/inventory.yml", "w") as inv:
			inv.write(yaml.dump(avd["inventory"], sort_keys=False))
  
	def norInit(self):
		self.nr = InitNornir(config_file=self.resource_path("./config.yml"))
		return self.nr
  

	def cleanConfigCall(self):
   
		##### 자동백업
		self.backupConfigCall(memo="스위치 초기화로인한 자동 백업")
  
		self.nr.run(task=self.cleanConfig)
		self.norInit()

		log = "초기화"
		self.log(desc=log, cfgBackUp=False)

		return self.nr
  
	def cleanConfig(self, task: Task):
		mgmtVrf = task.host.defaults.data["MGMT_VRF"]
		mgmtGw = task.host.defaults.data["MGMT_GW"]
		mgmtInterface = task.host.defaults.data["MGMT_INTERFACE"]
  
		vrfConfig = f"vrf {mgmtVrf}"
		vrfInstance = f"vrf instance {mgmtVrf}"


		cleanConfig = ["configure session", \
									"rollback clean-config", \
									f"{vrfInstance}", \
									f"interface {mgmtInterface}", \
									f"{vrfConfig}", \
									f"ip address {task.host.hostname}/24", \
									f"username {task.host.username} secret {task.host.password} privilege 15", \
									f"ip route {vrfConfig} 0/0 {mgmtGw}", \
									"ip routing", \
									"logging buffered 1000", \
									"logging console informational", \
									"logging monitor informational", \
									"logging synchronous level all", \
									"commit"]
  
		result = task.run(netmiko_send_config, config_commands=cleanConfig)
  
		# self.norInit()
		result = Result(
			host=task.host,
			result=task.run(netmiko_send_config, config_commands=cleanConfig)
		)
		return result
  
	def getBackupConfigList(self):
  
		workbook = load_workbook(filename=self.db, read_only=True, data_only=True)

		return workbook["db"]

	def selectedConfigCall(self, item):
		self.nr.data.reset_failed_hosts()
		self.nr.run(task=self.sendConfig, dir=f"config_backup/{item}")
		return self.nr

			
	def sendConfig(self, task: Task, dir):
		"""
		config 배포
		"""
		result = Result(
			host=task.host,
			result=task.run(netmiko_send_config, config_file=f"./inventory/{dir}/{task.host.name}.cfg")
		)
		return result
 
	def sendConfigCall(self):
		"""
		config 배포 호출
		"""
		self.nr.data.reset_failed_hosts()
		self.nr.run(task=self.sendConfig, dir="config")
		session = self.lastConfigGen
		log = f'{session} config 배포'

		self.log(desc=log, cfgBackUp=True)
  
		return self.nr
   
	def sendConfigCheck(self):
		# print(f"마지막 config gen {self.lastConfigGen}")
		if self.lastConfigGen == "backup" or not self.lastConfigGen:
			return False
		else:
			return True
 
	def getLastConfigGen(self):
		return self.lastConfigGen
 
	def backupConfig(self, task: Task, now):
		
		taskHost = task.host
		taskResult = task.run(netmiko_send_command, command_string="show running-config")

		with open(f"./inventory/config_backup/{now}/{taskHost}.cfg", "w") as inv:
			inv.write(taskResult[0].result)
			inv.close()
				
		return Result(
			host=taskHost,
			result=taskResult,
		)

	def backupConfigCall(self, memo):
		self.nr.data.reset_failed_hosts()
		now = datetime.now()
		folderName = now.strftime("%y%m%d%H%M%S")
		nowDate = now.strftime('%y-%m-%d %H:%M:%S')
  
		directory = f"./inventory/config_backup/{folderName}"
		if not os.path.exists(directory):
			os.makedirs(directory)
  
		self.nr.run(task=self.backupConfig, now=folderName)
   
   
		workbook = load_workbook(filename=self.db, read_only=False, data_only=True)
		sheet = workbook["db"]
		sheet.append([memo, folderName, nowDate])
		workbook.save(self.db)
  
		return self.nr

	def createTopology(self, topology, cpu, ram, ethernetCount, version, net, icon, configInclude):

		spineSwitchs = {}
		leafSwitchs = {}

		with open("./inventory/hosts.yml") as f:
			hosts = yaml.load(f, Loader=yaml.FullLoader)
			f.close()

		for host in hosts:
			hostType = hosts[host]["data"]["TYPE"]

			if (hostType.upper() == "SPINE"):
				spineSwitchs.setdefault(
					host, {}
				)
			else:
				leafSwitchs.setdefault(
					host, {}
				)
		
		spinesCount = len(spineSwitchs)
		leafsCount = len(leafSwitchs)
		width = 1920
		space = 200 ## switch icon 사이 간격
		leafSpace = 200
		spineTopMargin = 200
		leafTopMargin = 600
		iconWidth = 65
  
		spineIdx = 0
		leafIdx = spinesCount
  
		## spine icon 시작 위치값
		# s_start = int(width / spinesCount - space / spinesCount)
		# if eq(1, spinesCount):
		# 	s_start = int(width / 2 - (iconWidth / 2))
  
		s_start = width - (int(iconWidth * spinesCount) + int((space * (spinesCount - 1))))
		s_start = int(s_start / 2)
  
		if s_start < 10:
			s_start = 10
				
  
		## leaf icon 시작 위치값
		# l_start = int(width / leafsCount + space - (iconWidth/2))
		l_start = width - (int(iconWidth * leafsCount) + int((leafSpace * (leafsCount - 1))))
		l_start = int(l_start / 2)

		if l_start < 10:
			l_start = 10
  
		configs = {}
		for host in hosts:
			hostType = hosts[host]["data"]["TYPE"]
			# print("host type = ", host)
			###### config 포함시 base64로 인코딩 처리
			if configInclude:
				# print("config 포함")
				with open(f"./inventory/config/{host}.cfg") as r:
					config = base64.b64encode(r.read().encode('ascii')).strip().decode('utf-8')
					configState = 1
					r.close()
     
			else:
				configState = 0
				
			if (hostType.upper() == "SPINE"):
				spineIdx = spineIdx + 1
				spineSwitchs[host]= {
															"ID": spineIdx,
															"LEFT": s_start + (spineIdx * space),
															"TOP": spineTopMargin,
															"CONFIG": configState
														}
				configs.setdefault(spineIdx, config)
			else:
				leafIdx = leafIdx + 1
				leafSwitchs[host]= {
															"ID": leafIdx,
															"LEFT": l_start + (leafIdx * leafSpace),
															"TOP": leafTopMargin,
															"CONFIG": configState
														}
				configs.setdefault(leafIdx, config)
  
		# print(configs)
		with open("./inventory/topologyInterfaces.yml") as f:
			topologyInterfaces = yaml.load(f, Loader=yaml.FullLoader)
			f.close()

		topologyName = topology
		data = {
			"NAME": topologyName,
			"EOS_VERSION": version,
			"CPU": cpu,
			"RAM": ram,
			"ETHERNET": ethernetCount,
			"SPINES": spineSwitchs,
			"LEAFS": leafSwitchs,
			"NET": net,
			"INTERFACES": topologyInterfaces,
			"SWITCH_ICON": icon, 
			"CONFIGS": configs
		}
		
  
  
		directory = f"./topology"
		if not os.path.exists(directory):
			os.makedirs(directory)
  
		file = f'./{topologyName}.unl'
  
		with open('./inventory/templates/topology/topology.j2') as f:
			template = Template(f.read())
		with BlankNone(), open(f'{file}', "w", encoding='utf8') as reqs:   
				reqs.write(template.render(**data))
				reqs.close() 
    
    
		zipOutput = f'./{directory}/{topologyName}.zip'
		
		zipFile = zipfile.ZipFile(zipOutput, "w")
		
		zipFile.write(file, compress_type=zipfile.ZIP_DEFLATED)

		zipFile.close()
  
		os.remove(file)
    
    
	def createSimpleTopology(self, topology, spinePrefix, leafPrefix, spinesCount, leafsCount, version, cpu, ram, ethernetCount, net, icon):
    
		spineSwitchs = {}
		leafSwitchs = {}
  
		width = 1920
		space = 200 ## switch icon 사이 간격
		leafSpace = 200
		spineTopMargin = 200
		leafTopMargin = 600
		iconWidth = 50
  
		spineIdx = 0
		leafIdx = 0

		###### ethernetCount 체크
		if (ethernetCount < leafsCount):
			ethernetCount = leafsCount + 3

		## spine icon 시작 위치값
		# s_start = int(width / spinesCount - space / spinesCount)
		# if eq(1, spinesCount):
		# 	s_start = int(width / 2 - (iconWidth / 2))
  
		s_start = width - (int(iconWidth * spinesCount) + int((space * (spinesCount - 1))))
		s_start = int(s_start / 2)
  
		if s_start < 10:
			s_start = 10
				
  
		## leaf icon 시작 위치값
		# l_start = int(width / leafsCount + space - (iconWidth/2))
		l_start = width - (int(iconWidth * leafsCount) + int((leafSpace * (leafsCount - 1))))
		l_start = int(l_start / 2)

		if l_start < 10:
			l_start = 10
     
		for i in range(1, spinesCount + 1):
			spineIdx = spineIdx + 1
			spineName = spinePrefix + str(i)
			spineSwitchs.setdefault(
					spineName, {
						"ID": spineIdx,
						"LEFT": s_start + (spineIdx * space),
						"TOP": spineTopMargin
					}
			)
   
		space = space - (leafsCount * 3)
		if space < 50:
			space = 50
   
		for i in range(1, leafsCount + 1):
			leafIdx = leafIdx + 1
			leafName = leafPrefix + str(i)
			leafSwitchs.setdefault(
					leafName, {
						"ID": leafIdx + spinesCount + 10,
						"LEFT": l_start + (leafIdx * space),
						"TOP": leafTopMargin
					}
			)

		topologyInterfaces = {}
  
		id = 0
		
		leafPort = 0
		for spine in spineSwitchs:
			leafPort = leafPort + 1
			spinePort = 0
			for leaf in leafSwitchs:
				id = id + 1
				spinePort = spinePort + 1
    
				topologyInterfaces.setdefault(
					id, {
						"START": spine,
						"SPORT": "Et" + str(spinePort),
						"END": leaf,
						"EPORT": "Et" + str(leafPort),
					}
				)
  
		topologyName = topology
  
		data = {
			"NAME": topologyName,
			"EOS_VERSION": version,
			"CPU": cpu,
			"RAM": ram,
			"ETHERNET": ethernetCount,
			"SPINES": spineSwitchs,
			"LEAFS": leafSwitchs,
			"INTERFACES": topologyInterfaces,
			"NET": net,
			"SWITCH_ICON": icon
		}
		
		# print(data)
  
		directory = f"./topology"
		if not os.path.exists(directory):
			os.makedirs(directory)
  
		file = f'./{topologyName}.unl'
  
		with open('./inventory/templates/topology/topology.j2') as f:
			template = Template(f.read())
		with BlankNone(), open(f'{file}', "w", encoding='utf8') as reqs:   
				reqs.write(template.render(**data))
				reqs.close() 
    
		zipOutput = f'./{directory}/{topologyName}.zip'
		
		zipFile = zipfile.ZipFile(zipOutput, "w")
		
		zipFile.write(file, compress_type=zipfile.ZIP_DEFLATED)

		zipFile.close()
  
		os.remove(file)

	def createConfig(self, session):
		self.lastConfigGen = session
  
		workbook = load_workbook(filename=self.inventory, read_only=True, data_only=True)
		j2 = ""
  
		if session in self.fullSession:
			for ss in self.fullSession[session]:
				sheet = workbook[ss]
				if sheet.iter_rows():
					for row in sheet.iter_rows():
						j2 = j2 + row[0].value + "\n"
		else:
			sheet = workbook[session]
			if sheet.iter_rows():
				for row in sheet.iter_rows():
					j2 = j2 + row[0].value + "\n"
				

		template = Template(j2)
      
		for host in self.nr.inventory.hosts:
			data = {}
			for k in self.nr.inventory.hosts[host].keys():
				data.setdefault(k, self.nr.inventory.hosts[host][k])

			with open("./inventory/config/" + host + ".cfg", "w", encoding='utf8') as reqs:   
				reqs.write(template.render(**data))
				reqs.close() 
		return self.nr

	def statusCheck(self, task: Task):

		data = {}
		result = result=task.run(netmiko_send_command, command_string="show clock | json")
  
		r = json.loads(result[0].result)
		data.setdefault(
			"timezone", r["timezone"]
		)
		year = r["localTime"]["year"] 
		month = r["localTime"]["month"] 
		day = r["localTime"]["dayOfMonth"] 
		hour = r["localTime"]["hour"] 
		min = r["localTime"]["min"] 
		sec = r["localTime"]["sec"] 
		now = f'{year}-{month}-{day} {hour}:{min}:{sec}' 
		data.setdefault(
			"date", now
		)
  
		result = result=task.run(netmiko_send_command, command_string="show version | json")

		r = json.loads(result[0].result)
		
		data.setdefault(
			"model", r["modelName"]
		)
  
		data.setdefault(
			"version", r["version"]
		)
		return data

	def statusCheckCall(self):
		self.nr.data.reset_failed_hosts()
		return self.nr.run(task=self.statusCheck)
		
  
	def pingTest(self, task: Task):
		self.nr.data.reset_failed_hosts()
		cmd = "show ip interface | json"
  
		dictPing = collections.OrderedDict()
		listPing = ["Name","Local_address","Peer_address","Result", "Mtu","Description","Vrf"]

		returnInfo = task.run(netmiko_send_command, command_string=cmd)
		returnInfo = json.loads(returnInfo[0].result)
		# print(returnInfo)
		# returnInfo = returnInfo.result[0]
		# print("==================================s")
		# print(returnInfo["interfaces"])
		# for item in returnInfo:
				# print(item)
		# print("==================================e")
		# pingTarget = []
		p = re.compile("Ethernet")
		
		for interface in returnInfo["interfaces"]:
			# print("interface = ", interface)
			#### ethernet interface만 체크
			if (p.match(interface)):
				maskLen = returnInfo["interfaces"][interface]["interfaceAddress"]["primaryIp"]["maskLen"]
				# print(maskLen)
				if not interface in dictPing.keys():
					dictPing[interface] = collections.OrderedDict(zip(listPing, [''] * len(listPing)))
					dictPing[interface]["vrf"] = returnInfo["interfaces"][interface]["vrf"]
					# line protocol status 를 view 에서 제거 하기 위해서
					if returnInfo["interfaces"][interface]["lineProtocolStatus"] != "up":
						dictPing[interface]["result"] = "down"
					else:
						dictPing[interface]["result"] = "up"
					
					interfacename = returnInfo["interfaces"][interface]["name"]
					dictPing[interface]["name"] = interfacename
					# peer_address 계산
					localAddr = returnInfo["interfaces"][interface]["interfaceAddress"]["primaryIp"]["address"]
					tempAddr = localAddr.split('.')
					if maskLen == 31:
						if int(tempAddr[3]) % 2 == 0:
							tempAddr[3] = str(int(tempAddr[3]) + 1)
						else:
							tempAddr[3] = str(int(tempAddr[3]) - 1)
					elif maskLen == 30:
						
						if int(tempAddr[3]) % 2 == 0:
							tempAddr[3] = str(int(tempAddr[3]) - 1)
						else:
							tempAddr[3] = str(int(tempAddr[3]) + 1)
					else:
						tempAddr = returnInfo["interfaces"][interface]["interfaceAddress"]["broadcastAddress"].split('.')
					dictPing[interface]["peerAddress"] = ".".join(tempAddr)
					dictPing[interface]["localAddress"] = localAddr + "/" + str(maskLen)
		# pprint.pprint(dictPing)
  
		pingResult = {"success":0, "fail": 0, "down": 0}
		for peer in dictPing:
			peerIP = dictPing[peer]["peerAddress"]
			source = dictPing[peer]["name"]
			vrf = dictPing[peer]["vrf"]
   
			cmd = f'ping vrf {vrf} {peerIP} source {source} repeat 1'
			print(f'{task.host} {cmd}')
			result = task.run(netmiko_send_command, command_string=cmd)
			if " 0% packet loss" in result[0].result:
				pingResult["success"] = int(pingResult["success"]) + 1
			else:
				pingResult["fail"] = int(pingResult["fail"]) + 1
    
			if dictPing[peer]["result"] == "down":
				pingResult["down"] = int(pingResult["down"]) + 1
		
		return pingResult
    
	def pingTestCall(self):
		self.nr.data.reset_failed_hosts()
		return self.nr.run(self.pingTest)

	def log(self, desc=None, cfgBackUp=False):
		directory = f"./log"
  
		now = datetime.now()
		logTime = now.strftime("%y%m%d%H%M%S")
		logFile = now.strftime("%y%m%d%H")
		folder = now.strftime("%y%m%d")
		nowDate = now.strftime('%y-%m-%d %H:%M:%S')
		logDateFolder = f"{directory}/{folder}"
		logCfg = f'{logDateFolder}/{logTime}'
  
		if not os.path.exists(directory):
			os.makedirs(directory)

		if not os.path.exists(logDateFolder):
			os.makedirs(logDateFolder)
   
		with open(f'{logDateFolder}/{logFile}', "a", encoding='utf8') as reqs:   
			for host in self.nr.inventory.hosts:
				if host in self.nr.data.failed_hosts:
					log = f'{nowDate} {host} {desc} 실패'
				else:
					log = f'{nowDate} {host} {desc} 완료'

				reqs.write(f'{log}\n')
		reqs.close()
		
		

		if cfgBackUp:
			if not os.path.exists(logCfg):
				shutil.copytree("./inventory/config/", f'{logCfg}')


		
				
				
    
    