#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ADVANCED SHIfT — Issue 002
# Cinema 4D Xpresso Commander
#
# Copyright (c) 2026 Maksym Vysokolov
#
# Author:    Maksym Vysokolov
# Website:   https://cataclysm-vfx.com
# Instagram: https://instagram.com/thodos998
#
# Free to use, modify, and redistribute under the MIT License.
# If you find this useful, consider following my work!
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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

PLUGIN_ID = 1060799
PLUGIN_NAME = 'XCommander V.1.0.0'
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
		# Update shipped definitions, retaining custom-only entries
		if data1.get(key) != value:
			data1[key] = value
	if data1 != data1_original:
	# Write the updated data back to the first JSON file
		with open(json_file, 'w') as f1:
			json.dump(data1, f1, indent=4)

json_file_path = json_file


PYTHON_ID = 1022471

class XPoolRestoreError(RuntimeError):
    pass

def _decode(data,c4d):
    if data is None or isinstance(data,(bool,int,float,str)):
        return data
    if isinstance(data,dict):
        typ=data.get('type')
        if typ=='BaseContainer':
            bc=c4d.BaseContainer()
            for row in data['entries']:
                bc[int(row['id'])]=_decode(row['value'],c4d)
            return bc
        if typ=='Vector':
            return c4d.Vector(float(data['x']),float(data['y']),float(data['z']))
        if typ=='BaseTime':
            return c4d.BaseTime(float(data['seconds']))
    raise XPoolRestoreError('Unsupported serialized value: '+repr(data)[:100])


def _remap_defaults(container_spec,by_main):
    """Rekey nested per-port defaults from captured sub IDs to live sub IDs.
    Doesn't touch top-level parameter IDs or Python script/source.
    """
    spec=json.loads(json.dumps(container_spec))
    for row in spec.get('entries',[]):
        main=int(row['id']); m=by_main.get(main,{})
        nested=row['value']
        if not m or not isinstance(nested,dict) or nested.get('type')!='BaseContainer':
            continue
        out={}
        for item in nested['entries']:
            dest=m.get(int(item['id']),int(item['id']))
            if dest in out:
                raise XPoolRestoreError('Conflicting sub IDs at port group %d: %d'%(main,dest))
            out[dest]={**item,'id':dest}
        nested['entries']=list(out.values())
    return spec


def _restore_python(node,snapshot,*,verify=True):
    if snapshot.get('operator_id')!=PYTHON_ID or node.GetOperatorID()!=PYTHON_ID:
        raise XPoolRestoreError('Wrong operator type for Python preset')
    warnings=[]
    for p in list(node.GetInPorts())+list(node.GetOutPorts()):
        node.RemovePort(p,False)
    # Interleave IO by original sub ID to approximate the allocator's order.
    specified=[]
    for io,key in ((c4d.GV_PORT_INPUT,'inputs'),(c4d.GV_PORT_OUTPUT,'outputs')):
        for item in snapshot['ports'][key]:
            specified.append((int(item['sub_id']),io,item))
    specified.sort(key=lambda t:(t[0],t[1]))
    mapping={};created=[]
    for old_sid,io,p in specified:
        main=int(p['main_id']);typ=int(p['type_id'])
        did=c4d.DescID(c4d.DescLevel(main,typ,PYTHON_ID))
        flag=c4d.GV_PORT_FLAG_IS_VISIBLE if p.get('visible',True) else c4d.GV_PORT_FLAG_NONE
        port=node.AddPort(io,did,flag,False)
        if port is None:
            raise XPoolRestoreError('Could not create port '+p['name'])
        port.SetName(p['name'])
        port.SetVisible(bool(p.get('visible',True)))
        mapping.setdefault(main,{})[old_sid]=int(port.GetSubID())
        created.append((port,p))
        if int(port.GetValueType())!=typ:
            raise XPoolRestoreError('Port %s type differs: %s instead of %s'%(p['name'],port.GetValueType(),typ))
    converted=_remap_defaults(snapshot['operator_container'],mapping)
    node.SetOperatorContainer(_decode(converted,c4d))
    node.SetName(snapshot['name'])
    if verify:
        code=node.GetOperatorContainer().GetString(400)
        if code!=snapshot['python_source']:
            raise XPoolRestoreError('Python source not restored')
        for port,p in created:
            if port.GetName(node)!=p['name']:
                raise XPoolRestoreError('Wrong port name: '+p['name'])
    if 'xrange(' in snapshot['python_source']:
        warnings.append('Legacy Python 2 xrange() in original preset; code copied unchanged')
    return warnings


