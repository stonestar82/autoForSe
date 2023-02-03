from operator import ne, eq
from src.ProcessAuto import ProcessAuto

class Menu():
	def __init__(self, process):
		self.process = process
		self.menuSelected = True
		self.selectMenu = 0
  
	def tabMenu(self):
		print("==========================================")
		print("1. 상태체크")
		print("2. IP v4 config")
		print("3. IP v6 config")
		print("4. 토폴로지 생성")
		print("5. 백업 및 초기화")
		print("0. 종료")
  

		
		self.selectedMenuCheck()
  
		if eq(1, self.selectMenu):
			pass
		elif eq(2, self.selectMenu):
			pass
		elif eq(3, self.selectMenu):
			pass
		elif eq(4, self.selectMenu):
			self.topologyCreateCall()
		elif eq(5, self.selectMenu):
			pass
		elif eq(0, self.selectMenu):
			self.menuExit()
		else:
			self.printMenuRightSelect()
			self.tabMenu()

	def printMenuRightSelect(self):
		print("\n\n정확한 메뉴번호를 입력해 주세요\n\n")
  
	def ipv4Menu(self):
		print("==========================================")
		print("1. init cfg 생성")
		print("2. base cfg 생성")
		print("3. loop0 cfg 생성")
		print("0. 상위 메뉴")

		self.selectedMenuCheck()
  
		if eq(1, self.selectMenu):
			pass
		elif eq(2, self.selectMenu):
			pass
		elif eq(3, self.selectMenu):
			pass
		elif eq(0, self.selectMenu):
			self.menuExit()
		else:
			self.printMenuRightSelect()
			self.tabMenu()


	def menuExit(self):
		exit()
  
	def topologyCreateCall(self):
		self.process.createTopology()
		print("\n\n토폴로지 파일이 생성되었습니다.\n\n")
		self.tabMenu()
  
  
	def selectedMenuCheck(self):
		self.menuSelected = True

		while self.menuSelected:
			try:
				self.selectMenu = int(input("\n\n번호를 입력해주세요 : "))
				self.menuSelected = False
			except ValueError:
				print("\n\n메뉴의 번호를 정확히 입력해 주세요.\n\n") 