from __future__ import absolute_import

from ...tests.testing import unittest, patch
from ...tests.logging import getLogger

from ...accessors.xcvr import XcvrImpl

from ...components.scd import ScdInterruptRegister

from ...descs.led import LedColor
from ...descs.sensor import SensorDesc

from ...drivers.i2c import I2cKernelDriver
from ...drivers.scd.driver import ScdKernelDriver
from ...drivers.sysfs import SysfsDriver, SysfsEntry

from ...inventory.fan import Fan, FanSlot
from ...inventory.led import Led
from ...inventory.psu import Psu, PsuSlot
from ...inventory.temp import Temp
from ...inventory.xcvr import Xcvr

from .. import utils
from ..config import Config
from ..driver import Driver
from ..fixed import FixedSystem
from ..platform import getPlatformSkus
from ..types import I2cAddr

from ... import platforms as _

def mock_i2cBusFromName(name, idx=0, force=False):
   assert isinstance(name, str)
   return 0

# TODO: remove this type of simulation testing
def mock_inSimulation():
   return False

def mock_locateHwmonFolder(devicePath):
   assert isinstance(devicePath, str)
   return '%s/hwmon/mock' % devicePath

def mock_locateHwmonPath(searchPath, prefix):
   assert isinstance(searchPath, str)
   assert isinstance(prefix, str)
   return '%s/hwmon/mock/%s' % (searchPath, prefix)

def mock_writeConfig(path, data):
   assert isinstance(path, str)
   assert isinstance(data, (list, dict))

def mock_writeComponents(self, components, filename):
   assert components
   assert filename

def mock_sysfsRead(self):
   return '1'

def mock_sysfsWrite(self, value):
   assert value is not None

def mock_read(self, name, path=None):
   assert name
   return '1'

def mock_write(self, name, value, path=None):
   assert name
   assert value is not None

def mock_readReg(self, reg):
   assert reg
   return None

def mock_getStatus(self):
   return True

def mock_waitReady(self):
   return True

def mock_return(self):
   return

def mock_iterAll(self):
   return []

def mock_maybeCreatePath(self, dirPath):
   pass

