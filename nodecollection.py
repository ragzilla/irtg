from node import Node
from carbon import CarbonFactory
from twisted.internet import reactor, defer
from pysnmp.entity import engine, config
from pysnmp.carrier.twisted import dispatch
from pysnmp.carrier.twisted.dgram import udp
from pysnmp.entity.rfc3413.twisted import cmdgen
from pprint import pprint
from sys import exit
from time import time
from math import floor

ALIGN_TIME = 60
SNMP_COMMUNITY = 'CHANGEME'
GRAPHITE_HOST = '127.0.0.1'

class NodeCollection(list):
	unReadyNodes = None
	identifiers  = None
	snmpEngine   = None
	bcmdgen      = None
	runTime      = None
	carbonFact   = None

	def __init__(self):
		self.unReadyNodes = list()
		self.identifiers  = dict()
		self.snmpEngine   = engine.SnmpEngine()
		self.bcmdgen      = cmdgen.BulkCommandGenerator()

		self.snmpEngine.registerTransportDispatcher(dispatch.TwistedDispatcher())
		config.addV1System(self.snmpEngine, 'test-agent', SNMP_COMMUNITY)
		config.addTargetParams(self.snmpEngine, 'myParams', 'test-agent', 'noAuthNoPriv', 1)

		config.addSocketTransport(
	        self.snmpEngine,
	        udp.domainName,
	        udp.UdpTwistedTransport().openClientMode()
	        )

		self.carbonFact = CarbonFactory(self)
		reactor.connectTCP(GRAPHITE_HOST, 2003, self.carbonFact)
	
	def addNode(self, identifier, address):
		if identifier in self.identifiers:
			return false
		newnode = Node(self, identifier, address)
		self.append(newnode)
		self.identifiers[identifier] = newnode
		config.addTargetAddr(self.snmpEngine, identifier, config.snmpUDPDomain, (address, 161), 'myParams', timeout=5)
		newnode.reindex()
	
	def ready(self):
		return len(self.unReadyNodes) == 0
		
	def nodeReady(self, node):
		if node in self.unReadyNodes:
			self.unReadyNodes.remove(node)
			print "got nodeReady for: %s (still unReady: %u)" % (node,len(self.unReadyNodes),)
			# pprint(node.ifc)
		if self.ready():
			self.align()
	
	def nodeNotReady(self, node):
		if node not in self.unReadyNodes:
			self.unReadyNodes.append(node)
			print "got nodeNotReady for: %s" % (node,)
	
	def align(self):
		if not self.ready():
			raise Exception('align called while not ready.')
		print "aligning for %f" % (ALIGN_TIME - (time() % ALIGN_TIME),)
		reactor.callLater(ALIGN_TIME - (time() % ALIGN_TIME), self.runNodes)

	def runNodes(self):
		if not self.ready():
			raise Exception('runNodes called while not ready.')
		print "in self.runnodes at: %f" %  (time(),)
		self.runTime = floor(time())
		for node in self:
			node.run()
	
	def sendBulkReq(self, node, oids):
		# send a bulk snmp req, return a deffered
		df = self.bcmdgen.sendReq(self.snmpEngine, node.identifier, 0, 25, oids)
		return df
	
	def graph(self, point, value):
		# print "point: %u %s=%u" % (self.runTime, point, value,)
		# print "%s %u %u" % (point, value, self.runTime,)
		self.carbonFact.proto.sendPoint(self.runTime, point, value)

if __name__ == "__main__":
	# test code
	nc = NodeCollection()
	nc.addNode('CHANGEME', '127.0.0.1')
	reactor.run()
