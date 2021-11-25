from sbbbattlesim.events import OnDeath
from sbbbattlesim.characters import Character
from sbbbattlesim.utils import Tribe


class CharacterType(Character):
    display_name = 'Evil Queen'
    aura = True

    _attack = 1
    _health = 3
    _level = 3
    _tribes = {Tribe.EVIL, Tribe.QUEEN}

    def buff(self, target_character):
        # Instantiate queen buff
        class EvilQueenOnDeath(OnDeath):
            evil_queen = self
            def handle(self, *args, **kwargs):
                stat_change = 4 if self.evil_queen.golden else 2
                self.evil_queen.change_stats(attack=stat_change, health=stat_change, temp=False,
                                             reason=f'{self.manager} died and Evil Queen triggered')

        # Give evil minions the buff
        if 'evil' in target_character.tribes and target_character is not self:
            target_character.register(EvilQueenOnDeath, temp=True)


        # TODO fix evil tribe