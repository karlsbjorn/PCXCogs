from abc import ABC, abstractmethod
from typing import Dict, Union

import discord
from discord.ext.commands import CooldownMapping
from redbot.core import Config
from redbot.core.bot import Red

from autoroom.pcx_template import Template


class MixinMeta(ABC):
    """Base class for well-behaved type hint detection with composite class.

    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    bot: Red
    config: Config
    template: Template
    bucket_autoroom_name: CooldownMapping
    extra_channel_name_change_delay: int

    perms_public: Dict[str, bool]
    perms_locked: Dict[str, bool]
    perms_private: Dict[str, bool]

    @staticmethod
    @abstractmethod
    def get_template_data(member: discord.Member):
        raise NotImplementedError()

    @abstractmethod
    def format_template_room_name(self, template: str, data: dict, num: int = 1):
        raise NotImplementedError()

    @abstractmethod
    async def is_admin_or_admin_role(self, who: Union[discord.Role, discord.Member]):
        raise NotImplementedError()

    @abstractmethod
    async def is_mod_or_mod_role(self, who: Union[discord.Role, discord.Member]):
        raise NotImplementedError()

    @abstractmethod
    def check_perms_source_dest(
        self,
        autoroom_source: discord.VoiceChannel,
        category_dest: discord.CategoryChannel,
        with_manage_roles_guild=False,
        with_optional_clone_perms=False,
        split_required_optional_check=False,
        detailed=False,
    ):
        raise NotImplementedError()

    @abstractmethod
    async def get_all_autoroom_source_configs(self, guild: discord.guild):
        raise NotImplementedError()

    @abstractmethod
    async def get_autoroom_source_config(self, autoroom_source: discord.VoiceChannel):
        raise NotImplementedError()

    @abstractmethod
    async def get_autoroom_info(self, autoroom: discord.VoiceChannel):
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def check_if_member_or_role_allowed(
        channel: discord.VoiceChannel,
        member_or_role: Union[discord.Member, discord.Role],
        check_guild_role_perms: bool = False,
    ):
        raise NotImplementedError()

    @abstractmethod
    def get_member_roles(self, autoroom_source: discord.VoiceChannel):
        raise NotImplementedError()

    @abstractmethod
    async def get_bot_roles(self, guild: discord.guild):
        raise NotImplementedError()
