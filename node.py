#from twisted.internet import reactor
from interfaces import InterfaceCollection

# Node states
STATE_PAUSED = 0
STATE_CHECKREINDEX = 1
STATE_REINDEXING = 2
STATE_POLLING = 3
STATE_TIMEOUT = 255

validNextState = {
	STATE_PAUSED:       [STATE_CHECKREINDEX, ],
	STATE_CHECKREINDEX: [STATE_REINDEXING, STATE_POLLING, STATE_TIMEOUT, ],
	STATE_REINDEXING:   [STATE_POLLING, STATE_TIMEOUT, STATE_PAUSED, ],
	STATE_POLLING:      [STATE_TIMEOUT, STATE_PAUSED, ],
	STATE_TIMEOUT:      [STATE_PAUSED, ],
	}

# MIBs for Interface Metadata
MIB_IFNAME  = (1,3,6,1,2,1,31,1,1,1,1)
MIB_IFTYPE  = (1,3,6,1,2,1,2,2,1,3)
MIB_IFSPEED = (1,3,6,1,2,1,2,2,1,5)

reindexmibs = [MIB_IFNAME, MIB_IFTYPE, MIB_IFSPEED,]

# MIBs for Traffic
MIB_IFHCINOCTETS  = (1,3,6,1,2,1,31,1,1,1,6)
MIB_IFHCINUCAST   = (1,3,6,1,2,1,31,1,1,1,7)
MIB_IFHCINMCAST   = (1,3,6,1,2,1,31,1,1,1,8)
MIB_IFHCINBCAST   = (1,3,6,1,2,1,31,1,1,1,9)
MIB_IFINDISCARDS  = (1,3,6,1,2,1,2,2,1,13)
MIB_IFINERRORS    = (1,3,6,1,2,1,2,2,1,14)

MIB_IFHCOUTOCTETS = (1,3,6,1,2,1,31,1,1,1,10)
MIB_IFHCOUTUCAST  = (1,3,6,1,2,1,31,1,1,1,11)
MIB_IFHCOUTMCAST  = (1,3,6,1,2,1,31,1,1,1,12)
MIB_IFHCOUTBCAST  = (1,3,6,1,2,1,31,1,1,1,13)
MIB_IFOUTDISCARDS = (1,3,6,1,2,1,2,2,1,19)
MIB_IFOUTERRORS   = (1,3,6,1,2,1,2,2,1,20)

trafficmibs = [
	['ifHCInOctets',  MIB_IFHCINOCTETS],
	['ifHCInUcast',   MIB_IFHCINUCAST],
	['ifHCInMcast',   MIB_IFHCINMCAST],
	['ifHCInBcast',   MIB_IFHCINBCAST],
	['ifInDiscards',  MIB_IFINDISCARDS],
	['ifInErrors',    MIB_IFINERRORS],
	['ifHCOutOctets', MIB_IFHCOUTOCTETS],
	['ifHCOutUcast',  MIB_IFHCOUTUCAST],
	['ifHCOutMcast',  MIB_IFHCOUTMCAST],
	['ifHCOutBcast',  MIB_IFHCOUTBCAST],
	['ifOutDiscards', MIB_IFOUTDISCARDS],
	['ifOutErrors',   MIB_IFOUTERRORS],
]

