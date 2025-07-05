from enum import StrEnum, Enum

class PeakDetectionTypes(Enum):
    f_fo = 'f_fo'
    diameter = 'diameter'

for item in PeakDetectionTypes:
    print('XXXXXX', item.value)
