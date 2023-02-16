#-*- coding:utf-8 -*-
import shutil, os, platform, sys
from operator import eq
from jinja2 import Template
from datetime import datetime, timedelta
import subprocess, py_compile

now = datetime.now()		
now = now.strftime("%Y%m%d")


if eq(platform.system().lower(), "windows"):
  path = "."
  icon = "icloud.ico"
  cmd = f'pyinstaller -F --icon=./{icon} --add-data="{icon};." --add-data="excelEnvriment.json;." --distpath="release/dist" -n=i-CloudAutomation release/execCompile.pyc {now}'
else:
  ## mac에서는 .ico는 인식안됨. -w 옵션이 들어가야 실행파일에 아이콘이 들어감
  path = os.path.sep.join(sys.argv[0].split(os.path.sep)[:-1])
  icon = "icloud.icns"
  cmd = 'pyinstaller -F --icon={icon} --add-data="{icon}:." --add-data="icloud.png:." --add-data="excelEnvriment.json:." -n=i-CloudAutomation release/execCompile.pyc {now}'
  
readyFolder = f"{path}/ready"
execFolder = f"{readyFolder}/dist"
exec = f"{path}/execCompile.py"
toExec = f"{readyFolder}/exec.py"

## 난독화 불가 용량 파일
notInc = ["ProcessMinAnalyzer.py"]



execCreateJ2 = """import os
os.system('{{cmd}}')
"""



###### ready폴더 삭제/생성 및 소스 복사, exec.py 생성
if os.path.exists(f"{readyFolder}/src"):
  shutil.rmtree(f"{readyFolder}/src")  ##### 하위 폴터파일 전부 삭제
  
if os.path.exists(f"{readyFolder}/dist"):
  shutil.rmtree(f"{readyFolder}/dist")  ##### 하위 폴터파일 전부 삭제


if os.path.exists(f"{readyFolder}/lib"):
  shutil.rmtree(f"{readyFolder}/lib")  ##### 하위 폴터파일 전부 삭제

###### 기존 ready 폴더 삭제
if os.path.exists(readyFolder):
  shutil.rmtree(readyFolder)  ##### 하위 폴터파일 전부 삭제

os.mkdir(readyFolder)
  
shutil.copytree(f"{path}/src", f"{readyFolder}/src")
shutil.copytree(f"{path}/lib", f"{readyFolder}/lib")

###### 난독처리


  
  
###### dist 폴더에 db.xlsx, config.js2, inventory.xlsx, topology.j2, defaults.j2 복사
shutil.copy(exec, toExec)

###### 난독화 불가파일 삭제
src_dir = readyFolder

src_list = os.listdir(f"{src_dir}/src")

# 소스파일의 리스트에서 파일 하나씩 처리한다
for dst_file in src_list:
  if (dst_file.endswith('.py')):
    if dst_file in notInc:
      os.remove(f"{src_dir}/src/{dst_file}")

now = datetime.now() + timedelta(days=60)
now = now.strftime("%Y%m%d")

print(f"날자 정보 = ", now)

print("complete~!")