from sbbbattlesim.characters import Character
import logging

from sbbbattlesim.events import OnStart
from sbbbattlesim.utils import StatChangeCause, Tribe

logger = logging.getLogger(__name__)

class CharacterType(Character):
    display_name = 'Lordy'

    _attack = 7
    _health = 7
    _level = 6
    _tribes = {Tribe.DWARF}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        class LordyBuffOnStart(OnStart):
            lordy = self
            def handle(self, *args, **kwargs):
                dwarfes = self.manager.valid_characters(
                    _lambda=lambda char: Tribe.DWARF in char.tribes or char.id == 'SBB_CHARACTER_PRINCESSNIGHT'
                )
                stat_change = len(dwarfes) * (4 if self.lordy.golden else 2)
                for dwarf in dwarfes:
                    dwarf.change_stats(attack=stat_change, health=stat_change, temp=False,
                                       reason=StatChangeCause.LORDY_BUFF, source=self.lordy)

        self.owner.register(LordyBuffOnStart)
