from abc import ABC, abstractmethod
from typing import Optional, Union

import discord
from dateutil.relativedelta import relativedelta
from redbot.core import Config, commands

from .reminder_parse import ReminderParser


class MixinMeta(ABC):
    """Base class for well-behaved type hint detection with composite class.

    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    config: Config
    reminder_parser: ReminderParser
    me_too_reminders: dict[int, dict]
    clicked_me_too_reminder: dict[int, set[int]]
    reminder_emoji: str

    @staticmethod
    @abstractmethod
    def humanize_relativedelta(relative_delta: Union[relativedelta, dict]) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def insert_reminder(self, user_id: int, reminder: dict) -> bool:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def relativedelta_to_dict(relative_delta: relativedelta) -> dict[str, int]:
        raise NotImplementedError()

    @abstractmethod
    async def send_too_many_message(
        self, ctx_or_user: Union[commands.Context, discord.User], maximum: int = -1
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def update_bg_task(
        self,
        user_id: int,
        user_reminder_id: Optional[int] = None,
        partial_reminder: Optional[dict] = None,
    ) -> None:
        raise NotImplementedError()
