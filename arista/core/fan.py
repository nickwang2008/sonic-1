
from ..accessors.fan import FanSlotImpl

from .component import SlotComponent, Priority

class FanSlot(SlotComponent):
   def __init__(self, slotId=None, name=None, description=None, fans=None,
                faultGpio=None, presentGpio=None, maxPowerDraw=0, model='N/A',
                led=None,
                **kwargs):
      super(FanSlot, self).__init__(priority=Priority.COOLING, **kwargs)
      self.slotId = slotId
      self.name = name or 'slot%d' % self.slotId
      self.fans = fans or []
      self.led = led
      self.faultGpio = faultGpio
      self.presentGpio = presentGpio
      self.maxPowerDraw = maxPowerDraw
      self.model = model

      self.fanInv = self.inventory.addFanSlot(FanSlotImpl(self))

   def getId(self):
      return self.slotId

   def getName(self):
      return self.name

   def getModel(self):
      return self.model

   def getFans(self):
      return self.fans

   def getLed(self):
      return self.led

   def getFault(self):
      if self.faultGpio and self.faultGpio.isActive():
         return True
      for fan in self.fans:
         if fan.getFault():
            return True
      return False

   def getPresence(self):
      if self.presentGpio and not self.presentGpio.isActive():
         return False
      for fan in self.fans:
         if not fan.getPresence():
            return False
      return True

   def getMaxPowerDraw(self):
      return self.maxPowerDraw
