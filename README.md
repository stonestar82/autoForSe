# autoForSe
# autoForSe

# windows
pyinstaller -F --icon=./icloud.ico --add-data="icloud.ico;." --add-data="excelEnvriment.json;." -n=i-CloudAutomation exec.py

# mac
## mac에서는 .ico는 인식안됨. -w 옵션이 들어가야 실행파일에 아이콘이 들어감
pyinstaller -F --icon=icloud.icns --add-data="icloud.icns:." --add-data="icloud.png:." --add-data="excelEnvriment.json:." -n=i-CloudAutomation exec.py
