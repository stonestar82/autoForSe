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
from src.ProcessLab import ProcessLab
from src.ProcessPM import ProcessPM
import pandas as pd

# obj = ProcessLab()


# obj.sshConnectTest(host="192.168.1.111", user="root", pw="rkqtn!23", port=22)
# obj.labOSAppend(osVersion="veos-4.28.5.1M", host="192.168.1.112", user="root", pw="rkqtn!23", port=22)
# obj.labOSAppend(vendor="arista", osVersion="veos-4.28.4M", host="192.168.1.113", user="root", pw="rkqtn!23", port=22)
# obj.getLabOsList("arista")

# pm = ProcessPM()
# # pm.showtechToReport()
# pm.showToData("230203122905")

inventory_file = "./inventory.xlsx"

				


info = pd.read_excel(inventory_file, sheet_name="Var")[["Variables", "Variables Value", "Prefix & Define", "Prefix & Define Value"]]


print(info)
mgmtInterface = "Management1"
terminalLength = info.loc[[1],["Variables Value"]].values[0][0]
terminalWidth = info.loc[[2],["Variables Value"]].values[0][0]
logginBuffered = info.loc[[3],["Variables Value"]].values[0][0]
spanningTreeMode = info.loc[[5],["Variables Value"]].values[0][0]
mgmtVrf = info.loc[[6], ["Variables Value"]].values[0][0]
mgmtGw = info.loc[[7],["Variables Value"]].values[0][0]
clockTimeZone = info.loc[[9],["Variables Value"]].values[0][0]
adminName = info.loc[[11],["Variables Value"]].values[0][0]
adminPassword = info.loc[[12],["Variables Value"]].values[0][0]
admin_privilege = info.loc[[13],["Variables Value"]].values[0][0]
macAging = info.loc[[16],["Variables Value"]].values[0][0]
arpAging = info.loc[[17],["Variables Value"]].values[0][0]
spineBGPAsn = info.loc[[3],["Prefix & Define Value"]].values[0][0]
spinePrefix = info.loc[[9],["Prefix & Define Value"]].values[0][0]
leafPrefix = info.loc[[10],["Prefix & Define Value"]].values[0][0]
p2pSubnet = info.loc[[14],["Prefix & Define Value"]].values[0][0]

# print(info)
# print(switches.loc[["Variables Value"],[1]].values[0][0])