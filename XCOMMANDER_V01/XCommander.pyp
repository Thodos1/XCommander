# Copyright (c) <2023> <Maksym Vysokolov>
import c4d
from c4d import gui
import os, sys
import random
import json
import shutil

C4D_Version = c4d.GetC4DVersion()
def load_bitmap(path):
	path = os.path.join(os.path.dirname(__file__), path)
	bmp = c4d.bitmaps.BaseBitmap()
	if bmp.InitWith(path)[0] != c4d.IMAGERESULT_OK:
		bmp = None
	return bmp

y_position = 100
PLUGIN_ID = 1060799  # Replace with your unique plugin ID
PLUGIN_NAME = 'XCommander'
PLUGIN_ICON = load_bitmap('res/icons/Icon_logo_XCom.png')
PLUGIN_INFO = 0
PLUGIN_HELP = 'Search and Create Xpresso Nodes'

obj_list = []
all_object_names = []
x_list_data = []

def json_read_k():
	global x_list_data
	# Load the existing data from the JSON file
	with open(json_file_path, 'r') as json_file:
		x_list_data = json.load(json_file)

user_pref_folder = c4d.storage.GeGetC4DPath(c4d.C4D_PATH_STARTUPWRITE)
json_folder = os.path.join(user_pref_folder, "plugins", "XCOMMANDER")
json_file = os.path.join(user_pref_folder, "plugins", "XCOMMANDER", "System_Operators.json")
if not os.path.exists(json_file):
	if C4D_Version < 23000:
		if not os.path.exists(json_folder):
			os.makedirs(json_folder)
	else:

		os.makedirs(json_folder, exist_ok=True)
	#Json with Patterns
	# Get the current directory of the main plugin.py file
	current_directory = os.path.dirname(os.path.abspath(__file__))
	# Construct the path to the JSON file inside the res folder
	json_file_path_or = os.path.join(current_directory, 'res', 'System_Operators.json')
	shutil.copy(json_file_path_or, json_folder)
	#json_file_path
else:
	current_directory = os.path.dirname(os.path.abspath(__file__))
	json_file_path_or = os.path.join(current_directory, 'res', 'System_Operators.json')
	with open(json_file) as f1:
		data1 = json.load(f1)

	# Read the data from the second JSON file
	with open(json_file_path_or) as f2:
		data2 = json.load(f2)

	# Make a copy of the first data set to compare later
	data1_original = data1.copy()

	# Loop through the keys in the second JSON file
	for key, value in data2.items():
		# If the key is not present in the first JSON file, add it
		if key not in data1:
			data1[key] = value
	if data1 != data1_original:
	# Write the updated data back to the first JSON file
		with open(json_file, 'w') as f1:
			json.dump(data1, f1, indent=4)

json_file_path = json_file


def create_xpresso_node(node_name, results_area):
	global y_position
	global obj_list
	global all_object_names

	if obj_list and all_object_names:
		#name_itself = results_area.node_data.get(node_name)
		#print("NAME_ITSELF" + str(name_itself))

		id_obj = all_object_names.index(node_name)
		node_id = obj_list[id_obj]
		if node_id is None:
			#print(f"No node ID found for '{node_name}'")
			return

		node_master = c4d.modules.graphview.GetMaster(0)
		root_m = node_master.GetRoot()
		node = node_master.CreateNode(root_m, c4d.ID_OPERATOR_OBJECT, None,300, y_position)
		node[c4d.GV_OBJECT_OBJECT_ID]= node_id
		y_position += 50

	else:
		values = results_area.node_data.get(node_name)
		if isinstance(values, list):
			node_id = values[0]
		else:
			node_id = values
		if node_id is None:
			#print(f"No node ID found for '{node_name}'")
			return





		#print(f"Creating Xpresso node '{node_name}' with ID {node_id}")

		node_master = c4d.modules.graphview.GetMaster(0)
		root_m = node_master.GetRoot()
		node = node_master.CreateNode(root_m, node_id, None,300, y_position)
		y_position += 50
	c4d.EventAdd()