def restore_entry_preset(node, metadata):
    if metadata.get('kind') != 'python_preset':
        raise XPoolRestoreError('Unsupported preset kind')
    snapshot = metadata['snapshot']
    for item in metadata.get('user_data', []):
        if item['type'] != 'bool':
            raise XPoolRestoreError('Unsupported preset user-data type')
        desc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BOOL)
        desc[c4d.DESC_NAME] = item['name']
        desc[c4d.DESC_DEFAULT] = bool(item['default'])
        did = node.AddUserData(desc)
        if did is None or did[1].id != item['id']:
            raise XPoolRestoreError('Preset user-data ID mismatch')
        node[did] = bool(item['default'])
    _restore_python(node, snapshot)


def get_graphdata(node):
	bc = node.GetDataInstance()
	if bc is None:
		return None
	bc = bc.GetContainerInstance(1001)
	if bc is None:
		return None
	return bc.GetContainerInstance(1000)


def iter_xpresso_nodes(master):
	root = master.GetRoot() if master is not None else None
	if root is None:
		return
	pending = list(reversed(root.GetChildren()))
	while pending:
		node = pending.pop()
		yield node
		pending.extend(reversed(node.GetChildren()))


def xpresso_node_type(node, node_data):
	operator_id = node.GetOperatorID()
	for name, values in node_data.items():
		if (values[0] if isinstance(values, list) else values) == operator_id:
			return name
	return node.GetTypeName() or str(operator_id)


def xpresso_reference_name(node):
	if node.GetOperatorID() != c4d.ID_OPERATOR_OBJECT:
		return None
	reference = node[c4d.GV_OBJECT_OBJECT_ID]
	return reference.GetName() if reference is not None else "<unassigned>"


def focus_xpresso_node(node):
	graphview = c4d.modules.graphview
	master = graphview.GetMaster(0)
	if master is None:
		return False
	# Validate against the active graph, including deleted/stale search results
	if not any(candidate == node for candidate in iter_xpresso_nodes(master)):
		return False
	root = master.GetRoot()
	views = []
	target = node
	while target != root:
		parent = target.GetUp()
		if parent is None:
			return False
		node_data = get_graphdata(target)
		view_data = get_graphdata(parent)
		if node_data is None or view_data is None:
			return False
		views.append((view_data,
			-(node_data.GetFloat(100) + node_data.GetFloat(108) * 0.5),
			-(node_data.GetFloat(101) + node_data.GetFloat(109) * 0.5)))
		target = parent
	for view_data, pan_x, pan_y in views:
		view_data.SetFloat(102, pan_x)
		view_data.SetFloat(103, pan_y)
		view_data.SetFloat(104, 1.0)
	graphview.RedrawMaster(master)
	c4d.EventAdd()
	return True


def create_centered_xpresso_node(node_id, reference=None, offset_y=0.0, preset=None):
	graphview = c4d.modules.graphview
	master = graphview.GetMaster(0)
	if master is None:
		return None
	root = master.GetRoot()
	if root is None:
		return None
	root_data = get_graphdata(root)
	if root_data is None:
		print("XCOMMANDER: Cannot read root graph data.")
		return None

	pan_x = root_data.GetFloat(102)
	pan_y = root_data.GetFloat(103)
	master.AddUndo()

	node = master.CreateNode(root, node_id, None, 300, 100)
	if node is None:
		return None
	if reference is not None:
		node[c4d.GV_OBJECT_OBJECT_ID] = reference
	if preset is not None:
		try:
			restore_entry_preset(node, preset)
		except Exception as exc:
			node.Remove()
			graphview.RedrawMaster(master)
			c4d.EventAdd()
			gui.MessageDialog("XCommander could not restore the preset:\n" + str(exc))
			return None

	node_data = get_graphdata(node)
	if node_data is None:
		node.Remove()
		graphview.RedrawMaster(master)
		c4d.EventAdd()
		print("XCOMMANDER: Cannot read node graph data.")
		return None

	# Stored graph coordinates: center the whole node using its dimensions
	node_data.SetFloat(100, -pan_x - node_data.GetFloat(108) * 0.5)
	node_data.SetFloat(101, -pan_y - node_data.GetFloat(109) * 0.5 + offset_y)
	graphview.RedrawMaster(master)
	c4d.EventAdd()
	return node


