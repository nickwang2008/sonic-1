
from __future__ import absolute_import, division, print_function

from . import registerParser

@registerParser('reboot', help='perform a cold reboot for platform',
                 description='''
Powercycle the switch by cutting power to all components.
The behavior of such reboot differ from a regular CPU reset.
''')
def rebootParser(parser):
   pass
