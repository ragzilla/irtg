from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import LineOnlyReceiver

class CarbonProtocol(LineOnlyReceiver):
	def lineReceived(self, line):
		print "CarbonProtocol RECEIVED a line: %s" % (line,)
	
	def sendPoint(self, time, point, val):
		self.sendLine("%s %u %u" % (point, val, time,))

class CarbonFactory(ReconnectingClientFactory):
	protocol = CarbonProtocol
	proto    = None
	nc       = None

	def __init__(self, nc):
		self.nc = nc
	
	def buildProtocol(self, addr):
		p = CarbonProtocol()
		self.proto = p
		return p