def create_xpresso_node(node_name, results_area):
	index = results_area.selected_index
	if not 0 <= index < len(results_area.rows):
		return False
	row = results_area.rows[index]
	if row.existing_node is not None:
		return focus_xpresso_node(row.existing_node)
	dialog = results_area.parent_dialog
	# Activate the selected row's payload, independent of transient search globals
	if row.scene_object is not None:
		node = create_centered_xpresso_node(
			c4d.ID_OPERATOR_OBJECT, row.scene_object, dialog.node_offset_y
		)
	else:
		values = results_area.node_data.get(row.name)
		node_id = values[0] if isinstance(values, list) else values
		if node_id is None:
			return False
		preset = values[2] if isinstance(values, list) and len(values) > 2 else None
		if preset is not None and preset.get('kind') == 'unavailable':
			gui.MessageDialog(preset['reason'])
			return False
		node = create_centered_xpresso_node(
			node_id, offset_y=dialog.node_offset_y, preset=preset
		)
	if node is None:
		return False
	dialog.node_offset_y += 50.0
	return True


class ResultTreeRow:
	def __init__(self, index, name, scene_object=None, existing_node=None, node_type=""):
		self.existing_node = existing_node
		self.scene_object = scene_object
		self.name = name
		self.suffix = ""

		if existing_node is not None:
			reference_name = xpresso_reference_name(existing_node)
			if reference_name is not None:
				self.suffix = " | ref: " + reference_name
			self.suffix += " | type: " + node_type
		elif isinstance(scene_object, c4d.BaseTag):
			owner = scene_object.GetObject()
			self.suffix = " | parent: " + (
				owner.GetName() if owner is not None else ""
			)
		elif scene_object is not None:
			self.name = scene_object.GetName()
			self.suffix = " | type: " + scene_object.GetTypeName()

		self.index = index
		self.next = None
		self.pred = None


