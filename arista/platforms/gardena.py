from ..core.fixed import FixedSystem
from ..core.platform import registerPlatform
from ..core.psu import PsuSlot
from ..core.types import PciAddr, ResetGpio
from ..core.utils import incrange

from ..components.asic.xgs.tomahawk2 import Tomahawk2
from ..components.dpm import Ucd90120A, Ucd90160, UcdGpi
from ..components.max6658 import Max6658
from ..components.psu.delta import DPS750AB, DPS1900AB
from ..components.psu.emerson import DS750PED
from ..components.scd import Scd

from ..descs.gpio import GpioDesc
from ..descs.sensor import Position, SensorDesc

from .cpu.rook import RookCpu

@registerPlatform()
class Gardena(FixedSystem):

   SID = ['Gardena', 'GardenaE']
   SKU = ['DCS-7260CX3-64', 'DCS-7260CX3-64E']

   def __init__(self):
      super(Gardena, self).__init__()

      self.sfpRange = incrange(65, 66)
      self.qsfpRange = incrange(1, 64)

      self.inventory.addPorts(qsfps=self.qsfpRange, sfps=self.sfpRange)

      self.newComponent(Tomahawk2, PciAddr(bus=0x07))

      scd = self.newComponent(Scd, PciAddr(bus=0x06))
      self.scd = scd

      scd.createWatchdog()

      scd.newComponent(Max6658, scd.i2cAddr(0, 0x4c), sensors=[
         SensorDesc(diode=0, name='Board sensor',
                    position=Position.OTHER, target=65, overheat=75, critical=85),
      ])

      scd.addSmbusMasterRange(0x8000, 8, 0x80)

      scd.addResets([
         ResetGpio(0x4000, 0, False, 'switch_chip_reset'),
         ResetGpio(0x4000, 1, False, 'switch_chip_pcie_reset'),
         ResetGpio(0x4000, 2, False, 'security_asic_reset'),
      ])

      scd.addGpios([
         GpioDesc("psu1_present", 0x5000, 0, ro=True),
         GpioDesc("psu2_present", 0x5000, 1, ro=True),
         GpioDesc("psu1_status", 0x5000, 8, ro=True),
         GpioDesc("psu2_status", 0x5000, 9, ro=True),
         GpioDesc("psu1_ac_status", 0x5000, 10, ro=True),
         GpioDesc("psu2_ac_status", 0x5000, 11, ro=True),
      ])

      cpu = self.newComponent(RookCpu)
      cpu.cpld.newComponent(Ucd90160, cpu.cpuDpmAddr())
      cpu.cpld.newComponent(Ucd90120A, cpu.switchDpmAddr(0x34), causes={
         'powerloss': UcdGpi(1),
         'reboot': UcdGpi(2),
         'watchdog': UcdGpi(3),
         'overtemp': UcdGpi(4),
      })
      self.cpu = cpu
      self.syscpld = cpu.syscpld

      for psuId in incrange(1, 2):
         addrFunc=lambda addr, i=psuId: scd.i2cAddr(1 + i, addr, t=3, datr=2, datw=3)
         name = "psu%d" % psuId
         scd.newComponent(
            PsuSlot,
            slotId=psuId,
            addrFunc=addrFunc,
            presentGpio=scd.inventory.getGpio("%s_present" % name),
            inputOkGpio=scd.inventory.getGpio("%s_ac_status" % name),
            outputOkGpio=scd.inventory.getGpio("%s_status" % name),
            led=cpu.leds.inventory.getLed('%s_status' % name),
            psus=[
               DPS750AB,
               DPS1900AB,
               DS750PED,
            ],
         )

      addr = 0x6100
      for xcvrId in self.qsfpRange:
         leds = []
         for laneId in incrange(1, 4):
            name = "qsfp%d_%d" % (xcvrId, laneId)
            leds.append((addr, name))
            addr += 0x10
         scd.addLedGroup("qsfp%d" % xcvrId, leds)

      addr = 0x7100
      for xcvrId in self.sfpRange:
         name = "sfp%d" % xcvrId
         scd.addLedGroup(name, [(addr, name)])
         addr += 0x10

      intrRegs = [
         scd.createInterrupt(addr=0x3000, num=0),
         scd.createInterrupt(addr=0x3030, num=1),
         scd.createInterrupt(addr=0x3060, num=2),
      ]

      addr = 0xA010
      bus = 8
      for xcvrId in sorted(self.qsfpRange):
         name = 'qsfp%d' % xcvrId
         intr = intrRegs[xcvrId // 33 + 1].getInterruptBit(name, (xcvrId - 1) % 32)
         scd.addQsfp(addr, xcvrId, bus, interruptLine=intr,
                     leds=scd.inventory.getLedGroup(name))
         addr += 0x10
         bus += 1

      addr = 0xA410
      bus = 6
      for xcvrId in sorted(self.sfpRange):
         scd.addSfp(addr, xcvrId, bus,
                    leds=scd.inventory.getLedGroup('sfp%d' % xcvrId))
         addr += 0x10
         bus += 1
