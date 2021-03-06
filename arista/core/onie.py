
import datetime

from .utils import getCmdlineDict, getMachineConfigDict

class OnieEeprom(object):
   def __init__(self, prefdl):
      self.fields = {
         0x21: prefdl.get('SKU'),
         0x22: prefdl.get('ASY'),
         0x23: prefdl.get('SerialNumber'),
         0x24: prefdl.get('MAC', '').replace(':', ''),
         0x25: self._convertMfgTime(prefdl.get('MfgTime')),
         0x26: "01",
         0x27: '.'.join('%02x' % v for v in prefdl.get('HwApi', [0])),
         0x28: self._getOniePlatform(), # XXX: won't work for modules
         0x2A: None, # num macs (could be added using per platform metadata)
         0x2B: None, # manufacturer
         0x2C: None, # manufacturer country code
         0x2D: 'Arista Networks',
         0x2E: self._getAbootVersion(), # XXX: won't work for modules
         0x2F: prefdl.get('SerialNumbor'), # service tag
      }

   def _getAbootVersion(self):
      return getCmdlineDict().get('Aboot', 'N/A')

   def _getOniePlatform(self):
      name = getCmdlineDict().get('onie_platform')
      if name is not None:
         return name
      return getMachineConfigDict().get('platform')

   def _convertMfgTime(self, mfgtime):
      if mfgtime is None:
         return None
      dobj = datetime.datetime.strptime(mfgtime, '%Y%m%d%H%M%S')
      return dobj.strftime('%Y/%m/%d %H:%M:%S')

   def getField(self, code):
      return self.fields.get(code)

   def data(self, filterOut=None):
      filterOut = filterOut or []
      return {'0x%02x' % k : v for k, v in self.fields.items()
              if v and k not in filterOut}