class Node():
	identifier     = None
	address        = None
	nodecollection = None
	state          = None
	ifc            = None
	reindexstate   = None
	graphpoint     = None
	pending        = None

	def __init__(self, nc, identifier, address):
		self.state          = STATE_CHECKREINDEX
		self.nodecollection = nc
		self.identifier     = identifier
		self.address        = address
		self.ifc            = InterfaceCollection(self)
		parts               = identifier.lower().split('.')
		parts.reverse()
		self.graphpoint     = 'net.performance.' + '.'.join(parts)
		# print "graphpoint: " + self.graphpoint
		self.nodecollection.nodeNotReady(self)
	
	def run(self):
		self.switchState(STATE_CHECKREINDEX)
		self.nodecollection.nodeNotReady(self)
		# add reindex logic

		self.switchState(STATE_POLLING)
		self.pending = 0
		for mib in trafficmibs:
			# 0 = alpha, 1 = mib
			df = self.nodecollection.sendBulkReq(self, ((mib[1], None),))
			df.addCallback(self.trafficResponse, mib)
			df.addErrback(self.trafficError, mib)
			self.pending += 1
		print " -- %s leaving run (pending = %u)" % (self, self.pending, )
	
	def switchState(self, newstate):
		if newstate not in validNextState[self.state]:
			raise Exception('INVALID STATE TRANSITION')
		self.state = newstate
	
	def trafficDone(self):
		self.pending -= 1
		if self.pending <= 0:
			self.pending = None
			self.switchState(STATE_PAUSED)
			self.nodecollection.nodeReady(self)
			return
		# print " -- %s pending now: %u" % (self,self.pending,)

	def trafficError(self, failure, mib):
		print " -- %s timeout while collecting traffic data (%s): %s" % (self,mib[0],failure,)
		self.trafficDone()

	def trafficResponse(self, (errorIndication, errorStatus, errorIndex, varBindTable), inmib):
	#	reactor.callInThread(self.trafficResponseThreaded, (errorIndication, errorStatus, errorIndex, varBindTable), inmib)

	#def trafficResponseThreaded(self, (errorIndication, errorStatus, errorIndex, varBindTable), inmib):
		# print " -- %s trafficResponse %s" % (self, mib[0],)
		# self.trafficDone()
		falling = False
		mib = inmib[1]
		for varBindRow in varBindTable:
			for oid, val in varBindRow:
				if oid[0:len(mib)] == mib:
					if val is not None:
						ifIndex = oid[len(mib)]
						# intf = self.ifc.GetIfByIndex(oid[len(mib)])
						# print " -- %s/%s/%u=%u" % (self, inmib[0], ifIndex, int(val))
						# we should pass this to an Interface object
						intf = self.ifc.GetInteresting(oid[len(mib)])
						if intf:
							# print " -- %s/%s/%u=%u (%s/interesting)" % (self, inmib[0], intf.ifIndex, int(val), intf.ifName, )
							intf.TrafficValue(inmib[0], int(val))
				else:
					falling = True
					break
			if falling: break
		if not falling:
			for oid, val in varBindTable[-1]:
				if val is not None and oid[0:len(mib)] == mib:
					df = self.nodecollection.sendBulkReq(self, varBindTable[-1])
					df.addCallback(self.trafficResponse, inmib)
					df.addErrback(self.trafficError, inmib)
		else:
			self.trafficDone()
	
	def reindex(self):
		self.nodecollection.nodeNotReady(self)
		self.switchState(STATE_REINDEXING)
		# begin reindex
		# get a deffered from the NodeCollection
		self.reindexstate = 0
		df = self.nodecollection.sendBulkReq(self, ((reindexmibs[self.reindexstate], None),))
		df.addCallback(self.reindexResponse)
		df.addErrback(self.reindexError)
	
	def reindexError(self, failure):
		# print "got an error: %s" % (failure,)
		# presumably we timed out... sooooo ...
		self.switchState(STATE_TIMEOUT)
		print " -- %s timed out while reindexing." % (self,)
		self.reindexstate = None
		self.switchState(STATE_PAUSED)
		self.nodecollection.nodeReady(self)
	
	def reindexResponse(self, (errorIndication, errorStatus, errorIndex, varBindTable)):
		# print "in reindexResponse for %s (phase %u)" % (self.identifier, self.reindexstate,)
		mib = reindexmibs[self.reindexstate]
		falling = False
		for varBindRow in varBindTable:
			for oid, val in varBindRow:
				if oid[0:len(mib)] == mib:
					if val is not None:
						ifIndex = oid[len(mib)]
						if self.reindexstate == 0: # MIB_IFNAME
							self.ifc.GetIfByName(val)
							self.ifc.SetIfIndex(val, ifIndex)
						elif self.reindexstate == 1: # MIB_IFTYPE
							self.ifc.SetIfType(ifIndex, val)
						elif self.reindexstate == 2: # MIB_IFSPEED
							self.ifc.SetIfSpeed(ifIndex, val)
						else:
							raise Exception('Fell out of reindexresponse - bad reindexstate')
				else:
					falling = True
					break
			if falling: break
		if not falling:
			for oid, val in varBindTable[-1]:
				if val is not None and oid[0:len(mib)] == mib:
					df = self.nodecollection.sendBulkReq(self, varBindTable[-1])
					df.addCallback(self.reindexResponse)
		else:
			self.reindexstate += 1
			if self.reindexstate >= len(reindexmibs):
				self.reindexstate = None
				self.switchState(STATE_PAUSED)
				self.nodecollection.nodeReady(self)
				### JUMP TO STATE POLLING, TO SEED COUNTERS ###
			else:
				df = self.nodecollection.sendBulkReq(self, ((reindexmibs[self.reindexstate], None),))
				df.addCallback(self.reindexResponse)
	
	def __str__(self):
		return 'Node(%s/%s)' % (self.identifier,self.address,)
