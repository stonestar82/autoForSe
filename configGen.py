from operator import mod
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_config, netmiko_send_command
from nornir.core.task import Task, Result, AggregatedResult
from nornir_utils.plugins.functions import print_result
from nornir.core.filter import F
import json
from jinja2 import Template
import sys

if len(sys.argv) != 2:
  print("파라미터값이 적용되지 않았습니다.")
  exit()
else:
  session = sys.argv[1]

sessions = ["base", "init", "p2pip", "loop0", "bgpv4", "vxlan", "etcport"]

if session.lower() not in sessions:
  print("잘못된 파라미터값입니다.")
  exit()


  
nr = InitNornir(config_file="./config.yml")



with open('./inventory/templates/config/' + session + '.j2', encoding='utf8') as f:
  template = Template(f.read())
  f.close()
  
# print(nr.inventory.get_hosts_dict())
# print(nr.inventory.hosts['D1-Leaf-01'].data)

# data = {}

# for k in nr.inventory.hosts['D1-Leaf-01'].keys():
# 	# print(k + " = ")
# 	# print(nr.inventory.hosts['D1-Leaf-01'][k])
# 	data.setdefault(k, nr.inventory.hosts['D1-Leaf-01'][k])
# 	with open("./inventory/intended/configs/" + switch[hostNameCol] + ".cfg", "w", encoding='utf8') as reqs:   
#     reqs.write(template.render(**data))
#     reqs.close() 
# print(data)

# print(nr.de)

for host in nr.inventory.hosts:
	data = {}
	for k in nr.inventory.hosts[host].keys():
		data.setdefault(k, nr.inventory.hosts[host][k])
		
	with open("./inventory/config/" + host + ".cfg", "w", encoding='utf8') as reqs:   
		reqs.write(template.render(**data))
		reqs.close() 

def backupConfig(task: Task) -> Result:
	taskHost = task.host
	taskResult = task.run(netmiko_send_command, command_string="show running-config")

	with open(f"./inventory/config_backup_nn/{taskHost}.cfg", "w") as inv:
		inv.write(taskResult[0].result)
		inv.close()
			
	return Result(
		host=taskHost,
		result=taskResult,
	)
		
		
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