@patch('arista.drivers.scd.driver.i2cBusFromName', mock_i2cBusFromName)
@patch('arista.core.utils.inSimulation', mock_inSimulation)
@patch('arista.core.utils.locateHwmonFolder', mock_locateHwmonFolder)
@patch('arista.core.utils.locateHwmonPath', mock_locateHwmonPath)
@patch('arista.core.utils.writeConfig', mock_writeConfig)
@patch.object(I2cKernelDriver, 'setup', mock_return)
@patch.object(ScdInterruptRegister, 'readReg', mock_readReg)
@patch.object(ScdInterruptRegister, 'setup', mock_return)
@patch.object(ScdKernelDriver, 'finish', mock_return)
@patch.object(ScdKernelDriver, 'waitReady', mock_waitReady)
@patch.object(ScdKernelDriver, 'writeComponents', mock_writeComponents)
@patch.object(SysfsEntry, '_read', mock_sysfsRead)
@patch.object(SysfsEntry, '_write', mock_sysfsWrite)
@patch.object(SysfsDriver, 'read', mock_read)
@patch.object(SysfsDriver, 'write', mock_write)
@patch.object(utils.FileWaiter, 'waitFileReady', mock_return)
@patch.object(utils.StoredData, 'maybeCreatePath', mock_maybeCreatePath)
class MockPlatformTest(unittest.TestCase):
   @classmethod
   def setUpClass(cls):
      cls.logger = getLogger(cls.__name__)
      cls.ledColors = [
         LedColor.OFF,
         LedColor.GREEN,
         LedColor.RED,
         LedColor.AMBER,
      ]

   def _testLed(self, led):
      self.assertIsInstance(led, Led)
      self.assertIsInstance(led.getName(), str)
      self.assertIsInstance(led.getColor(), str) # TODO: match supported colors
      self.assertIsInstance(led.isStatusLed(), bool)

   def testSetup(self):
      for name, platform in getPlatformSkus().items():
         if not issubclass(platform, FixedSystem):
            continue
         self.logger.info('Testing setup for platform %s', name)
         assert platform
         platform = platform()
         platform.setup()
         assert platform
         self.logger.info('Setting inventory for platform %s', name)
         inventory = platform.getInventory()
         assert inventory

   def testXcvrs(self):
      for name, platform in getPlatformSkus().items():
         if not issubclass(platform, FixedSystem):
            continue
         inventory = platform().getInventory()
         self.logger.info('Testing transceivers for platform %s', name)
         for index, xcvr in inventory.getXcvrs().items():
            self.logger.debug('Testing xcvr index %s', index)
            assert isinstance(xcvr, XcvrImpl)
            assert isinstance(xcvr.name, str)
            assert isinstance(xcvr.driver, Driver)
            assert isinstance(xcvr.addr, I2cAddr)
            assert xcvr.xcvrType in [Xcvr.SFP, Xcvr.QSFP, Xcvr.OSFP]
            assert isinstance(xcvr.xcvrId, int)
            assert isinstance(xcvr.getName(), str)
            assert isinstance(xcvr.getPresence(), bool)
            assert isinstance(xcvr.getLowPowerMode(), bool)
            xcvr.setLowPowerMode(0)
            xcvr.setLowPowerMode(1)
            assert isinstance(xcvr.getModuleSelect(), bool)
            xcvr.setModuleSelect(0)
            xcvr.setModuleSelect(1)
            assert isinstance(xcvr.getTxDisable(), bool)
            xcvr.setTxDisable(0)
            xcvr.setTxDisable(1)
            interruptLine = xcvr.getInterruptLine()
            assert interruptLine is xcvr.interruptLine
            if interruptLine:
               assert isinstance(interruptLine.reg, object)
               assert isinstance(interruptLine.bit, int)
               interruptLine.set()
               interruptLine.clear()
            reset = xcvr.getReset()
            assert reset is xcvr.reset
            if reset:
               assert isinstance(reset.name, str)
               assert isinstance(reset.driver, Driver)
               assert isinstance(reset.getName(), str)
               assert reset.read() in ['0', '1']
               reset.resetIn()
               reset.resetOut()
            leds = xcvr.getLeds()
            for led in leds:
               self._testLed(led)

   def _testPsu(self, psu):
      self.assertIsInstance(psu, Psu)
      self.assertIsInstance(psu.psuId, int)
      self.assertIsInstance(psu.getName(), str)
      self.assertIsInstance(psu.getModel(), str)
      self.assertIsInstance(psu.getSerial(), str)
      self.assertIsInstance(psu.getStatus(), bool)

   def _testPsuSlot(self, slot):
      self.assertIsInstance(slot, PsuSlot)
      self.assertIsInstance(slot.getId(), int)
      self.assertIsInstance(slot.getName(), str)
      self.assertIsInstance(slot.getPresence(), bool)
      self.assertIsInstance(slot.getStatus(), bool)
      led = slot.getLed()
      if led is not None:
         self._testLed(led)
      psu = slot.getPsu()
      if psu is not None:
         self._testPsu(psu)

   def testPsus(self):
      for name, platform in getPlatformSkus().items():
         if not issubclass(platform, FixedSystem):
            continue
         inventory = platform().getInventory()
         self.logger.info('Testing PSUs for platform %s', name)
         for slot in inventory.getPsuSlots():
            self._testPsuSlot(slot)
         for psu in inventory.getPsus():
            self._testPsu(psu)

   def _testFan(self, fan):
      self.assertIsInstance(fan, Fan)
      self.assertIsInstance(fan.driver, Driver)
      self.assertIsInstance(fan.getId(), int)
      self.assertIsInstance(fan.getPresence(), bool)
      self.assertIsInstance(fan.getStatus(), bool)
      self.assertIsInstance(fan.getName(), str)
      self.assertIsInstance(fan.getSpeed(), int)
      assert (not fan.getSpeed() < 0) or (not fan.getSpeed() > 100)
      fan.setSpeed(100)
      self.assertIsInstance(fan.getDirection(), str)
      led = fan.getLed()
      if led is not None:
         self._testLed(led)

   def _testFanSlot(self, slot):
      self.assertIsInstance(slot, FanSlot)
      self.assertIsInstance(slot.getId(), int)
      self.assertIsInstance(slot.getName(), str)
      self.assertIsInstance(slot.getModel(), str)
      self.assertIsInstance(slot.getFault(), bool)
      self.assertIsInstance(slot.getDirection(), str)
      self.assertIsInstance(slot.getPresence(), bool)
      self.assertIsInstance(slot.getMaxPowerDraw(), float)
      fans = slot.getFans()
      for fan in fans or []:
         self._testFan(fan)
      led = slot.getLed()
      if led is not None:
         self._testLed(led)

   def testFans(self):
      for name, platform in getPlatformSkus().items():
         if not issubclass(platform, FixedSystem):
            continue
         inventory = platform().getInventory()
         self.logger.info('Testing fans for platform %s', name)
         for slot in inventory.getFanSlots():
            self._testFanSlot(slot)
         for fan in inventory.getFans():
            self._testFan(fan)

   def _testTemp(self, temp):
      self.assertIsInstance(temp, Temp)
      self.assertIsInstance(temp.driver, Driver)
      desc = temp.getDesc()
      self.assertIsInstance(desc, SensorDesc)
      self.assertIsInstance(desc.target, float)
      self.assertIsInstance(desc.overheat, float)
      self.assertIsInstance(desc.critical, float)
      self.assertTrue(desc.target <= desc.overheat <= desc.critical)
      self.assertIsInstance(temp.getName(), str)
      self.assertIsInstance(temp.getPresence(), bool)
      self.assertIsInstance(temp.getStatus(), bool)
      self.assertIsInstance(temp.getModel(), str)
      self.assertIsInstance(temp.getTemperature(), float)
      self.assertTrue(0 <= temp.getTemperature() < 200)
      self.assertIsInstance(temp.getLowThreshold(), float)
      self.assertTrue(-200 <= temp.getLowThreshold() < 200)
      temp.setLowThreshold(10)
      self.assertIsInstance(temp.getLowCriticalThreshold(), float)
      self.assertTrue(-200 <= temp.getLowCriticalThreshold() < 200)
      self.assertIsInstance(temp.getHighThreshold(), float)
      self.assertTrue(0 <= temp.getHighThreshold() < 200)
      temp.setHighThreshold(50)
      self.assertIsInstance(temp.getHighCriticalThreshold(), float)
      self.assertTrue(0 <= temp.getHighCriticalThreshold() < 200)

   def testTemps(self):
      for name, platform in getPlatformSkus().items():
         if not issubclass(platform, FixedSystem):
            continue
         inventory = platform().getInventory()
         self.logger.info('Testing fans for platform %s', name)
         for temp in inventory.getTemps():
            self._testTemp(temp)

   def testComponents(self):
      def _testSubcomponentPriority(component):
         for sub in component.components:
            assert sub.priority >= component.priority
            _testSubcomponentPriority(sub)

      for name, platform in getPlatformSkus().items():
         if not issubclass(platform, FixedSystem):
            continue
         self.logger.info('Testing components priority for platform %s', name)
         for component in platform().iterComponents():
            _testSubcomponentPriority(component)

class MockPlatformMetaTest(MockPlatformTest):
   def setUp(self):
      Config().use_metainventory = True

   def tearDown(self):
      Config().use_metainventory = False

if __name__ == '__main__':
   unittest.main()
