import asyncio
from src.UI3 import UI3
from src.ProcessAuto import ProcessAuto
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import *
import yaml, json
import asyncio, os
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_config, netmiko_send_command
from nornir.core.task import Task, Result
from jinja2 import Template
from datetime import datetime
from openpyxl import load_workbook
from lib.BlankNone import *

class App:
	def exec(self):
		self.window = UI3(asyncio, ProcessAutoImpl())
		# await self.window.show();

App().exec()