class ResultsTreeFunctions(gui.TreeViewFunctions):
	def GetFirst(self, root, userdata):
		return root.rows[0] if root.rows else root.empty_row

	def GetNext(self, root, userdata, obj):
		return obj.next

	def GetPred(self, root, userdata, obj):
		return obj.pred

	def GetDown(self, root, userdata, obj):
		return None

	def GetId(self, root, userdata, obj):
		return id(obj)

	def GetName(self, root, userdata, obj):
		return obj.name

	def IsOpened(self, root, userdata, obj):
		return False

	def IsSelectable(self, root, userdata, obj):
		return obj.index >= 0

	def IsSelected(self, root, userdata, obj):
		return obj.index >= 0 and obj.index == root.selected_index

	def Select(self, root, userdata, obj, mode):
		if obj.index >= 0 and mode != c4d.SELECTION_SUB:
			root.previous_selected_index = root.selected_index
			root.selected_index = obj.index

	def GetBackgroundColor(self, root, userdata, obj, line, col):
		# An empty-state row must blend into the unused TreeView area
		if obj.index < 0 or obj.index % 2:
			return c4d.COLOR_BG
		return c4d.Vector(0.15)

	def GetDragType(self, root, userdata, obj):
		return c4d.DRAGTYPE_ATOMARRAY if obj.scene_object is not None else c4d.NOTOK

	def DragStart(self, root, userdata, obj):
		if obj.scene_object is None:
			return 0
		root.selected_index = obj.index
		return c4d.TREEVIEW_DRAGSTART_ALLOW | c4d.TREEVIEW_DRAGSTART_SELECT

	def GenerateDragArray(self, root, userdata, obj):
		if obj.scene_object is None:
			return []

		root.parent_dialog.keep_open_after_drag = True
		return [obj.scene_object]

	def FinishInput(self, root, userdata, data):
		# Release drag-only focus protection after native input has unwound
		if root.parent_dialog.keep_open_after_drag and root.parent_dialog.IsOpen():
			root.parent_dialog.SetTimer(50)

	def GetLineHeight(self, root, userdata, obj, col, area):
		return 230 if obj.index < 0 else max(20, area.DrawGetFontHeight() + 4)

	def GetColumnWidth(self, root, userdata, obj, col, area):
		return 370 if obj.index < 0 else area.DrawGetTextWidth(obj.name + obj.suffix) + 28

	def DrawCell(self, root, userdata, obj, col, drawinfo, bgcolor):
		area = drawinfo['frame']
		x, y = drawinfo['xpos'], drawinfo['ypos']
		w, h = drawinfo['width'], drawinfo['height']
		area.DrawSetPen(bgcolor)
		area.DrawRectangle(x, y, x + w - 1, y + h - 1)
		area.DrawSetFont(c4d.FONT_DEFAULT)
		if obj.index < 0:
			area.DrawSetTextCol(c4d.Vector(0.6), bgcolor)
			area.DrawText('Search: nodes, @ objects, # tags, $ existing nodes', x + 8, y + 20)
			area.DrawText('Shift + Enter/Double-Click keeps XCom open', x + 8, y + 40)
			return None
		icon = None
		if obj.existing_node is not None:
			icon = obj.existing_node.GetIcon()
		elif obj.scene_object is not None:
			icon = obj.scene_object.GetIcon()
		else:
			values = root.node_data.get(obj.name)
			if isinstance(values, list) and len(values) > 1:
				icon = gui.GetIcon(values[1])
		if icon and icon.get('bmp') is not None:
			area.DrawBitmap(icon['bmp'], x + 2, y + (h - 18) // 2, 18, 18,
				icon['x'], icon['y'], icon['w'], icon['h'],
				c4d.BMP_NORMAL | c4d.BMP_ALLOWALPHA)
		text_color = c4d.Vector(1, 0.5, 0) if self.IsSelected(root, userdata, obj) else c4d.Vector(0.9)
		area.DrawSetTextCol(text_color, bgcolor)
		text_y = y + (h - area.DrawGetFontHeight()) // 2
		area.DrawText(obj.name, x + 24, text_y)
		if obj.suffix:
			area.DrawSetTextCol(c4d.Vector(0.6), bgcolor)
			area.DrawText(obj.suffix, x + 24 + area.DrawGetTextWidth(obj.name), text_y)
		return None

	def DoubleClick(self, root, userdata, obj, col, mouseinfo):
		if obj.index < 0 or mouseinfo['button'] != c4d.MOUSEINFO_BUTTON_LEFT:
			return False
		root.selected_index = obj.index
		# Finish the native TreeView callback before closing its host dialog
		root.pending_double_click = (obj.name,
			mouseinfo['inputmsg'].GetInt32(c4d.BFM_INPUT_QUALIFIER))
		root.parent_dialog.SetTimer(1)
		return True


