"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds
from features.doors.commands import (
    CmdOpenDoor, CmdCloseDoor, CmdLockDoor, CmdUnlockDoor, CmdDoorStatus
)
from features.combat.commands import CombatCmdSet
from features.equipment.commands import EquipmentCmdSet
from features.shop.commands import ShopCmdSet
from features.crafting.commands import CraftingCmdSet
from features.quests.commands import QuestCmdSet
from features.skills.commands import SkillCmdSet
from features.party.commands import PartyCmdSet
from features.reputation.commands import ReputationCmdSet
from features.bank.commands import BankCmdSet
from features.enchantment.commands import EnchantCmdSet
from features.achievements.commands import AchievementCmdSet
from features.events.commands import EventCmdSet
from features.duels.commands import DuelCmdSet
from features.guilds.commands import GuildCmdSet
from features.records.commands import RecordsCmdSet
from features.market.commands import MarketCmdSet
from features.pets.commands import PetsCmdSet
from features.contracts.commands import ContractCmdSet
from features.classes.commands import ClassCmdSet
from features.subclasses.commands import SubclassCmdSet
from features.buffs.commands import BuffsCmdSet
from features.ranks.commands import RankCmdSet
from features.professions.commands import ProfessionCmdSet
from features.dungeons.commands import DungeonCmdSet
from features.trade.commands import TradeCmdSet
from features.mail.commands import MailCmdSet
from features.world_bosses.commands import WorldBossCmdSet
from features.runes.commands import RunasCmdSet
from features.arena.commands import ArenaCmdSet
from features.housing.commands import HousingCmdSet
from features.bestiary.commands import BestiaryCmdSet
from features.cartography.commands import CartographyCmdSet
from features.mounts.commands import MountCmdSet
from commands.general_commands import GeneralCmdSet


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CmdOpenDoor())
        self.add(CmdCloseDoor())
        self.add(CmdLockDoor())
        self.add(CmdUnlockDoor())
        self.add(CmdDoorStatus())
        # --- Combate ---
        self.add(CombatCmdSet)
        # --- Equipamiento ---
        self.add(EquipmentCmdSet)
        # --- Tienda ---
        self.add(ShopCmdSet)
        # --- Crafteo ---
        self.add(CraftingCmdSet)
        # --- Misiones ---
        self.add(QuestCmdSet)
        # --- Habilidades ---
        self.add(SkillCmdSet)
        # --- Grupo ---
        self.add(PartyCmdSet)
        # --- Reputación ---
        self.add(ReputationCmdSet)
        # --- Banco ---
        self.add(BankCmdSet)
        # --- Encantamiento ---
        self.add(EnchantCmdSet)
        # --- Logros ---
        self.add(AchievementCmdSet)
        # --- Eventos ---
        self.add(EventCmdSet)
        # --- Duelos ---
        self.add(DuelCmdSet)
        # --- Gremios ---
        self.add(GuildCmdSet)
        # --- Récords ---
        self.add(RecordsCmdSet)
        # --- Mercado ---
        self.add(MarketCmdSet)
        # --- Mascotas ---
        self.add(PetsCmdSet)
        # --- Contratos ---
        self.add(ContractCmdSet)
        # --- Clases ---
        self.add(ClassCmdSet)
        # --- Subclases ---
        self.add(SubclassCmdSet)
        # --- Buffs ---
        self.add(BuffsCmdSet)
        # --- Rangos ---
        self.add(RankCmdSet)
        # --- Profesiones ---
        self.add(ProfessionCmdSet)
        # --- Mazmorras ---
        self.add(DungeonCmdSet)
        # --- Intercambio ---
        self.add(TradeCmdSet)
        # --- Correo ---
        self.add(MailCmdSet)
        # --- Jefes de Mundo ---
        self.add(WorldBossCmdSet)
        # --- Runas ---
        self.add(RunasCmdSet)
        # --- Arena y Torneos ---
        self.add(ArenaCmdSet)
        # --- Vivienda ---
        self.add(HousingCmdSet)
        # --- Bestiario ---
        self.add(BestiaryCmdSet)
        # --- Cartografía ---
        self.add(CartographyCmdSet)
        # --- Monturas ---
        self.add(MountCmdSet)
        # --- General ---
        self.add(GeneralCmdSet)

class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
