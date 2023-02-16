#-*- coding:utf-8 -*-
import shutil, os, platform, sys
from operator import eq
from jinja2 import Template
from datetime import datetime, timedelta
import subprocess, py_compile


kkk = "83BC0105E48BF7878DE20DA02A5AF235"

if eq(platform.system().lower(), "windows"):
  path = "."
  icon = "icloud.ico"
  cmd = f'pyinstaller -F --icon=./{icon} --add-data="{icon};." --add-data="excelEnvriment.json;." --key={kkk} --distpath="release" -n=i-CloudAutomation execCompile.py'
else:
  ## mac에서는 .ico는 인식안됨. -w 옵션이 들어가야 실행파일에 아이콘이 들어감
  path = os.path.sep.join(sys.argv[0].split(os.path.sep)[:-1])
  icon = "icloud.icns"
  cmd = f'pyinstaller -F --icon={icon} --add-data="{icon}:." --add-data="icloud.png:." --add-data="excelEnvriment.json:." --key={kkk} --distpath="release" -n=i-CloudAutomation execCompile.py'
  
releaseFolder = f"{path}/release"
execFolder = f"{releaseFolder}/dist"
execSample = f"{path}/dist-sample"
inventoryXlsx = f"{path}/inventory.xlsx"
toInventoryXlsx = f"{releaseFolder}/inventory.xlsx"
configJ2 = f"{path}/inventory/templates/inventory/config.j2"
toConfigJ2 = f"{releaseFolder}/inventory/templates/inventory/config.j2"
defaultsJ2 = f"{path}/inventory/templates/inventory/defaults.j2"
toDefaultsJ2 = f"{releaseFolder}/inventory/templates/inventory/defaults.j2"
topologyJ2 = f"{path}/inventory/templates/topology/topology.j2"
toTopologyJ2 = f"{releaseFolder}/inventory/templates/topology/topology.j2"
dbXlsx = f"{path}/dist-sample/db.xlsx"
toDbXlsx = f"{releaseFolder}/db/db.xlsx"
copyIco = f"{path}/{icon}"
toCopyIco = f"{releaseFolder}/{icon}"
envJson = f"{path}/excelEnvriment.json"
toEnvJson = f"{releaseFolder}/excelEnvriment.json"
exec = f"{path}/execCompile.py"
toExec = f"{releaseFolder}/exec.py"

###### release폴더 삭제/생성 및 소스 복사, exec.py 생성
if os.path.exists(f"{releaseFolder}"):
  shutil.rmtree(f"{releaseFolder}")  ##### 하위 폴터파일 전부 삭제

os.mkdir(f"{releaseFolder}")


os.makedirs(f"{releaseFolder}/db")
os.makedirs(f"{releaseFolder}/inventory")
os.makedirs(f"{releaseFolder}/inventory/config")
os.makedirs(f"{releaseFolder}/inventory/backup_config")
os.makedirs(f"{releaseFolder}/inventory/templates")
os.makedirs(f"{releaseFolder}/inventory/templates/inventory")
os.makedirs(f"{releaseFolder}/inventory/templates/topology")
  
  
###### dist 폴더에 db.xlsx, config.js2, inventory.xlsx, topology.j2, defaults.j2 복사
shutil.copy(configJ2, toConfigJ2)
shutil.copy(dbXlsx, toDbXlsx)
shutil.copy(inventoryXlsx, toInventoryXlsx)
shutil.copy(defaultsJ2, toDefaultsJ2)
shutil.copy(topologyJ2, toTopologyJ2)



###### exec 생성
# filepath = f"python release/createExec.py"
# subprocess.check_output(filepath, shell=True)

# os.remove(f"{src_dir}/createExec.py")

print(cmd)
os.system(cmd)
print("complete~!")