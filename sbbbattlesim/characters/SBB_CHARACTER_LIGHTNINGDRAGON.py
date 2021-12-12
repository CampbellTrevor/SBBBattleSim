import logging

from sbbbattlesim.characters import Character
from sbbbattlesim.combat import attack
from sbbbattlesim.events import OnStart
from sbbbattlesim.utils import Tribe

logger = logging.getLogger(__name__)


class LightningDragonOnStart(OnStart):

    def handle(self, *args, **kwargs):
        attack(
            attack_position=self.lightning_dragon.position,
            attacker=self.lightning_dragon.player,
            defender=self.lightning_dragon.player.opponent,
        )


class CharacterType(Character):
    display_name = 'Lightning Dragon'

    flying = True

    _attack = 10
    _health = 1
    _level = 4
    _tribes = {Tribe.DRAGON}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player.board.register(LightningDragonOnStart, lightning_dragon=self)
