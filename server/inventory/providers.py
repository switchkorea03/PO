"""ERP read boundary. Replace the disconnected provider after iCUBE access is agreed."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class StockSnapshot:
    on_hand:Decimal|None=None
    available:Decimal|None=None
    observed_at:datetime|None=None
    erp_code:str=''
    warehouse:str=''


class DisconnectedInventoryProvider:
    connected=False
    label='ERP 미연결'

    def fetch(self,items):
        # Unknown must remain None; zero is a real, successfully observed quantity.
        return {item:StockSnapshot() for item in items}


def get_inventory_provider():
    return DisconnectedInventoryProvider()
