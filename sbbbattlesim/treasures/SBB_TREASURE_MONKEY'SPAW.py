from sbbbattlesim.treasures import Treasure
from sbbbattlesim.events import OnDeath
import random
import logging

from sbbbattlesim.utils import StatChangeCause

logger = logging.getLogger(__name__)


class TreasureType(Treasure):
    name = 'Coin of Charon'
    aura = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.coin_trigger = False

    def buff(self, target_character):
        class CoinOfCharonOnDeath(OnDeath):
            priority = 999
            last_breath = False
            coin = self

            def handle(self, *args, **kwargs):
                # This should only proc once per combat
                if self.coin.coin_trigger:
                    return  # This has already procced
                self.coin.coin_trigger = True

                self.manager.change_stats(attack=4, health=4, reason=StatChangeCause.COIN_OF_CHARON, source=self.coin)

        target_character.register(CoinOfCharonOnDeath)
