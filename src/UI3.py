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
from tkinter.messagebox import askyesno
import platform, time
from async_tkinter_loop import async_handler, async_mainloop

class UI3():
	def __init__(self, asyncio=asyncio, process=ProcessImpl):
		self.asyncio = asyncio
		self.process = process
		self.loop = self.asyncio.get_event_loop()
		# if platform.system()=='Windows':
		# 	asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
		self.root = tk.Tk()
		self.root.title("GlobalTelecom & i-Cloud")
		self.root.geometry("640x500+600+100") ## w, h, x, y
		self.root.resizable(False, False)
  
		self.db = "./db/db.xlsx"
		self.inventory = "./inventory.xlsx"
		self.cpuSize = [1,2]
		self.ethernetSize = []
		for i in range(9, 97):
			self.ethernetSize.append(i)
   
		self.spineSize = [2,4]
		self.leafSize = []
		for i in range(2, 60):
			self.leafSize.append(i)
   
		self.ramSize = [1024, 2048, 3072, 4096]
		self.lastConfigGen = "" ## 마지막으로 실행한 config 생성 session
		self.fullSession = {"fullv4":["init", "base", "loop0", "p2pip", "bgpv4", "etcport", "vxlan"] , "fullv6": ["init", "base", "loop0", "p2pipv6", "bgpv6", "etcport", "vxlan"]}
		self.sessions = list(set(self.fullSession["fullv4"] + self.fullSession["fullv6"]))
  
		self.ymlInit()
		self.norInit()
  
  
		##### grid S #####
		self.frame_top = ttk.Frame(self.root)
		self.frame_top.pack(side="top")


		self.treeview=ttk.Treeview(self.frame_top, columns=["one", "two", "three"])
		self.treeview.tag_configure("green",foreground='green')
		self.treeview.tag_configure("red",foreground='red')

		self.treeview.column("#1", width=180, anchor="center")
		self.treeview.heading("one", text="name", anchor="center")

		self.treeview.column("#2", width=330, anchor="w")
		self.treeview.heading("two", text="description", anchor="center")
  
		self.treeview.column("#3", width=120, anchor="w")
		self.treeview.heading("three", text="datetime", anchor="center")


		self.treeview["show"] = "headings"
		self.treeview.pack()
		##### grid E #####

		##### tab 구현 S #####
		self.notebook = ttk.Notebook(self.root, width=620, height=300, )
		self.notebook.pack()
  
	
		##### 핑테스트
		self.pingTestFrame = ttk.Frame(self.root)
		self.notebook.add(self.pingTestFrame, text=" PING TEST ")
		
		self.pingTestButton = tk.Button(self.pingTestFrame, text="PING TEST", width=18, command=(async_handler(self.pingTestCall)))
		self.pingTestButton.grid(row=0, column=3, sticky=tk.W, padx=(8, 8), pady=(8, 8))
  
		self.root.protocol("WM_DELETE_WINDOW", self.windowButtonClose)
		async_mainloop(self.root)
		##### tab 구현 E #####
  
		
		

  
		# self.proccessingState = False
		# self.root.update()
  
	def ymlInit(self):
		self.process.ymlInit()
  
	def norInit(self):
		self.nr = self.process.norInit()
  
	def windowButtonClose(self):
		# print("close!!")
		# exit()
		self.root.quit()
		self.root.destroy()
		# try:
		# 	self.root.destroy()
		# except:
		# 	print("close!")		
		# finally:
		# 	self.root.quit()
		# 	self.root.destroy()
		# 	print("finally close")
   
	async def pingTest(self):
		
		await self.process.pingTestCall()

	async def pingTestCall(self):
		print(f'{time.ctime()} call!! ')
		await self.process.pingTestCall()
		print(f'{time.ctime()} close!! ')
		