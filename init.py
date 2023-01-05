import yaml, json
from generators.generateInventory import generateInventory 
from jinja2 import Template
from generators.BlankNone import BlankNone
from operator import eq
from generators.BlankNone import *
from openpyxl import load_workbook

def taskPrint(task):
	task = task + " "
	print(task.ljust(100, "*") + "\n")

def main():
    
	taskPrint("TASK [Start]")	

	## 엑셀파일 지정
	file_location = "./inventory.xlsx"
	
	with open("./excelEnvriment.json", "r") as f:
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

	taskPrint("TASK [inventory Parsing]")
	## 엑셀에서 데이터를 읽어 inventory 정보 처리 d1.yml, all.yml 파일 생성
	avd["inventory"] = generateInventory(file_location, excelVar)

	## Create inventory file
	## yaml.dump시 sort_keys=False 값을 주지 않으면 키값 기준으로 오름차순으로 정렬되어 적용됨
	## sort_keys=False 실제 적용한 값 순서대로 처리
	taskPrint("TASK [inventory.yml Generate]")
	with BlankNone(), open("./inventory/inventory.yml", "w") as inv:
			inv.write(yaml.dump(avd["inventory"], sort_keys=False))

if __name__ == "__main__":
	main()