class CustomGeUserArea(c4d.gui.GeUserArea):
	def __init__(self, parent_dialog):
		super(CustomGeUserArea, self).__init__()

		self.min_width = 370
		self.min_height = 600
		self.results = []
		self.selected_index = -1
		self.previous_selected_index = -1
		self.node_data = x_list_data
		self.SetResults(list(self.node_data.keys()))
		self.double_click_detected = False
		self.parent_dialog = parent_dialog
		# Add scroll count variable
		self.scroll_count = 0

	def GetMinSize(self):
		return self.min_width, self.min_height

	def SetResults(self, results):
		self.results = results
		self.selected_index = 0 if results else -1  # reset selection
		self.previous_selected_index = -1
		self.m_height = len(results)*20
		self.min_height = self.m_height
		self.Redraw()

	def GetSelectedName(self):
		if 0 <= self.selected_index < len(self.results):
			return self.results[self.selected_index]
		return None


	def DrawMsg(self, x1, y1, x2, y2, msg):
		self.DrawSetPen(c4d.GetViewColor(c4d.VIEWCOLOR_C4DBACKGROUND))

		ua_width, ua_height = self.GetMinSize()

		# Get the height of the dialog
		dialog_height = self.GetHeight()

		# Calculate the height of the rectangle
		rectangle_height = max(len(self.results) * 20, dialog_height)

		# Draw a rectangle that fills the entire area
		self.DrawRectangle(0, 0, ua_width, rectangle_height)
		if not self.results:

			# If there are no results, display a specific text
			self.DrawSetTextCol(c4d.Vector(0.6, 0.6, 0.6), c4d.Vector(0.17, 0.17, 0.17))  # white color
			self.DrawSetFont(c4d.FONT_DEFAULT)
			self.DrawText("Start typing: Node name or @ to search objects", 80, 60)  # Display the text "No results" at position (15,20)

			self.DrawText("Did you know, that Shift + Enter/Double-Click does not close XCom? :)", 30,80)  # Display the text "No results" at position (15,20)

			icon_xpr = c4d.bitmaps.BaseBitmap()
			icon_xpr.InitWith(os.path.join(os.path.dirname(__file__), 'res/icons/Logo_ic_empt.png'))





			scale_xpr = c4d.bitmaps.BaseBitmap()
			scale_xpr.Init(256, 256)
			# Scale the original bitmap into the new bitmap
			icon_xpr.ScaleIt(scale_xpr, 256, True, False)

			# Draw the new bitmap
			self.DrawBitmap(icon_xpr,130 , 100, 128, 128, 0, 0, 256, 256, c4d.BMP_NORMAL)


		else:

			self.DrawSetTextCol(c4d.Vector(1, 1, 1), c4d.GetViewColor(c4d.VIEWCOLOR_C4DBACKGROUND))
			self.DrawSetFont(c4d.FONT_DEFAULT)
			for i, result in enumerate(self.results):
				y_pos = i*15
				if i % 2 == 0:
					if i == self.selected_index:
						self.DrawSetTextCol(c4d.Vector(1, 0.5, 0), c4d.Vector(0.15, 0.15, 0.15))  # red color
					else:
						self.DrawSetTextCol(c4d.Vector(0.9, 0.9, 0.9), c4d.Vector(0.15, 0.15, 0.15))  # white color

				else:
					if i == self.selected_index:
						self.DrawSetTextCol(c4d.Vector(1, 0.5, 0), c4d.GetViewColor(c4d.VIEWCOLOR_C4DBACKGROUND))  # red color
					else:
						self.DrawSetTextCol(c4d.Vector(0.9, 0.9, 0.9), c4d.GetViewColor(c4d.VIEWCOLOR_C4DBACKGROUND))  # white color
				# Draw a rectangle around the text
				# Draw a rectangle for every second result, adjusted by 12 pixels
				# Create a new bitmap of the desired size

				if i % 2 == 0:
					self.DrawSetPen(c4d.Vector(0.15, 0.15, 0.15))  # red color
					self.DrawRectangle(0, (i * 20) - 3, 15 + 452, ((i + 1) * 20)-3)  # adjust as needed
				if obj_list:
					#new_bitmap = c4d.bitmaps.BaseBitmap()
					#new_bitmap.Init(65, 65)
					obj_corr_id = all_object_names.index(result)

					obj_ic = obj_list[obj_corr_id].GetIcon()
					if i % 2 == 0:
						self.DrawSetPen(c4d.Vector(0.15, 0.15, 0.15))
					else:
						self.DrawSetPen(c4d.GetViewColor(c4d.VIEWCOLOR_C4DBACKGROUND))


					self.DrawBitmap(obj_ic['bmp'],-1 , i * 20, 18, 18, obj_ic['x'], obj_ic['y'], 64, 64, c4d.BMP_NORMAL | c4d.BMP_ALLOWALPHA)

				else:
					icon_xpr = x_list_data[result][1]

					new_bitmap = c4d.bitmaps.InitResourceBitmap(icon_xpr)



					scale_b = c4d.bitmaps.BaseBitmap()
					scale_b.Init(15, 15)
					# Scale the original bitmap into the new bitmap
					new_bitmap.ScaleIt(scale_b, 256, True, False)
					if i % 2 == 0:
						self.DrawSetPen(c4d.Vector(0.15, 0.15, 0.15))
					else:
						self.DrawSetPen(c4d.GetViewColor(c4d.VIEWCOLOR_C4DBACKGROUND))

					# Draw the new bitmap
					self.DrawBitmap(scale_b,1 , i * 20, 15, 15, 0, 0, 15, 15, c4d.BMP_NORMAL | c4d.BMP_ALLOWALPHA)


				self.DrawText(result, 20, i * 20)

	def Message(self, msg, result):
		if msg.GetId() == c4d.BFM_INPUT:
			device = msg.GetInt32(c4d.BFM_INPUT_DEVICE)
			channel = msg.GetInt32(c4d.BFM_INPUT_CHANNEL)
			double_click = msg.GetBool(c4d.BFM_INPUT_DOUBLECLICK)

			if device == c4d.BFM_INPUT_MOUSE and channel == c4d.BFM_INPUT_MOUSELEFT and double_click:
				self.double_click_detected = True

		return c4d.gui.GeUserArea.Message(self, msg, result)



	def InputEvent(self, bc):
		# only handle left mouse button
		global obj_list
		global all_object_names
		global y_position
		if bc[c4d.BFM_INPUT_CHANNEL] == c4d.BFM_INPUT_MOUSELEFT:
			if bc[c4d.BFM_INPUT_VALUE] == 1:
				mx = bc[c4d.BFM_INPUT_X]
				my = bc[c4d.BFM_INPUT_Y] - 12

				# calculate the selected index based on the mouse y position and the height of each item
				selected_index = (my - 15) // 20  # assume each result has a height of 15 pixels

				# check if selected index is valid
				if 0 <= selected_index < len(self.results):
					self.selected_index = int(selected_index)


					if self.double_click_detected:

						#node_name = self.selected_index
						node_name = self.GetSelectedName()

						#print(f"DOUBLE_CLICK on result: {self.results[self.selected_index]}")
						create_xpresso_node(node_name, self)  # create the Xpresso node when double clicked
						self.double_click_detected = False
						if bc[c4d.BFM_INPUT_QUALIFIER] != c4d.QUALIFIER_SHIFT:

							obj_list = []
							all_object_names = []

							y_position = 100
							self.parent_dialog.Close()





					self.Redraw()



		return True