class ResultsTree:
	def __init__(self, parent_dialog, tree):
		self.parent_dialog = parent_dialog
		self.tree = tree
		self.existing_node_search = False
		self.results = []
		self.rows = []
		self.empty_row = ResultTreeRow(-1, '')
		self.selected_index = -1
		self.previous_selected_index = -1
		self.node_data = x_list_data
		self.pending_double_click = None
		self.functions = ResultsTreeFunctions()
		self.tree.SetRoot(self, self.functions, None)

	def SetResults(self, results, existing_nodes=None):
		self.existing_node_search = existing_nodes is not None
		self.results = list(results)
		# Retain the previous rows until the native view has refreshed
		old_rows = self.rows
		if existing_nodes is not None:
			self.rows = [ResultTreeRow(i, name, existing_node=node,
				node_type=xpresso_node_type(node, self.node_data))
				for i, (name, node) in enumerate(zip(self.results, existing_nodes))]
		else:
			self.rows = [ResultTreeRow(i, name, obj_list[i] if i < len(obj_list) else None)
				for i, name in enumerate(self.results)]
		for i, row in enumerate(self.rows):
			row.pred = self.rows[i - 1] if i else None
			row.next = self.rows[i + 1] if i + 1 < len(self.rows) else None
		self.selected_index = 0 if self.results else -1
		self.previous_selected_index = -1
		self.Redraw()

	def GetSelectedName(self):
		if 0 <= self.selected_index < len(self.results):
			return self.results[self.selected_index]
		return None

	def Redraw(self):
		if not self.parent_dialog.IsOpen():
			return
		self.tree.Refresh()
		if self.parent_dialog.IsOpen() and 0 <= self.selected_index < len(self.rows):
			self.tree.MakeVisible(self.rows[self.selected_index])


class XpressoCommanderDialog(gui.GeDialog):
	IDC_SEARCH = 1000
	IDC_NODE_LIST = 1001
	IDC_RESULTS_AREA = 1002

	def __init__(self):
		self.keep_open_after_drag = False
		self.node_offset_y = 0.0


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
		elif search_text.startswith('$'):
			obj_list = []
			all_object_names = []
			filter_text = search_text[1:].strip().casefold()
			master = c4d.modules.graphview.GetMaster(0)
			nodes = [node for node in iter_xpresso_nodes(master)
				if not filter_text or filter_text in (node.GetName() + ' ' +
					xpresso_node_type(node, self.results_area.node_data) + ' ' +
					(xpresso_reference_name(node) or '')).casefold()]
			self.results_area.SetResults([node.GetName() for node in nodes], nodes)
		elif search_text.startswith(('@', '#')):
			filter_text = search_text[1:].strip().casefold()
			if search_text.startswith('#'):
				# Keep the actual tag reference; identical names can belong to different objects.
				obj_list = [tag for obj in self.iter_scene_objects() for tag in obj.GetTags()]
				if filter_text:
					obj_list = [tag for tag in obj_list if filter_text in
						(tag.GetName() + ' ' + tag.GetTypeName() + ' ' +
						 tag.GetObject().GetName()).casefold()]
				all_object_names = [tag.GetName() for tag in obj_list]
			else:
				all_object_names = self.get_all_object_names()
				if filter_text:
					matches = [(name, obj) for name, obj in zip(all_object_names, obj_list)
						if filter_text in name.casefold()]
					all_object_names = [name for name, obj in matches]
					obj_list = [obj for name, obj in matches]
			self.results_area.SetResults(all_object_names)

		else:
			obj_list = []
			all_object_names = []

			search_results = [name for name in self.results_area.node_data.keys() if search_text.lower() in name.lower()]
			search_results = sorted(search_results, key=lambda x: (not x.lower().startswith(search_text.lower()), x))
			self.results_area.SetResults(search_results)
		self.LayoutChanged(self.IDC_RESULTS_AREA)

	def iter_scene_objects(self):
		# Iterative depth-first traversal preserves Object Manager order at any depth
		doc = c4d.documents.GetActiveDocument()
		if doc is None:
			return
		pending = list(reversed(doc.GetObjects()))
		while pending:
			obj = pending.pop()
			yield obj
			pending.extend(reversed(obj.GetChildren()))

	def get_all_object_names(self):
		global all_object_names, obj_list
		obj_list = list(self.iter_scene_objects())
		all_object_names = [f"{obj.GetName()} | {obj.GetTypeName()}" for obj in obj_list]
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
		settings = c4d.BaseContainer()
		settings[c4d.TREEVIEW_HIDE_LINES] = True
		settings[c4d.TREEVIEW_NO_MULTISELECT] = True
		settings[c4d.TREEVIEW_HAS_HEADER] = False
		settings[c4d.TREEVIEW_ALTERNATE_BG] = False
		settings[c4d.TREEVIEW_CUSTOM_BG_COLOR] = c4d.COLOR_BG
		settings[c4d.TREEVIEW_NOENTERRENAME] = True
		settings[c4d.TREEVIEW_NO_DELETE] = True
		tree = self.AddCustomGui(self.IDC_RESULTS_AREA, c4d.CUSTOMGUI_TREEVIEW, '',
			c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, 0, 0, settings)
		if tree is None:
			return False
		columns = c4d.BaseContainer()
		columns.SetInt32(0, c4d.LV_USERTREE)
		tree.SetLayout(1, columns)
		self.results_area = ResultsTree(self, tree)
		self.GroupEnd()
		self.update_node_list('')
		return True

	def Timer(self, msg):
		global obj_list, all_object_names
		self.SetTimer(0)
		self.keep_open_after_drag = False
		pending = self.results_area.pending_double_click
		self.results_area.pending_double_click = None
		if pending is None or not self.IsOpen():
			return
		node_name, qualifier = pending
		if not create_xpresso_node(node_name, self.results_area):
			return
		if qualifier != c4d.QUALIFIER_SHIFT:
			obj_list = []
			all_object_names = []
			self.Close()
		else:
			self.results_area.Redraw()

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
		if msg.GetId() == c4d.BFM_LOSTFOCUS:
			if self.keep_open_after_drag:
				return True


			obj_list = []
			all_object_names = []
			self.Close()
		if msg.GetId() == c4d.BFM_INTERACTSTART:
			bc = c4d.BaseContainer()
			if c4d.gui.GetInputState(c4d.BFM_INPUT_KEYBOARD, c4d.KEY_ESC, bc):
				if bc[c4d.BFM_INPUT_VALUE] == 1:
					self.keep_open_after_drag = False
					self.SetTimer(0)
					self.results_area.pending_double_click = None
					obj_list = []
					all_object_names = []
					self.Close()
					return True

			if c4d.gui.GetInputState(c4d.BFM_INPUT_KEYBOARD, c4d.KEY_ENTER, bc):
				if bc[c4d.BFM_INPUT_VALUE] == 1:


					node_name = self.results_area.GetSelectedName()
					#print(node_name)
					if node_name is not None:
						if not create_xpresso_node(node_name, self.results_area):
							return True
					if bc[c4d.BFM_INPUT_QUALIFIER] != c4d.QUALIFIER_SHIFT:
						obj_list = []
						all_object_names = []
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


