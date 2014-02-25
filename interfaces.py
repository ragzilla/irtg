import re

class InterfaceCollection(list):
	node    = None
	names   = None
	indexes = None
	interesting = None

	def __init__(self, node):
		self.node    = node
		self.names   = dict()
		self.indexes = dict()
		self.interesting = dict()
	
	def GetIfByName(self, name):
		if name in self.names:
			return self.names[name]
		newif = Interface(self, name)
		self.append(newif)
		self.names[name] = newif
	
	def GetIfByIndex(self, index):
		if index in self.indexes:
			return self.indexes[index]
		raise Exception('GetIfByIndex Failed - Index not found.')

	def SetIfIndex(self, name, index):
		if name in self.names:
			self.indexes[index] = self.names[name]
			self.names[name].SetIfIndex(index)
			return True
		raise Exception('SetIfIndex Failed - Name not found.')
	
	def SetIfType(self, index, ifType):
		if index in self.indexes:
			self.indexes[index].SetIfType(ifType)
			return True
		raise Exception('SetIfType Failed - Index not found.')

	def SetIfSpeed(self, index, ifSpeed):
		if index in self.indexes:
			self.indexes[index].SetIfSpeed(ifSpeed)
			return True
		raise Exception('SetIfSpeed Failed - Index not found.')
	
	def SetInteresting(self, intf):
		self.interesting[intf.ifIndex] = intf
		return
	
	def GetInteresting(self, ifIndex):
		if ifIndex in self.interesting:
			return self.interesting[ifIndex]
		return None

class Interface():
	interesting = False
	ifName      = None
	ifIndex     = None
	ifType      = None
	ifSpeed     = None
	ifColl      = None
	graphpoint  = None
	traffic     = None

	def __init__(self, ifc, name):
		self.ifName = name
		self.ifColl = ifc
		parts = re.split('[^A-Za-z0-9]+', str(name).lower())
		self.graphpoint = self.ifColl.node.graphpoint + '.' + '-'.join(parts)
		self.traffic = dict()
	
	def SetIfIndex(self, index):
		self.ifIndex = index
	
	def SetIfType(self, ifType):
		self.ifType = ifType
		# hey I can become interesting now!
		if ifType in [6, 49, 108, 135]: # ethernetCsmacd / aal5 / pppMultilinkBundle / l2vlan
			self.interesting = True
		elif ifType in [23, 53] and self.ifName[0:2] in ['Se', 'Vl', 'Po', 'Gi', 'Fa', 'Et']: # ppp / propVirtual
			self.interesting = True
		if self.interesting:
			self.ifColl.SetInteresting(self)
	
	def SetIfSpeed(self, ifSpeed):
		self.ifSpeed = ifSpeed
	
	def TrafficValue(self, key, val):
		if key in self.traffic:
			oldval = self.traffic[key]
			# if oldval != val:
			# print "%s.%s: %u" % (self.graphpoint, key.lower(), val,)
			self.ifColl.node.nodecollection.graph(self.graphpoint + '.' + key.lower(), val)
			self.traffic[key] = val
		else:
			# seed the traffic value
			self.traffic[key] = val

	def __repr__(self):
		interesting = ""
		if self.interesting:
			interesting = " INTERESTING"
		return "<%s instance (ifIndex: %u | ifName: %s | ifType: %u | ifSpeed: %u | graphpoint: %s))%s>" % \
				(self.__class__, self.ifIndex, self.ifName, self.ifType, self.ifSpeed, self.graphpoint, interesting,)
