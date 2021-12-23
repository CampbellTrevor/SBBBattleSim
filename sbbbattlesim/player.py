import collections
import logging
import random
from collections import OrderedDict
from turtle import position

from sbbbattlesim import utils
from sbbbattlesim.characters import registry as character_registry
from sbbbattlesim.events import EventManager, OnStart, OnSetup
from sbbbattlesim.heros import registry as hero_registry
from sbbbattlesim.spells import registry as spell_registry
from sbbbattlesim.treasures import registry as treasure_registry

logger = logging.getLogger(__name__)


class CastSpellOnStart(OnStart):
    def handle(self, *args, **kwargs):
        self.source.cast_spell(self.kwargs['spell'], trigger_onspell=False)


class PlayerOnSetup(OnSetup):
    def handle(self, stack, *args, **kwargs):
        for char in self.source.valid_characters():
            for buff in sorted(self.source.auras, key=lambda b: b.priority, reverse=True):
                buff._register(char)
                buff._char_buffer.add(char)
                char._action_history.append(buff)
                logger.debug(f'{buff} >>> {char}')

            if char.support:
                support_targets = utils.get_support_targets(char.position, self.source.banner_of_command)
                targets = self.source.valid_characters(_lambda=lambda c: c.position in support_targets)
                for t in targets:
                    char.support._register(t)
                    char.support._char_buffer.add(char)
                    t._action_history.append(char.support)
                    logger.debug(f'{char.support} >>> {t}')


