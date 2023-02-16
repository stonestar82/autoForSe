#-*- coding:utf-8 -*-
from http.server import BaseHTTPRequestHandler
import os, json
from operator import eq
from jinja2 import Template
from urllib.parse import parse_qs

class ProcessWeb(BaseHTTPRequestHandler):



	def do_POST(self):
		self.directory = f"./pm/report"
		
		

		contentLength = int(self.headers['Content-Length']) # <--- Gets the size of data
		postData = self.rfile.read(contentLength).decode("utf-8") # <--- Gets the data itself
		print(parse_qs(postData))
		types = parse_qs(postData)["types"][0]
		val = parse_qs(postData)["val"][0]
		d = parse_qs(postData)["d"][0]
		host = parse_qs(postData)["host"][0]

		if eq("host", types):
			path = f"{self.directory}/{val}/show"
		elif eq("showtechList", types):
			path = f"{self.directory}/{d}/show/{val}"
		elif eq("showtech", types):
			path = f"{self.directory}/{d}/show/{host}/{val}"
		elif eq("showtechResult", types):
			path = f"{self.directory}/{d}/data/{host}-data.json"
			


		if eq("host", types) or eq("showtechList", types) or eq("showtechResult", types):
			
			if eq("showtechResult", types):
				
				with open(path, encoding="utf-8") as r:
					result = json.load(r)
				r.close()
    
				
    
				for d in result:
					result[d] = str(result[d]).replace("/\n/g", "\\n")
     
				data = { "data" : result}
    
				jsonTemplate = """
				{"data" : 
					[
					{%-for d in data -%}
					"{{ d }}" : "{{ data[d] }}"
						{%-if loop.index < loop.length-%}
						,
						{%-endif-%}
					{%-endfor-%}
					]
				}
				"""

			else:
				dirs = os.listdir(path)
				data = {"dirs": dirs}

				jsonTemplate = """
				{"data" : 
					[
					{%-for dir in dirs -%}
					"{{ dir }}"
						{%-if loop.index < loop.length-%}
						,
						{%-endif-%}
					{%-endfor-%}
					]
				}
				"""
			
			
			template = Template(jsonTemplate)
			body = template.render(**data)

			self.send_response(200)
			self.send_header('Content-type', 'application/json')
			self.end_headers()

		else:
			self.send_response(200)
			self.send_header('Content-type', 'text/plain')
			self.end_headers()
			with open(path, encoding="utf-8") as r:
				body = r.read()
			r.close()

		# print(body)
		self.wfile.write(bytes(body, encoding='utf-8'))

	def do_GET(self):
		self.directory = f"./pm/report"
		
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()

		self.directory = f"./pm/report/"
		dirs = os.listdir(self.directory)
		data = {"dirs": dirs}

		# response(응답)할 body내용이다.
		body = """
		<!DOCTYPE html>
		<html>
		<head><title>python</title></head>
		<style>
		.parent{
				width: 100%;
				margin: 10px auto;
				display: flex;
		}

		.first {
				border: 1px solid red;
				flex:1;
				width:70%;
				box-sizing: border-box;
		}

		.second{
				border: 1px solid green;
				flex:1;
				margin: 0px 5%;
				width:30%;
				box-sizing: border-box;
		}
		</style>
		<body>
		<div>
		<select name="dir" id="dir" onchange="getHosts(this.value)">
			<option value="">------------------</option>
		{%-for dir in dirs -%}
			<option value="{{ dir }}">{{ dir }}</option>
		{%-endfor-%}
		</select>
		<select name="host_name" id="host_name" onchange="getShowtechList(this.value);getShowtechResult(this.value)">
			<option value="">------------------</option>
		</select>
		<select name="showtech" id="showtech" onchange="getShowtech(this.value)">
			<option value="">------------------</option>
		</select>
		</div>
		<div id="view" class="parent">
			<div class="first"><textarea id="show_tech_view" readonly="true" width="100%"></textarea></div>
			<div id="etc_view" class="second">etc_view</div>
		</div>
		<script src="http://code.jquery.com/jquery-3.6.3.min.js" integrity="sha256-pvPw+upLPUjgMXY0G+8O0xUf+/Im1MZjXxxgOcBQBXU=" crossorigin="anonymous"></script>
		<script type="text/javascript">
		function getHosts(d) {
			if (d != ""){
				$.post("http://localhost",{ types: "host", val: d, d: "empty", host: "empty" })
						.done(
									function(data){
										hosts = data.data
										$("#host_name option[value!='']").remove();
										$("#showtech option[value!='']").remove();
										for (var i = 0; i < hosts.length; i++) {
											var option = $("<option value=\\""+hosts[i]+"\\">"+hosts[i]+"</option>");
											$('#host_name').append(option);
										}

								});
			}
		}
  
		function getShowtechList(host) {
			if (host != ""){
				$.post("http://localhost",{ types: "showtechList", val: host, d: $("#dir option:selected").val(), host: host })
						.done(
									function(data){
										showtech = data.data
										$("#showtech option[value!='']").remove();
										for (var i = 0; i < showtech.length; i++) {
											var option = $("<option value=\\""+showtech[i]+"\\">"+showtech[i]+"</option>");
											$('#showtech').append(option);
										}

								});
			}
		}
		function getShowtech(showtech) {
			if (showtech != ""){
				$.post("http://localhost",{ types: "showtech", val: showtech, d: $("#dir option:selected").val(), host: $("#host_name option:selected").val() })
						.done(
									function(data){
										$("#show_tech_view").html(data)
								});
			}
		}

		var hostResult = ""
		function getShowtechResult(host) {
			if (host != ""){
				$.post("http://localhost",{ types: "showtechResult", val: host, d: $("#dir option:selected").val(), host: host })
						.done(
									function(data){
										alert(data.data)
										hostResult = data.data
										console.log(hostResult)
								});
			}
		}
		</script>
		</body>
		</html>
		""";

		template = Template(body)
		body = template.render(**data)
  
		self.wfile.write(bytes(body, encoding='utf-8'))