def install_xcommander_shortcut():
	target = 1001148
	qualifier = c4d.QUALIFIER_SHIFT
	key = ord("C")

	for index in range(gui.GetShortcutCount()):
		row = gui.GetShortcut(index)
		if row.GetInt32(c4d.SHORTCUT_PLUGINID) == PLUGIN_ID:
			return True

	# Don't overwrite another command using Shift+C
	for index in range(gui.GetShortcutCount()):
		row = gui.GetShortcut(index)
		if (
			row.GetInt32(c4d.SHORTCUT_ADDRESS) == target
			and row.GetInt32(0) == qualifier
			and row.GetInt32(1) == key
		):
			print(
				"[XCommander] Shift+C is already assigned in XPresso"
				"Assign a shortcut in Customize Commands"
			)
			return False

	bc = c4d.BaseContainer()
	bc.SetInt32(c4d.SHORTCUT_PLUGINID, PLUGIN_ID)
	bc.SetInt32(c4d.SHORTCUT_ADDRESS, target)
	bc.SetInt32(0, qualifier)
	bc.SetInt32(1, key)

	if not gui.AddShortcut(bc):
		print("[XCommander] Failed to register Shift+C.")
		return False

	return True


def PluginMessage(message_id, data):
	if message_id == c4d.C4DPL_PROGRAM_STARTED:
		install_xcommander_shortcut()
		return True
	return False

if __name__ == "__main__":
	exec_plug = c4d.plugins.RegisterCommandPlugin(PLUGIN_ID, PLUGIN_NAME, PLUGIN_INFO, PLUGIN_ICON, PLUGIN_HELP,
												  XCom_pl())
	if (exec_plug):
		print("XCOMMANDER registered successfully")
