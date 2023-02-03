import paramiko, time, ftplib, collections
from paramiko.ssh_exception import AuthenticationException
from operator import eq, ne

class ProcessLab():
	def __init__(self) -> None:
		# self.ftpServer = "123.215.15.155"
		# self.ftpUser = "lab"
		# self.ftpPw = "CD8F4893A77F7549075DB79EC7029F73" ## icloud&aristaswitch!2#  / CD8F4893A77F7549075DB79EC7029F73
		# self.ftpDefaultDir = "/labos"
		self.ftpServer = "192.168.1.114"
		self.ftpUser = "ftpuser"
		self.ftpPw = "rkqtn!23" ## icloud&aristaswitch!2#  / CD8F4893A77F7549075DB79EC7029F73
		self.ftpDefaultDir = ""
  
	def getLabOsList(self, vendor):
		
		try:
			ftp = ftplib.FTP()
			ftp.encoding = 'utf-8'
			ftp.timeout = 3

			ftp.connect(self.ftpServer)
			ftp.login(self.ftpUser, self.ftpPw)
			ftp.cwd(f"{self.ftpDefaultDir}/{vendor}")
			osList = ftp.nlst()
			osList.sort(reverse=True)
			result = 1
		except TimeoutError as e:
			osList = []
			result = 0

		return osList, result
  
  
	def sshConnect(self, host, user, pw, port):
   
		try:
			client = paramiko.SSHClient()
			client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

			client.connect(hostname=host, port=port, username=user, password=pw, timeout=3)
			# print(client)
			# client.close()
		except AuthenticationException:
			print("id/pw warng")
			client = None
		except TimeoutError:
			print("timeout ")
			client = None
   
		return client

	def sshConnectTest(self, host, user, pw, port):
		
		client = self.sshConnect(host, user, pw, port)
		if client:
			print("connectTest seccess")	
			client.close()
		else:
			print("connectTest failed")

	def sendCmd(self, cmd):
		print(f"************************  {cmd[1]}")
		self.invoke.send(cmd[0])
		out, err = self.waitStream(self.invoke) 

		err = err.strip().decode('utf-8')
		out = out.strip().decode('utf-8')
  
		return out, err

	def waitStream(self, chan):
		time.sleep(1)
		out = err = b''

		while chan.recv_ready():
			out += chan.recv(1000)
			while chan.recv_stderr_ready():
				err += chan.recv_stderr(1000)

		return out, err
   
	def labOSAppend(self, vendor, osVersion, host, user, pw, port):

		cmdMkDir = [f"mkdir -p /opt/unetlab/addons/qemu/{osVersion}\n", f"{osVersion} 폴더 생성"]
		cmdFtp = [f"ftp {self.ftpServer}\n", "ftp 접속"]
		cmdId = [f"{self.ftpUser}\n", "id 입력"]
		cmdPw = [f"{self.ftpPw}\n", "pw 입력"] 
		cmdLabDown = [f"get {vendor}/{osVersion}.qcow2 /opt/unetlab/addons/qemu/{osVersion}/hda.qcow2\n", f"{osVersion} 다운로드"]
		cmdExit = ["exit\n", "ftp close"]
		cmdPermission = ["/opt/unetlab/wrappers/unl_wrapper -a fixpermissions\n", "퍼미션"]

		cmds = [cmdMkDir, cmdFtp, cmdId, cmdPw, cmdLabDown, cmdExit, cmdPermission]

		# print(cmdMkDir)
		# try:
		client = self.sshConnect(host, user, pw, port)
		
		if not client:
			return -1, "Lab Server 접속이 실패하였습니다."
	
		self.invoke = client.invoke_shell()

		errResult = ""
		for cmd in cmds:
			out, err = self.sendCmd(cmd)
   
			if ne(err, ""):
				errResult = f"{cmd[1]} 실패, {err}"
				print(errResult)
				break
			elif "unreachable" in out.lower():
				errResult = "Lab OS 파일서버에 접속 실패했습니다."
				print(errResult)
				break
			elif "invalid command" in out.lower():
				errResult = f"{cmd[1]} 실패, 잘못된 cmd"
				print(errResult)
				break
			else:
				print(f"************************  {cmd[1]} 성공")
				# print(out)
		
  
		if ne(errResult, ""):
			return -2, errResult
  
		return 1, ""
    
		# except Exception as e:
		# 	print(e)
		# finally:
		# 	if client:
		# 		client.close()

	

  