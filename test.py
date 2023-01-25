import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import *
import yaml, json
import asyncio, os
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
import zipfile
from src.ProcessImpl import ProcessImpl


obj = ProcessImpl()

now = datetime.now()
obj.log(now=now, desc="D1-Spine-01 init config admin/admin 배포 \n", cfgBackUp=True)
obj.log(now=now, desc="D1-Spine-02 init config admin/admin 배포 \n", cfgBackUp=True)
obj.log(now=now, desc="D1-Spine-02 init config admin/admin 배포 \n", cfgBackUp=True)
obj.log(now=now, desc="D1-Leaf-01 init config admin/admin 배포 \n", cfgBackUp=True)
obj.log(now=now, desc="D1-Leaf-02 init config admin/admin 배포 \n", cfgBackUp=True)
obj.log(now=now, desc="D1-Leaf-03 init config admin/admin 배포 \n", cfgBackUp=True)
obj.log(now=now, desc="D1-Leaf-04 init config admin/admin 배포 \n", cfgBackUp=True)
obj.log(now=now, desc="D1-BL-01 init config admin/admin 배포 \n", cfgBackUp=True)
obj.log(now=now, desc="D1-BL-02 init config admin/admin 배포 \n", cfgBackUp=True)

