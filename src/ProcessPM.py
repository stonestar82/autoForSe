import os, re, json
from tqdm import tqdm
from datetime import datetime
from operator import eq, ne


class ProcessPM():
	def __init__(self) -> None:
		self.path = "./pm"
		self.hostnamePattern = "\nhostname\s(.*)"
		self.showtechPath = f"{self.path}/showtech/"
		self.showCmdPatternPrefix = "------------- "
		self.showCmdPatternSuffix = " -------------"
		self.showCmdPattern = f"({self.showCmdPatternPrefix}show .*?{self.showCmdPatternSuffix})"
		
  
	def showtechToReport(self):

		print("show tech-suport parsing\n\n")
		##### 폴더 생성
		now = datetime.now()
		folderName = now.strftime("%y%m%d%H%M%S")
		
  
		directory = f"./pm/report/{folderName}"
		tmpDirectory = f"{directory}/show/tmp"
		showDirectory = f"{directory}/show"
		dataDirectory = f"{directory}/data"
  
		if not os.path.exists(directory):
			os.makedirs(directory)
   
		if not os.path.exists(showDirectory):
			os.makedirs(showDirectory)
  
		if not os.path.exists(dataDirectory):
			os.makedirs(dataDirectory)
  
  
		showtechList = os.listdir(self.showtechPath)
		
		for showtech in showtechList:
			print("\n\n", showtech, " 처리중")
   
			if not os.path.exists(tmpDirectory):
				os.makedirs(tmpDirectory)
				
			with open(f"{self.showtechPath}/{showtech}") as r:
				rl = r.readlines()
				config = []
				cmd = ""
				preCmd = ""
				
				p = re.compile(self.showCmdPattern)
				# bar = progressbar.ProgressBar(maxval=len(rl)).start()
				pbar = tqdm(rl)
				for line in pbar:
					cmdPattern = p.match(str(line).strip())
					# bar.update(idx)
					if cmdPattern:
						preCmd = cmd
						cmd = cmdPattern.group().replace(self.showCmdPatternPrefix, "").replace(self.showCmdPatternSuffix, "").replace("|", "--")

						if ne(preCmd, ""):
							with open(f"{tmpDirectory}/{preCmd}", "w") as f:
								f.write("".join(config))
								f.close

						config = []
      
					else:
						config.append(line)

				with open(f"{tmpDirectory}/{cmd}", "w") as f:
					f.write("".join(config))
					f.close()

				pbar.close()
    
			r.close()
   
			with open(f"{tmpDirectory}/show running-config sanitized") as r:
				c = r.read()
				result = re.findall(self.hostnamePattern, c)
				hostname = result[0]
				r.close()
   
   
			os.rename(f"{tmpDirectory}", f"{showDirectory}/{hostname}")
   
		self.showToData(folderName)
    
	def showToData(self, folder):
  
		directory = f"./pm/report/{folder}"
		showDirectory = f"{directory}/show"
		dataDirectory = f"{directory}/data"
  
		hostList = os.listdir(showDirectory)
  
		for host in hostList:
			hostPath = f"{showDirectory}/{host}"
			print(hostPath)
			# hostShowList = os.listdir(hostPath)
			# print(hostShowList)
   
			data = { "hostname-host": host}
   
			##### show version detail
			##### serial, model, total memory, free memory, free memory per, uptime, eos version
			with open(f"{hostPath}/show version detail") as f:
				
				c = f.read()
				f.seek(0)
				l = f.readlines()
			f.close()

			serial = str(re.findall("Serial number: (.*)", c)[0]).strip()
			model = re.findall("[A-Z0-9-]{8,30}", l[1])[0]
			totalMemory = re.findall("Total memory: (.*) kB", c)[0]
			freeMemory = re.findall("Free memory: (.*) kB", c)[0]
			memoryFreePercent = str(int((int(totalMemory) - int(freeMemory)) / int(totalMemory) * 100)) + "%"
			uptime = re.findall("Uptime: (.*)", c)[0]
			esoVersion = re.findall("Software image version: (.*)", c)[0]

	
			data.setdefault("version detail-serial", serial)
			data.setdefault("version detail-model", model)
			data.setdefault("version detail-total memory", str(totalMemory).strip())
			data.setdefault("version detail-free memory", str(freeMemory).strip())
			data.setdefault("version detail-free memory percent", memoryFreePercent)
			data.setdefault("version detail-uptime", str(uptime).strip())
			data.setdefault("version detail-eos version", str(esoVersion).strip())
				
    
			# print(data)
    
    
			##### show ip interface brief
			##### host ip(mgmt)
			with open(f"{hostPath}/show ip interface") as f:
				c = f.read()
			f.close()
			## description 이 없는경우
			hostIp = re.findall("Management(\d) is up, line protocol is up \(connected\)\n  Internet address is (.*)", c)

			if hostIp:
				hostIp = list(hostIp[0])[1]

			## description 이 있는경우
			else:
     
				hostIp = re.findall("Management(\d) is up, line protocol is up \(connected\)\n(.*)\n  Internet address is (.*)", c)
    
				if hostIp:
					hostIp = list(hostIp[0])[2]
				else:
					hostIp = "N\A"
				
   
			# print(hostIp)
    
			data.setdefault("ip interface-hostip", hostIp)


			##### show system venvironment power detail
			##### supply
			powerFind = False
   
			## 버전에 따라 다른듯
			powerDetail = f"{hostPath}/show system environment power detail"
   
			if not os.path.exists(f"{hostPath}/show system environment power detail"):
				powerDetail = f"{hostPath}/show environment power detail"
   
			with open(powerDetail) as f:
				l = f.readlines()	
			f.close()
   
			
			powerSupply = []
			psIdx = 0
			for r in l:
				if "PWR-" in r and not powerFind:
					powerFind = True

				if "PWR-" in r:
					psIdx = psIdx + 1
					if "Ok" in r:
						status = f"power-supply {psIdx}: 무"
					else:
						status = f"power-supply {psIdx}: 유"

					powerSupply.append(status)
     
				if powerFind and not "PWR-" in r:
					break
   

			data.setdefault("system environment power detail-power system", powerSupply)


			with open(f"{hostPath}/data.json", "w", encoding='utf8') as f:   
				json.dump(data, f)
			f.close()
			
			print(data)