class Player(EventManager):
    def __init__(self, characters, id, board, treasures, hero, hand, spells, level=0, *args, **kwargs):
        super().__init__()
        # Board is board
        self.board = board
        self.board.register(PlayerOnSetup, source=self, priority=0)

        self.__characters = OrderedDict({i: None for i in range(1, 8)})
        self.stateful_effects = {}
        self._attack_slot = None
        self.graveyard = []
        self.id = id
        self.opponent = None
        self.level = level
        self._last_attacker = None
        self._attack_chain = 0
        self._spells_cast = kwargs.get('spells_cast', None)

        # Treasure Counting
        self.banner_of_command = 'SBB_TREASURE_BANNEROFCOMMAND' in treasures
        singing_sword = 'SBB_TREASURE_WHIRLINGBLADES' in treasures
        evileye = 'SBB_TREASURE_HELMOFCOMMAND' in treasures
        mimic = 'SBB_TREASURE_TREASURECHEST' in treasures

        self.support_itr = 1
        if evileye:
            self.support_itr = 2
            if mimic:
                self.support_itr = 3
        logger.debug(f'{self.id} support_itr = {self.support_itr}')


        self.singing_sword_multiplier = 1
        if singing_sword:
            self.singing_sword_multiplier = 2
            if mimic:
                self.singing_sword_multiplier = 3
        logger.debug(f'{self.id} singing_sword_multiplier = {self.singing_sword_multiplier}')

        self.treasures = collections.defaultdict(list)
        for tres in treasures:
            treasure = treasure_registry[tres]
            mimic_count = mimic + ((hero == 'SBB_HERO_THECOLLECTOR') if treasure._level <= 3 else 0)
            treasure = treasure(player=self, mimic=mimic_count)
            logger.debug(f'{self.id} Registering treasure {treasure.pretty_print()}')
            self.treasures[treasure.id].append(treasure)

        self.hand = [character_registry[char_data['id']](player=self, **char_data) for char_data in hand]
        self.hero = hero_registry[hero](player=self, *args, **kwargs)
        logger.debug(f'{self.id} registering hero {self.hero.pretty_print()}')

        for spl in spells:
            if spl in utils.START_OF_FIGHT_SPELLS:
                self.board.register(CastSpellOnStart, spell=spl, source=self, priority=spell_registry[spl].priority)

        for char_data in characters:
            char = character_registry[char_data['id']](player=self, **char_data)
            logger.debug(f'{self.id} registering character {char.pretty_print()}')
            self.__characters[char.position] = char

        self.auras = set()

        for char in self.valid_characters():
            if char.aura:
                try:
                    self.auras.update(set(char.aura))
                except TypeError:
                    self.auras.add(char.aura)

        for tid, tl in self.treasures.items():
            if tid == '''SBB_TREASURE_WHIRLINGBLADES''':
                continue

            for treasure in tl:
                if treasure.aura and treasure.aura:
                    try:
                        self.auras.update(set(treasure.aura))
                    except TypeError:
                        self.auras.add(treasure.aura)

        if self.hero.aura:
            try:
                self.auras.update(set(self.hero.aura))
            except TypeError:
                self.auras.add(self.hero.aura)

    def pretty_print(self):
        return f'{self.id} {", ".join([char.pretty_print() if char else "_" for char in self.characters.values()])}'

    def get_attack_slot(self):
        if self._attack_slot is None:
            self._attack_slot = 1

        # Handle case where tokens are spawning in the same position
        # With the max chain of 5 as implemented to stop trophy hunter + croc + grim soul shenanigans
        if (self.characters.get(self._attack_slot) is self._last_attacker) or (self._attack_chain >= 5) or (
                self._last_attacker is None):
            # Prevents the same character from attacking repeatedly
            if self._last_attacker is not None:
                self._attack_slot += 1
            self._attack_chain = 0
        else:
            self._attack_chain += 1

        # If we are advancing the attack slot do it here
        found_attacker = False
        for _ in range(8):
            character = self.characters.get(self._attack_slot)
            if character is not None:
                if character.attack > 0:
                    found_attacker = True
                    break
            self._attack_slot += 1

            if self._attack_slot >= 8:
                self._attack_slot = 1

        # If we have not found an attacker just return None
        if found_attacker:
            self._last_attacker = self.characters.get(self._attack_slot)
        else:
            return None

        return self._attack_slot

    def spawn(self, character, position):
        logger.info(f'Spawning {character.pretty_print()} in {position} position')
        self.__characters[position] = character
        character.position = position

        # TODO Add in Singing Swords

        support_positions = (5, 6, 7) if self.banner_of_command else utils.get_behind_targets(position)
        support_units = self.valid_characters(_lambda=lambda char: (char.position in support_positions and char.support))
        support_buffs = set([char.support for char in support_units])

        for buff in sorted(self.auras | support_buffs, key=lambda b: b.priority, reverse=True):
            buff.update(targets=[character])

        if character.support:
            pos_ls = utils.get_support_targets(position, self.banner_of_command)
            for c in self.valid_characters(_lambda=lambda char: char.position in pos_ls):
                logger.debug(f'character {character} is supporting {c} with {character.support}')
                character.support.execute(c)

        if character.aura:
            self.auras.add(character.aura)
            character.aura.update(targets=self.valid_characters())
        character('OnSpawn')

        return character

    def despawn(self, character):
        logger.info(f'Despawning {character.pretty_print()}')
        position = character.position
        self.graveyard.append(character)
        self.__characters[position] = None
        logger.info(f'{character.pretty_print()} died')

        if character.support:
            character.support.roll_back()

        if character.aura:
            character.aura.roll_back()

        character('OnDespawn')

        return character

    @property
    def characters(self):
        return {pos: char for pos, char in self.__characters.items()}

    def summon_from_different_locations(self, characters, *args, **kwargs):
        '''Pumpkin King spawns each evil unit at the location a prior one died. This means that we need to be
        able to summon from multiple points at once before running the onsummon stack. This may be useful
        for other things too'''
        summoned_characters = [self.spawn(char, char.position) for char in characters]

        self('OnSummon', summoned_characters=summoned_characters)

        return summoned_characters

    def summon(self, pos, characters, *args, **kwargs):
        summoned_characters = []
        spawn_order = utils.get_spawn_positions(pos)
        for char in characters:
            pos = next((pos for pos in spawn_order if self.__characters.get(pos) is None), None)
            if pos is None:
                break

            summoned_characters.append(self.spawn(char, pos))

        # The player handles on-summon effects
        stack = self('OnSummon', summoned_characters=summoned_characters)

        return summoned_characters

    def transform(self, pos, character, *args, **kwargs):
        if self.__characters[pos] is not None:
            self.spawn(character, pos)

            # TODO wrap this into a nice helper function to be used in the attack slot getter as well
            if self._attack_slot == pos:
                self._attack_slot += 1
                if self._attack_slot > 7:
                    self.attack_slot = 1

    def valid_characters(self, _lambda=lambda char: True):
        """
        Return a list of valid characters based on an optional lambda that is passed in as an additoinal filter
        onto the base lambda that guarantees that the character exists and is not dead
        """
        # NOTE: this assumes that a dead thing can NEVER be targeted
        base_lambda = lambda char: char is not None and not char.dead

        return [char for char in self.__characters.values() if base_lambda(char) and _lambda(char)]

    def cast_spell(self, spell_id, trigger_onspell=True):
        spell = spell_registry[spell_id]
        if spell is None:
            return

        target = None
        if spell.targeted:
            valid_targets = self.valid_characters(_lambda=spell.filter)
            if valid_targets:
                target = random.choice(valid_targets)

        if spell.targeted and target is None:
            return

        logger.debug(f'{self.id} casting {spell}')

        stack = None
        if trigger_onspell:  # for spells in the passed-in list of spells cast, do not increment
            if self._spells_cast is None:
                self._spells_cast = 0
            self._spells_cast += 1

            stack = self('OnSpellCast', caster=self, spell=spell, target=target)

        spell(self).cast(target=target)
