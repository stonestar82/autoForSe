#-*- coding:utf-8 -*-
import shutil, os, platform, sys
from operator import eq
from jinja2 import Template
from datetime import datetime, timedelta
import subprocess, py_compile


if eq(platform.system().lower(), "windows"):
  path = "."
  icon = "icloud.ico"
  cmd = f'pyinstaller -F --icon=./{icon} --add-data="{icon};." --add-data="excelEnvriment.json;." --distpath="release/dist" -n=i-CloudAutomation exec.pyc'
else:
  ## mac에서는 .ico는 인식안됨. -w 옵션이 들어가야 실행파일에 아이콘이 들어감
  path = os.path.sep.join(sys.argv[0].split(os.path.sep)[:-1])
  icon = "icloud.icns"
  cmd = 'pyinstaller -F --icon={icon} --add-data="{icon}:." --add-data="icloud.png:." --add-data="excelEnvriment.json:." -n=i-CloudAutomation exec.pyc'
  
releaseFolder = f"{path}/release/"
execFolder = f"{releaseFolder}/dist"
execSample = f"{path}/dist-sample"
inventoryXlsx = f"{path}/inventory.xlsx"
toInventoryXlsx = f"{releaseFolder}/dist/inventory.xlsx"
configJ2 = f"{path}/inventory/templates/inventory/config.j2"
toConfigJ2 = f"{releaseFolder}/dist/inventory/templates/inventory/config.j2"
defaultsJ2 = f"{path}/inventory/templates/inventory/defaults.j2"
toDefaultsJ2 = f"{releaseFolder}/dist/inventory/templates/inventory/defaults.j2"
topologyJ2 = f"{path}/inventory/templates/topology/topology.j2"
toTopologyJ2 = f"{releaseFolder}/dist/inventory/templates/topology/topology.j2"
dbXlsx = f"{path}/dist-sample/db.xlsx"
toDbXlsx = f"{releaseFolder}/dist/db/db.xlsx"
copyIco = f"{path}/{icon}"
toCopyIco = f"{releaseFolder}/{icon}"
envJson = f"{path}/excelEnvriment.json"
toEnvJson = f"{releaseFolder}/excelEnvriment.json"
exec = f"{path}/execCompile.py"
toExec = f"{releaseFolder}/exec.py"

###### release폴더 삭제/생성 및 소스 복사, exec.py 생성
if os.path.exists(f"{releaseFolder}/src"):
  shutil.rmtree(f"{releaseFolder}/src")  ##### 하위 폴터파일 전부 삭제


if os.path.exists(f"{releaseFolder}/lib"):
  shutil.rmtree(f"{releaseFolder}/lib")  ##### 하위 폴터파일 전부 삭제

  
shutil.copytree(f"{path}/src", f"{releaseFolder}/src")
shutil.copytree(f"{path}/lib", f"{releaseFolder}/lib")

# data = {"now": now}

# template = Template(execJ2)

# with open(f"{releaseFolder}/exec.py", "w", encoding="utf-8") as inv:
#   inv.write(template.render(**data))
# inv.close()


###### 기존 dist 폴더 삭제
if os.path.exists(execFolder):
  shutil.rmtree(execFolder)  ##### 하위 폴터파일 전부 삭제
  
os.makedirs(execFolder) ##### 폴더만 생성
os.makedirs(f"{execFolder}/db")
os.makedirs(f"{execFolder}/inventory")
os.makedirs(f"{execFolder}/inventory/config")
os.makedirs(f"{execFolder}/inventory/backup_config")
os.makedirs(f"{execFolder}/inventory/templates")
os.makedirs(f"{execFolder}/inventory/templates/inventory")
os.makedirs(f"{execFolder}/inventory/templates/topology")
  
  
###### dist 폴더에 db.xlsx, config.js2, inventory.xlsx, topology.j2, defaults.j2 복사
shutil.copy(configJ2, toConfigJ2)
shutil.copy(dbXlsx, toDbXlsx)
shutil.copy(inventoryXlsx, toInventoryXlsx)
shutil.copy(defaultsJ2, toDefaultsJ2)
shutil.copy(topologyJ2, toTopologyJ2)
shutil.copy(copyIco, toCopyIco)
shutil.copy(envJson, toEnvJson)
shutil.copy(exec, toExec)

###### 난독화
src_dir = releaseFolder
# pyc 파일을 copy할 폴더 이름
src_list = os.listdir(f"{src_dir}/src")


# 소스파일의 리스트에서 파일 하나씩 처리한다
for dst_file in src_list:
  # py 파일을 하나씩 pyc 로 bytecode로 컴파일한다.
  if (dst_file.endswith('.py')):
    # py--> pyc 로 확장자 변경
    compiled_py = dst_file.replace('.py', '.pyc')
    # py 파일을 pyc 로 컴파일하고 output을 target dir에 저장
    py_compile.compile(f"{src_dir}/src/{dst_file}", f"{src_dir}/src/{compiled_py}")          
    os.remove(f"{src_dir}/src/{dst_file}")



src_list = os.listdir(f"{src_dir}/lib")
# 소스파일의 리스트에서 파일 하나씩 처리한다
for dst_file in src_list:
  # py 파일을 하나씩 pyc 로 bytecode로 컴파일한다.
  if (dst_file.endswith('.py')):
    # py--> pyc 로 확장자 변경
    compiled_py = dst_file.replace('.py', '.pyc')
    # py 파일을 pyc 로 컴파일하고 output을 target dir에 저장
    py_compile.compile(f"{src_dir}/lib/{dst_file}", f"{src_dir}/lib/{compiled_py}")          
    os.remove(f"{src_dir}/lib/{dst_file}")


py_compile.compile(f"{releaseFolder}/exec.py", f"{releaseFolder}/exec.pyc")   
os.remove(f"{releaseFolder}/exec.py")



###### exec 생성
# filepath = f"python release/createExec.py"
# subprocess.check_output(filepath, shell=True)

# os.remove(f"{src_dir}/createExec.py")


print(cmd)

print("complete~!")