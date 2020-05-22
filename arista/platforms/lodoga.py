from ..core.fixed import FixedSystem
from ..core.platform import registerPlatform
from ..core.types import PciAddr, I2cAddr, NamedGpio, ResetGpio
from ..core.utils import incrange

from ..components.asic.xgs.trident3 import Trident3
from ..components.cpu.amd.k10temp import K10Temp
from ..components.cpu.crow import CrowSysCpld, CrowFanCpldComponent
from ..components.dpm import Ucd90120A, UcdGpi
from ..components.max6658 import Max6658
from ..components.psu import PmbusPsu
from ..components.scd import Scd

from ..descs.fan import FanDesc
from ..descs.psu import PsuDesc
from ..descs.sensor import Position, SensorDesc

@registerPlatform()
class Lodoga(FixedSystem):

   SID = ['Lodoga', 'LodogaSsd']
   SKU = ['DCS-7050CX3-32S', 'DCS-7050CX3-32S-SSD']

   def __init__(self):
      super(Lodoga, self).__init__()

      self.sfpRange = incrange(33, 34)
      self.qsfp100gRange = incrange(1, 32)

      self.inventory.addPorts(sfps=self.sfpRange, qsfps=self.qsfp100gRange)

      self.newComponent(Trident3, PciAddr(bus=0x01))

      scd = self.newComponent(Scd, PciAddr(bus=0x02))

      scd.createWatchdog()

      self.newComponent(K10Temp, sensors=[
         SensorDesc(diode=0, name='Cpu temp sensor',
                    position=Position.OTHER, target=60, overheat=90, critical=95),
      ])

      scd.newComponent(Max6658, scd.i2cAddr(0, 0x4c),
                       waitFile='/sys/class/hwmon/hwmon2', sensors=[
         SensorDesc(diode=0, name='Cpu board temp sensor',
                    position=Position.OTHER, target=55, overheat=75, critical=80),
         SensorDesc(diode=1, name='Back-panel temp sensor',
                    position=Position.OUTLET, target=50, overheat=75, critical=85),
      ])
      scd.newComponent(Ucd90120A, scd.i2cAddr(0, 0x4e, t=3))

      scd.newComponent(CrowFanCpldComponent, addr=scd.i2cAddr(0, 0x60),
                       waitFile='/sys/class/hwmon/hwmon3', fans=[
         FanDesc(fanId) for fanId in incrange(1, 4)
      ])

      scd.newComponent(Max6658, scd.i2cAddr(9, 0x4c),
                       waitFile='/sys/class/hwmon/hwmon4', sensors=[
         SensorDesc(diode=0, name='Board temp sensor',
                    position=Position.OTHER, target=65, overheat=75, critical=85),
         SensorDesc(diode=1, name='Front-panel temp sensor',
                    position=Position.INLET, target=50, overheat=60, critical=65),
      ])

      scd.addSmbusMasterRange(0x8000, 6, 0x80)

      scd.addLeds([
         (0x6050, 'status'),
         (0x6060, 'fan_status'),
         (0x6070, 'psu1'),
         (0x6080, 'psu2'),
         (0x6090, 'beacon'),
      ])

      for psuId in incrange(1, 2):
         scd.addPsu(PmbusPsu,
                    addr=scd.i2cAddr(10 + psuId, 0x58, t=3, datr=2, datw=3),
                    waitFile='/sys/class/hwmon/hwmon%d' % (4 + psuId), psus=[
            PsuDesc(psuId=psuId, led=self.inventory.getLed('psu%s' % psuId),
                    sensors=[
               SensorDesc(diode=0,
                          name='Power supply %d hotspot sensor' % psuId,
                          position=Position.OTHER,
                          target=80, overheat=95, critical=100),
               SensorDesc(diode=1,
                          name='Power supply %d inlet temp sensor' % psuId,
                          position=Position.OTHER,
                          target=55, overheat=70, critical=75),
               SensorDesc(diode=2,
                          name='Power supply %d secondary hotspot sensor' % psuId,
                          position=Position.OTHER,
                          target=80, overheat=108, critical=113),
            ]),
         ])

      scd.newComponent(Ucd90120A, scd.i2cAddr(13, 0x4e, t=3), causes={
         'reboot': UcdGpi(1),
         'watchdog': UcdGpi(2),
         'overtemp': UcdGpi(4),
         'powerloss': UcdGpi(5),
         'systempowerloss': UcdGpi(6),
      })

      scd.addResets([
         ResetGpio(0x4000, 1, False, 'switch_chip_reset'),
         ResetGpio(0x4000, 2, False, 'switch_chip_pcie_reset'),
      ])

      self.syscpld = self.newComponent(CrowSysCpld, I2cAddr(1, 0x23))
      cpld = self.syscpld
      cpld.createPowerCycle()
      scd.addGpios([
         NamedGpio(0x5000, 1, True, False, "psu1_present"),
         NamedGpio(0x5000, 0, True, False, "psu2_present"),
         NamedGpio(0x5000, 9, True, False, "psu1_status"),
         NamedGpio(0x5000, 8, True, False, "psu2_status"),
         NamedGpio(0x5000, 11, True, False, "psu1_ac_status"),
         NamedGpio(0x5000, 10, True, False, "psu2_ac_status"),
      ])

      addr = 0x6100
      for xcvrId in self.sfpRange:
         name = "sfp%d" % xcvrId
         scd.addLedGroup(name, [(addr, name)])
         addr += 0x10

      addr = 0x6140
      for xcvrId in self.qsfp100gRange:
         leds = []
         for laneId in incrange(1, 4):
            name = "qsfp%d_%d" % (xcvrId, laneId)
            leds.append((addr, name))
            addr += 0x10
         scd.addLedGroup("qsfp%d" % xcvrId, leds)

      intrRegs = [
         scd.createInterrupt(addr=0x3000, num=0),
         scd.createInterrupt(addr=0x3030, num=1),
      ]

      addr = 0xa010
      bus = 16
      for xcvrId in self.sfpRange:
         intr = intrRegs[0].getInterruptBit(28 + xcvrId - 33)
         name = 'sfp%d' % xcvrId
         self.inventory.addInterrupt(name, intr)
         scd.addSfp(addr, xcvrId, bus, interruptLine=intr,
                    leds=self.inventory.getLedGroup(name))
         addr += 0x10
         bus += 1

      addr = 0xa050
      bus = 24
      for xcvrId in self.qsfp100gRange:
         intr = intrRegs[1].getInterruptBit(xcvrId - 1)
         name = 'qsfp%d' % xcvrId
         self.inventory.addInterrupt(name, intr)
         scd.addQsfp(addr, xcvrId, bus, interruptLine=intr,
                     leds=self.inventory.getLedGroup(name))
         addr += 0x10
         bus += 1
