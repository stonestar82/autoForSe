import asyncio
from src.UI import UI
from src.ProcessAuto import ProcessAuto
from src.ProcessLab import ProcessLab
from src.ProcessPM import ProcessPM
from src.ProcessMinAnalyzer import ProcessMinAlanyzer
from src. ProcessWeb import ProcessWeb
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import *
import yaml, json
import asyncio, os, sys
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_config, netmiko_send_command
from nornir.core.task import Task, Result
from jinja2 import Template
from datetime import datetime
from openpyxl import load_workbook
from lib.BlankNone import *

class App:
	def exec(self, expired):
		self.window = UI(asyncio, ProcessAuto(expired), ProcessLab(), ProcessPM(), ProcessMinAlanyzer())





App().exec(sys.argv[1])