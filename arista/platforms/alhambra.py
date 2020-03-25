from ..core.driver import KernelDriver
from ..core.fixed import FixedSystem
from ..core.platform import registerPlatform
from ..core.utils import incrange
from ..core.types import PciAddr, NamedGpio, ResetGpio

from ..components.asic.tofino import Tofino
from ..components.common import I2cKernelComponent
from ..components.cpu.rook import RookLedComponent, LAFanCpldComponent, RookSysCpld
from ..components.dpm import Ucd90120A, Ucd90160, UcdGpi
from ..components.lm73 import Lm73
from ..components.max6658 import Max6658
from ..components.psu import PmbusPsu
from ..components.scd import Scd

from ..descs.fan import FanDesc
from ..descs.led import LedDesc

@registerPlatform()
class Alhambra(FixedSystem):

   SID = ['Alhambra', 'AlhambraSsd']
   SKU = ['DCS-7170-64C', 'DCS-7170-64C-M']

   def __init__(self, ports=64):
      super(Alhambra, self).__init__()

      self.qsfpRange = incrange(1, ports)
      self.sfpRange = incrange(ports + 1, ports + 2)

      self.inventory.addPorts(qsfps=self.qsfpRange, sfps=self.sfpRange)

      self.addDriver(KernelDriver, 'rook-led-driver')

      self.newComponent(Tofino, PciAddr(bus=0x07))

      scd = self.newComponent(Scd, PciAddr(bus=0x06))

      scd.createWatchdog()

      scd.newComponent(Max6658, scd.i2cAddr(7, 0x4c),
                       waitFile='/sys/class/hmon/hwmon2')
      scd.newComponent(PmbusPsu, scd.i2cAddr(6, 0x58, t=3, datr=2, datw=3),
                       name='dps1900')
      scd.newComponent(PmbusPsu, scd.i2cAddr(5, 0x58, t=3, datr=2, datw=3),
                       name='dps1900')

      scd.addSmbusMasterRange(0x8000, 9, 0x80)

      scd.addResets([
         ResetGpio(0x4000, 8, False, 'switch_chip_reset'),
         ResetGpio(0x4000, 1, False, 'security_chip_reset'),
         ResetGpio(0x4000, 0, False, 'repeater_sfp_reset'),
      ])

      scd.addGpios([
         NamedGpio(0x5000, 0, True, False, "psu1_present"),
         NamedGpio(0x5000, 1, True, False, "psu2_present"),
         NamedGpio(0x5000, 8, True, False, "psu1_status"),
         NamedGpio(0x5000, 9, True, False, "psu2_status"),
         NamedGpio(0x5000, 10, True, False, "psu1_ac_status"),
         NamedGpio(0x5000, 11, True, False, "psu2_ac_status"),
      ])

      ledComponent = self.newComponent(RookLedComponent, baseName='rook_leds-96',
                                       scd=scd, leds=[
         LedDesc(colors=['blue'], name='beacon'),
         LedDesc(colors=['green', 'red'], name='fan_status'),
         LedDesc(colors=['green', 'red'], name='psu1_status'),
         LedDesc(colors=['green', 'red'], name='psu2_status'),
         LedDesc(colors=['green', 'red'], name='status'),
      ])

      scd.createPsu(1, led=self.inventory.getLed('psu1_status'))
      scd.createPsu(2, led=self.inventory.getLed('psu2_status'))

      addr = 0x6100
      for xcvrId in self.qsfpRange:
         leds = []
         for laneId in incrange(1, 4):
            name = "qsfp%d_%d" % (xcvrId, laneId)
            leds.append(scd.addLed(addr, name))
            addr += 0x10
         self.inventory.addLedGroup("qsfp%d" % xcvrId, leds)

      addr = 0x7200
      for xcvrId in self.sfpRange:
         name = "sfp%d" % xcvrId
         self.inventory.addLedGroup(name, [scd.addLed(addr, name)])
         addr += 0x10

      scd.setMsiRearmOffset(0x190)

      intrRegs = [
         scd.createInterrupt(addr=0x3000, num=0, mask=0x60003ff),
         scd.createInterrupt(addr=0x3030, num=1),
         scd.createInterrupt(addr=0x3060, num=2),
      ]

      addr = 0xA010
      bus = 8
      for xcvrId in sorted(self.qsfpRange):
         intr = intrRegs[xcvrId // 33 + 1].getInterruptBit((xcvrId - 1) % 32)
         name = 'qsfp%d' % xcvrId
         self.inventory.addInterrupt(name, intr)
         scd.addQsfp(addr, xcvrId, bus, interruptLine=intr,
                     leds=self.inventory.getLedGroup(name))
         addr += 0x10
         bus += 1

      addr = 0xA500
      bus = 72
      for xcvrId in sorted(self.sfpRange):
         scd.addSfp(addr, xcvrId, bus,
                    leds=self.inventory.getLedGroup('sfp%d' % xcvrId))
         addr += 0x10
         bus += 1

      cpld = self.newComponent(Scd, PciAddr(bus=0xff, device=0x0b, func=3),
                               newDriver=True)

      cpld.addSmbusMasterRange(0x8000, 4, 0x80, 4)
      cpld.newComponent(Max6658, cpld.i2cAddr(0, 0x4c),
                        waitFile='/sys/class/hwmon/hwmon3')
      cpld.newComponent(Ucd90160, cpld.i2cAddr(1, 0x4e, t=3))
      cpld.newComponent(Ucd90120A, cpld.i2cAddr(10, 0x4e, t=3), causes={
         'powerloss': UcdGpi(1),
         'overtemp': UcdGpi(2),
         'reboot': UcdGpi(4),
         'watchdog': UcdGpi(5),
      })

      laFanCpldAddr = cpld.i2cAddr(12, 0x60)
      laFanComponent = cpld.newComponent(LAFanCpldComponent, addr=laFanCpldAddr,
                                         waitFile='/sys/class/hwmon/hwmon4',
                                         fans=[
         FanDesc(fanId) for fanId in incrange(1, 4)
      ])

      cpld.newComponent(I2cKernelComponent, cpld.i2cAddr(15, 0x20), 'rook_leds')
      cpld.newComponent(Lm73, cpld.i2cAddr(15, 0x48),
                        waitFile='/sys/class/hwmon/hwmon5'),

      cpld.createPowerCycle()

      self.syscpld = self.newComponent(RookSysCpld, cpld.i2cAddr(8, 0x23))