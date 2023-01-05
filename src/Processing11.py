from operator import mod
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_config, netmiko_send_command
from nornir.core.task import Task, Result, AggregatedResult
from nornir_utils.plugins.functions import print_result
from nornir.core.filter import F
from jinja2 import Template

class Processing():
  
	def __init__(self):
		self.nr = InitNornir(config_file="./config.yml")
		self.sessions = ["base", "init", "p2pip", "loop0", "bgpv4", "vxlan", "etcport"]

	# print(nr.inventory.hosts.keys())

	def backupConfig(self, task: Task) -> Result:
		taskHost = task.host
		taskResult = task.run(netmiko_send_command, command_string="show running-config")

		with open(f"./inventory/config_backup_nn/{taskHost}.cfg", "w") as inv:
			inv.write(taskResult[0].result)
			inv.close()
				
		return Result(
			host=taskHost,
			result=taskResult,
		)
		
	async def createConfig(self, task: Task, session) -> Result:
		if session.lower() not in self.sessions:
			print("잘못된 파라미터값입니다.")
			exit()

		with open('./inventory/templates/config/' + session + '.j2', encoding='utf8') as f:
			template = Template(f.read())
			f.close()	
   
		for host in self.nr.inventory.hosts:
			data = {}
		for k in self.nr.inventory.hosts[host].keys():
			data.setdefault(k, self.nr.inventory.hosts[host][k])
			
		with open("./inventory/config/" + host + ".cfg", "w", encoding='utf8') as reqs:   
			reqs.write(template.render(**data))
			reqs.close() 

	def sendConfig(task1: Task) -> Result:
		result = Result(
			host=task1.host,
			result=task1.run(netmiko_send_config, config_file=f"./inventory/config/{task1.host.name}.cfg")
		)
		print("print host-----------")
		print(result.result[0].result)
		return result

	def spineOddFilter(host):
		# print(host.data["ID"])
		id = host.data["ID"]
		f = int((mod(id, 2) == 1))
		# print(f)
		return f


		result = self.nr.run(task=sendConfig)

	## 그룹 필터 스파인
	# cmh_and_spine = nr.filter(F(groups__contains="spine"))
	# print(cmh_and_spine.inventory.hosts.keys())

	## 그룹 필터 스파인 홀수
	# cmh_and_spine = nr.filter(F(groups__contains="spineOdd"))
	# print(cmh_and_spine.inventory.hosts.keys())

	# ## 그룹 필터 스파인 짝수
	# cmh_and_spine = nr.filter(F(groups__contains="spineEven"))
	# print(cmh_and_spine.inventory.hosts.keys())


	## 그룹 필터 leaf
	# cmh_and_spine = nr.filter(F(groups__contains="leaf"))
	# print(cmh_and_spine.inventory.hosts.keys())

	## 그룹 필터 leaf TYPE = Leaf
	# cmh_and_spine = nr.filter(F(groups__contains="leaf") & F(TYPE="Leaf"))
	# print(cmh_and_spine.inventory.hosts.keys())


	## 그룹 필터 leaf  TYPE != Leaf 가 아닌것
	# cmh_and_spine = nr.filter(F(groups__contains="leaf") & ~F(TYPE="Leaf"))
	# print(cmh_and_spine.inventory.hosts.keys())

	# cmh_and_spine = nr.filter(F(groups__contains="leaf") & ~F(TYPE="Leaf"))
	# print(cmh_and_spine.inventory.hosts.keys())

	## 필터 함수
	# h = nr.filter(filter_func=spineOddFilter)
	# print(h.inventory.hosts.keys())

	# cmh_and_spine = nr.filter(F(TYPE="BL"))
	# print(cmh_and_spine.inventory.hosts.keys())

	# nr.inventory.children_of_group("spine")

	# print(nr.inventory.hosts.keys())