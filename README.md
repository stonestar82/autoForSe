# autoForSe
# autoForSe

# windows
pyinstaller -F --icon=./icloud.ico --add-data="icloud.ico;." --add-data="excelEnvriment.json;." --add-data="config.yml;." -n=icloudautomation exec.py

# mac
pyinstaller -F --icon=./icloud.ico --add-data="icloud.ico:." --add-data="excelEnvriment.json:." --add-data="config.yml:." -n=icloudautomation exec.py