# def Sized(self, w, h):
# self.SetSize(self.min_width, self.min_height)

class XpressoCommanderDialog(gui.GeDialog):
	IDC_SEARCH = 1000
	IDC_NODE_LIST = 1001
	IDC_RESULTS_AREA = 1002

	def __init__(self):

		return None


	def MinSize(self):
		return 400, 300
	def MaxSize(self):
		return 400, 300

	def update_node_list(self, search_text):
		global obj_list
		global all_object_names
		#print(f'update_node_list called with search_text = {search_text}')
		if search_text == "":
			obj_list = []
			all_object_names = []
			self.results_area.SetResults([])
		elif search_text.startswith('@'):
			# Get all object names in the document and update the node list
			all_object_names = self.get_all_object_names()
			filter_text = search_text[1:].strip()  # remove the '@' and strip leading/trailing whitespace
			if filter_text:  # if there is any text after '@'
				all_object_names = [name for name in all_object_names if filter_text.lower() in name.lower()]
			self.results_area.SetResults(all_object_names)


		else:
			obj_list = []
			all_object_names = []

			search_results = [name for name in self.results_area.node_data.keys() if search_text.lower() in name.lower()]
			search_results = sorted(search_results, key=lambda x: (not x.lower().startswith(search_text.lower()), x))
			self.results_area.SetResults(search_results)  # this will update self.min_height in CustomGeUserArea
		self.LayoutChanged(self.IDC_RESULTS_AREA)

	def get_all_object_names(self):
		global all_object_names
		doc = c4d.documents.GetActiveDocument()
		all_objects = doc.GetObjects()

		if obj_list != all_objects:
			for obj in all_objects:
				all_object_names.append(f"{obj.GetName()} | {obj.GetTypeName()}")
				obj_list.append(obj)


			return all_object_names
		else:
			return all_object_names



	def resize_dialog(self, width, height):
		bc = c4d.BaseContainer()
		bc.SetInt32(c4d.BFM_SETDIALOG_WIDTH, width)
		bc.SetInt32(c4d.BFM_SETDIALOG_HEIGHT, height)
		self.SendMessage(c4d.BFM_SETDIALOG, bc)

	def CreateLayout(self):
		self.SetTitle("Xpresso Commander")
		self.GroupBegin(id=1005454, flags=c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1, rows=2)
		self.AddEditText(self.IDC_SEARCH, c4d.BFH_SCALEFIT,0, 15, c4d.EDITTEXT_ENABLECLEARBUTTON | c4d.EDITTEXT_CURSORUPDOWNBUTTONS)
		self.SetString(self.IDC_SEARCH, "At least someone did it...", True, c4d.EDITTEXT_HELPTEXT)
		self.ScrollGroupBegin(5634698, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, c4d.SCROLLGROUP_VERT)
		self.GroupBegin(4952349, c4d.BFH_LEFT | c4d.BFV_TOP, 0, 0)
		self.results_area = CustomGeUserArea(self)
		self.AddUserArea(self.IDC_RESULTS_AREA, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT)
		self.AttachUserArea(self.results_area, self.IDC_RESULTS_AREA)
		self.GroupEnd()

		self.GroupEnd()
		self.update_node_list('')
		return True

	def selected_node_changed(self):
		selected_index = self.node_list_area.selected_index
		if 0 <= selected_index < len(self.node_list_area.items):
			self.CreateSelectedNode(selected_index)

	def Command(self, id, msg):
		if id == self.IDC_SEARCH:

			if msg.GetBool(c4d.BFM_ACTION_KEYDOWN):
				self.results_area.previous_selected_index = self.results_area.selected_index
				self.results_area.selected_index += 1
				if self.results_area.selected_index >= len(self.results_area.results):
					self.results_area.selected_index = 0
				self.results_area.Redraw()
			elif msg.GetBool(c4d.BFM_ACTION_KEYUP):
				self.results_area.previous_selected_index = self.results_area.selected_index
				self.results_area.selected_index -= 1
				if self.results_area.selected_index < 0:
					self.results_area.selected_index = len(self.results_area.results) - 1
				self.results_area.Redraw()

			else:
				search_text = self.GetString(self.IDC_SEARCH)

				self.update_node_list(search_text)
			return True


		# elif id == self.IDC_NODE_LIST:
		# selected_line = self.GetMultiLineEditTextCursor(self.IDC_NODE_LIST, c4d.MULTILINE_CURSORLINE)
		# selected_text = self.get_node_name_by_line(selected_line)
		# if selected_text:
		# self.create_xpresso_node(selected_text)
		# self.Close()
		# return True

		return c4d.gui.GeDialog.Command(self, id, msg)

	def get_node_name_by_line(self, line):
		node_names = self.GetMultiLineEditTextString(self.IDC_NODE_LIST).split("\n")
		if 0 <= line < len(node_names):
			return node_names[line].strip()
		return None

	def PopulateNodeList(self, search_string):
		# node_data = {
		# 'math': c4d.ID_OPERATOR_MATH,
		# 'range_mapper': c4d.ID_OPERATOR_RANGEMAPPER,
		# 'result': c4d.ID_OPERATOR_RESULT
		# }

		self.node_list_area.items.clear()
		self.node_list_area.items = [name for name in node_data.keys() if search_string in name]
		self.node_list_area.selected_index = -1
		self.node_list_area.Redraw()



	def Message(self, msg, result):
		global obj_list
		global all_object_names
		global y_position
		if msg.GetId() == c4d.BFM_LOSTFOCUS:


			obj_list = []
			all_object_names = []
			y_position = 100
			self.Close()
		if msg.GetId() == c4d.BFM_INTERACTSTART:
			bc = c4d.BaseContainer()

			if c4d.gui.GetInputState(c4d.BFM_INPUT_KEYBOARD, c4d.KEY_ENTER, bc):
				if bc[c4d.BFM_INPUT_VALUE] == 1:


					node_name = self.results_area.GetSelectedName()
					#print(node_name)
					if node_name is not None:
						create_xpresso_node(node_name, self.results_area)
					if bc[c4d.BFM_INPUT_QUALIFIER] != c4d.QUALIFIER_SHIFT:
						obj_list = []
						all_object_names = []
						y_position = 100
						self.Close()

					return True

		return gui.GeDialog.Message(self, msg, result)

class XCom_pl(c4d.plugins.CommandData):
	dialog = None

	def Execute(self, doc):
		# create the dialog
		if self.dialog is None:


			json_read_k()
			self.dlg = XpressoCommanderDialog()
		return self.dlg.Open(dlgtype=c4d.DLG_TYPE_ASYNC_POPUP_RESIZEABLE, pluginid=PLUGIN_ID, xpos=-1, ypos=-1, defaultw=400,
			 defaulth=300)


if __name__ == "__main__":
	exec_plug = c4d.plugins.RegisterCommandPlugin(PLUGIN_ID, PLUGIN_NAME, PLUGIN_INFO, PLUGIN_ICON, PLUGIN_HELP,
												  XCom_pl())
	if (exec_plug):
		print("XCOMMANDER registered successfully")

