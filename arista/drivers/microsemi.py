
import os

from ..core.driver import Driver
from ..core.types import PciAddr
from ..core.utils import MmapResource
from ..libs.wait import waitFor

class MicrosemiConsts(object):
   GAS_DONE = 2
   GAS_INPROGRESS = 1
   SWITCHTEC_MAX_PORTS = 48
   MICROSEMI_VENDOR_ID = 0x11f8
   MICROSEMI_DEVICE_IDS = [ 0x8533, 0x8534, 0x8532 ]
   MICROSEMI_BUS = 5
   MICROSEMI_FUNC = 1

class MicrosemiGAS(object):
   GAS_INPUT_DATA = 0
   GAS_OUTPUT_DATA = 0x400
   GAS_COMMAND = 0x800
   GAS_STATUS = 0x804
   GAS_RETURNVALUE = 0x808

class MCRPC_P2PSubcommand(object):
   MRPC_P2P_BIND = 0
   MRPC_P2P_UNBIND = 1
   MRPC_P2P_INFO = 3

class MicrosemiMRPC(MCRPC_P2PSubcommand):
   MRPC_PORTLN = 8
   MRPC_PORTPARTP2P = 12
   MRPC_LNKSTAT = 28

class MicrosemiDriver(MicrosemiConsts, MicrosemiMRPC, MicrosemiGAS, Driver):
   def __init__(self, addr, **kwargs):
      super(MicrosemiDriver, self).__init__(addr=addr, **kwargs)
      self.microsemiBar = 0
      self.mapResource()

   def mapResource(self):
      p = os.path.join(self.addr.getSysfsPath(), "resource%d" % self.microsemiBar)
      self.resource = MmapResource(p)
      self.resource.map()

   def write32(self, offset, value):
      return self.resource.write32(offset, value)

   def read32(self, offset):
      return self.resource.read32(offset)

   def gasWait(self):
      def status():
         return self.read32(self.GAS_STATUS)
      waitFor(lambda: (status() == self.GAS_DONE))
      return self.read32(self.GAS_RETURNVALUE)

   def doGas(self, argument, cmd):
      self.write32(self.GAS_INPUT_DATA, argument)
      self.write32(self.GAS_COMMAND, cmd)
      return self.gasWait()

   def bind(self, port, dsp=1, partition=0):
      return self.doGas(self.MRPC_P2P_BIND | int(partition) << 8 |
                        int(dsp) << 16 | int(port) << 24,
                        self.MRPC_PORTPARTP2P)

   def unbind(self, dsp, partition=0, flags=0x2):
      return self.doGas(self.MRPC_P2P_UNBIND | int(partition) << 8 |
                        int(dsp) << 16 | int(flags) << 24,
                        self.MRPC_PORTPARTP2P)