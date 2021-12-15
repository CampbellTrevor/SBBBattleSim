import logging
import random

from sbbbattlesim.characters import Character
from sbbbattlesim.characters import registry as character_registry
from sbbbattlesim.events import OnDeath
from sbbbattlesim.utils import Tribe

logger = logging.getLogger(__name__)


class PumpkinKingOnDeath(OnDeath):
    last_breath = True

    def handle(self, *args, **kwargs):
        summons = []
        dead_in_order = sorted(
            [char for char in self.manager.player.graveyard if Tribe.EVIL in char.tribes],
            key=lambda char: char._level, reverse=True
        )
        #todo do we have a test for this?
        for dead in dead_in_order[:7]:
            summon_choices = list(character_registry.filter(
                _lambda=lambda char: (char._level > 1 and char._level == dead._level - 1 and Tribe.EVIL in char._tribes) or (char.id == 'SBB_CHARACTER_CAT' and dead._level == 2)))
            if summon_choices:
                summons.append(random.choice(summon_choices).new(
                    player=self.manager.player,
                    position=dead.position,
                    golden=self.manager.golden
                ))

        self.manager.player.summon_from_different_locations(summons)


class CharacterType(Character):
    display_name = 'Great Pumpkin King'

    _attack = 10
    _health = 10
    _level = 6
    _tribes = {Tribe.EVIL, Tribe.MONSTER}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(PumpkinKingOnDeath)
