"""The autoroomset command."""
import asyncio

import discord
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import error, info, warning
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.i18n import Translator

from .abc import MixinMeta
from .pcx_lib import SettingDisplay, checkmark

_ = Translator("AutoRoom", __file__)

channel_name_template = {
    "username": _("{{username}}'s Room{% if dupenum > 1 %} ({{dupenum}}){% endif %}"),
    "game": _(
        "{{game}}{% if not game %}{{username}}'s Room{% endif %}{% if dupenum > 1 %} ({{dupenum}}){% endif %}"
    ),
}


class AutoRoomSetCommands(MixinMeta):
    """The autoroomset command."""

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def autoroomset(self, ctx: commands.Context):
        """Configure the AutoRoom cog.

        For a quick rundown on how to get started with this cog,
        check out [the readme](https://github.com/PhasecoreX/PCXCogs/tree/master/autoroom/README.md)
        """

    @autoroomset.command()
    async def settings(self, ctx: commands.Context):
        """Display current settings."""
        server_section = SettingDisplay(_("Server Settings"))
        server_section.add(
            _("Admin access all AutoRooms"),
            await self.config.guild(ctx.guild).admin_access(),
        )
        server_section.add(
            _("Admin access all AutoRoom Text Channels"),
            await self.config.guild(ctx.guild).admin_access_text(),
        )
        server_section.add(
            _("Moderator access all AutoRooms"),
            await self.config.guild(ctx.guild).mod_access(),
        )
        server_section.add(
            _("Moderator access all AutoRoom Text Channels"),
            await self.config.guild(ctx.guild).mod_access_text(),
        )

        autoroom_sections = []
        avcs = await self.get_all_autoroom_source_configs(ctx.guild)
        for avc_id, avc_settings in avcs.items():
            source_channel = ctx.guild.get_channel(avc_id)
            if not source_channel:
                continue
            dest_category = ctx.guild.get_channel(avc_settings["dest_category_id"])
            autoroom_section = SettingDisplay(f"AutoRoom - {source_channel.name}")
            autoroom_section.add(
                _("Room type"),
                avc_settings["room_type"].capitalize(),
            )
            autoroom_section.add(
                _("Destination category"),
                f"#{dest_category.name}" if dest_category else "INVALID CATEGORY",
            )
            if avc_settings["text_channel"]:
                autoroom_section.add(
                    _("Text Channel"),
                    _("True"),
                )
            member_roles = self.get_member_roles(source_channel)
            if member_roles:
                autoroom_section.add(
                    _("Member Roles") if len(member_roles) > 1 else _("Member Role"),
                    ", ".join(role.name for role in member_roles),
                )
            room_name_format = _("Username")
            if avc_settings["channel_name_type"] in channel_name_template:
                room_name_format = avc_settings["channel_name_type"].capitalize()
            elif (
                avc_settings["channel_name_type"] == "custom"
                and avc_settings["channel_name_format"]
            ):
                room_name_format = _('Custom: "{channel_name_format}"').format(
                    channel_name_format=avc_settings["channel_name_format"]
                )
            autoroom_section.add(_("Room name format"), room_name_format)
            autoroom_sections.append(autoroom_section)

        message = server_section.display(*autoroom_sections)
        required_check, optional_check = await self._check_all_perms(ctx.guild)
        if not required_check:
            message += "\n" + error(
                _(
                    "It looks like I am missing one or more required permissions. "
                    "Until I have them, the AutoRoom cog may not function properly "
                    "for all AutoRoom Sources. "
                    "Check `[p]autoroomset permissions` for more information."
                )
            )
        elif not optional_check:
            message += "\n" + warning(
                _(
                    "It looks like I am missing one or more optional permissions. "
                    "All AutoRooms will work, however some features (text channels and "
                    "cloned source permissions) may not work. "
                    "Check `[p]autoroomset permissions` for more information."
                )
            )
        await ctx.send(message)

    @autoroomset.command(aliases=["perms"])
    async def permissions(self, ctx: commands.Context):
        """Check that the bot has all needed permissions."""
        required_check, optional_check, details_list = await self._check_all_perms(
            ctx.guild, detailed=True
        )
        if not details_list:
            await ctx.send(
                info(
                    _(
                        "You don't have any AutoRoom Sources set up! "
                        "Set one up with `[p]autoroomset create` first, "
                        "then I can check what permissions I need for it."
                    )
                )
            )
            return

        if (
            len(details_list) > 1
            and not ctx.channel.permissions_for(ctx.me).add_reactions
        ):
            await ctx.send(
                error(
                    _(
                        "Since you have multiple AutoRoom Sources, "
                        'I need the "Add Reactions" permission to display permission information.'
                    )
                )
            )
            return

        if not required_check:
            await ctx.send(
                error(
                    _(
                        "It looks like I am missing one or more required permissions. "
                        "Until I have them, the AutoRoom Source(s) in question will not function properly."
                        "\n\n"
                        "The easiest way of fixing this is just giving me these permissions as part of my server role, "
                        "otherwise you will need to give me these permissions on the AutoRoom Source and destination "
                        "category, as specified below."
                    )
                )
            )
        elif not optional_check:
            await ctx.send(
                warning(
                    _(
                        "It looks like I am missing one or more optional permissions. "
                        "All AutoRooms will work, however some features (text channels and cloned source permissions) "
                        "may not work. "
                        "\n\n"
                        "The easiest way of fixing this is just giving me these permissions as part of my server role, "
                        "otherwise you will need to give me these permissions on the destination category, "
                        "as specified below."
                        "\n\n"
                        "In the case of optional permissions, any permission on the AutoRoom Source will be copied to "
                        "the created AutoRoom, as if we were cloning the AutoRoom Source. In order for this to work, "
                        "I need each permission to be allowed in the destination category (or server). "
                        "If it isn't allowed, I will skip copying that permission over."
                    )
                )
            )
        else:
            await ctx.send(checkmark(_("Everything looks good here!")))

        if len(details_list) > 1:
            if (
                ctx.channel.permissions_for(ctx.me).add_reactions
                and ctx.channel.permissions_for(ctx.me).read_message_history
            ):
                await menu(ctx, details_list, DEFAULT_CONTROLS, timeout=60.0)
            else:
                for details in details_list:
                    await ctx.send(details)
        else:
            await ctx.send(details_list[0])

    @autoroomset.group()
    async def access(self, ctx: commands.Context):
        """Control access to all AutoRooms."""

    @access.group(name="admin")
    async def access_admin(self, ctx: commands.Context):
        """Change Admin access to AutoRooms."""

    @access_admin.command(name="room")
    async def access_admin_room(self, ctx: commands.Context):
        """Allow Admins to join locked/private AutoRooms."""
        admin_access = not await self.config.guild(ctx.guild).admin_access()
        await self.config.guild(ctx.guild).admin_access.set(admin_access)
        await ctx.send(
            checkmark(
                _(
                    "Admins are {now_or_no_longer} able to join (new) locked/private AutoRooms."
                ).format(now_or_no_longer=_("now") if admin_access else _("no longer"))
            )
        )

    @access_admin.command(name="text")
    async def access_admin_text(self, ctx: commands.Context):
        """Allow Admins to see all AutoRoom Text Channels."""
        admin_access_text = not await self.config.guild(ctx.guild).admin_access_text()
        await self.config.guild(ctx.guild).admin_access_text.set(admin_access_text)
        await ctx.send(
            checkmark(
                _(
                    "Admins are {now_or_no_longer} able to see all (new) AutoRoom Text Channels."
                ).format(
                    now_or_no_longer=_("now") if admin_access_text else _("no longer")
                )
            )
        )

    @access.group(name="mod")
    async def access_mod(self, ctx: commands.Context):
        """Change Moderator access to AutoRooms."""

    @access_mod.command(name="room")
    async def access_mod_room(self, ctx: commands.Context):
        """Allow Moderators to join locked/private AutoRooms."""
        mod_access = not await self.config.guild(ctx.guild).mod_access()
        await self.config.guild(ctx.guild).mod_access.set(mod_access)
        await ctx.send(
            checkmark(
                _(
                    "Moderators are {now_or_no_longer} able to join (new) locked/private AutoRooms."
                ).format(now_or_no_longer=_("now") if mod_access else _("no longer"))
            )
        )

    @access_mod.command(name="text")
    async def access_mod_text(self, ctx: commands.Context):
        """Allow Moderators to see all AutoRoom Text Channels."""
        mod_access_text = not await self.config.guild(ctx.guild).mod_access_text()
        await self.config.guild(ctx.guild).mod_access_text.set(mod_access_text)
        await ctx.send(
            checkmark(
                _(
                    "Moderators are {now_or_no_longer} able to see all (new) AutoRoom Text Channels."
                ).format(
                    now_or_no_longer=_("now") if mod_access_text else _("no longer")
                )
            )
        )

    @autoroomset.command(aliases=["enable", "add"])
    async def create(
        self,
        ctx: commands.Context,
        source_voice_channel: discord.VoiceChannel,
        dest_category: discord.CategoryChannel,
    ):
        """Create an AutoRoom Source.

        Anyone joining an AutoRoom Source will automatically have a new
        voice channel (AutoRoom) created in the destination category,
        and then be moved into it.
        """
        good_permissions, details = self.check_perms_source_dest(
            source_voice_channel, dest_category, detailed=True
        )
        if not good_permissions:
            await ctx.send(
                error(
                    _(
                        "I am missing a permission that the AutoRoom cog requires me to have. "
                        "Check below for the permissions I require in both the AutoRoom Source "
                        "and the destination category. "
                        "Try creating the AutoRoom Source again once I have these permissions."
                        "\n"
                        "{details}"
                        "\n"
                        "The easiest way of doing this is just giving me these permissions as part of my server role, "
                        "otherwise you will need to give me these permissions on the source channel and destination "
                        "category, as specified above."
                    ).format(details=details)
                )
            )
            return
        new_source = {"dest_category_id": dest_category.id}

        # Room type
        options = ["public", "locked", "private", "server"]
        pred = MessagePredicate.lower_contained_in(options, ctx)
        await ctx.send(
            _(
                "**Welcome to the setup wizard for creating an AutoRoom Source!**"
                "\n"
                "Users joining the {source_channel} AutoRoom Source will have an AutoRoom "
                "created in the {dest_category} category and be moved into it."
                "\n\n"
                "**AutoRoom Type**"
                "\n"
                "AutoRooms can be one of the following types when created:"
                "\n"
                "`public ` - Visible and joinable by other users. The AutoRoom Owner can kick/ban users out of them."
                "\n"
                "`locked ` - Visible, but not joinable by other users. The AutoRoom Owner must allow users into their room."
                "\n"
                "`private` - Not visible or joinable by other users. The AutoRoom Owner must allow users into their room."
                "\n"
                "`server ` - Same as a public AutoRoom, but with no AutoRoom Owner. "
                "No modifications can be made to the generated AutoRoom."
                "\n\n"
                "What would you like these created AutoRooms to be by default? (`public`/`locked`/`private`/`server`)"
            ).format(
                source_channel=source_voice_channel.mention,
                dest_category=dest_category.mention,
            )
        )
        try:
            await ctx.bot.wait_for("message", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send(_("No valid answer was received, canceling setup process."))
            return
        new_source["room_type"] = options[pred.result]

        # Check perms room type
        good_permissions, details = self.check_perms_source_dest(
            source_voice_channel,
            dest_category,
            with_manage_roles_guild=new_source["room_type"] != "server",
            detailed=True,
        )
        if not good_permissions:
            await ctx.send(
                error(
                    _(
                        "Since you want to have this AutoRoom Source create {room_type} AutoRooms, "
                        "I will need a few extra permissions. "
                        "Try creating the AutoRoom Source again once I have these permissions."
                        "\n"
                        "{details}"
                    ).format(room_type=new_source["room_type"], details=details)
                )
            )
            return

        # Text channel
        pred = MessagePredicate.yes_or_no(ctx)
        await ctx.send(
            _(
                "**Text Channel**"
                "\n"
                "AutoRooms can optionally have a text channel created with them, where only the AutoRoom members can"
                "see and message in it. This is useful to keep AutoRoom specific chat out of your other channels."
                "\n\n"
                "Would you like these created AutoRooms to also have a created text channel? (`yes`/`no`)"
            )
        )
        try:
            await ctx.bot.wait_for("message", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send(_("No valid answer was received, canceling setup process."))
            return
        new_source["text_channel"] = pred.result

        # Check perms text channel
        good_permissions, details = self.check_perms_source_dest(
            source_voice_channel,
            dest_category,
            with_manage_roles_guild=new_source["room_type"] != "server",
            with_text_channel=new_source["text_channel"],
            detailed=True,
        )
        if not good_permissions:
            await ctx.send(
                warning(
                    _(
                        "Since you want to have this AutoRoom Source also create text channels, "
                        "I will need a few extra permissions. "
                        "Until I have these permissions, text channels will not be created."
                        "\n"
                        "{details}"
                    ).format(details=details)
                )
            )

        # Channel name
        options = ["username", "game"]
        pred = MessagePredicate.lower_contained_in(options, ctx)
        await ctx.send(
            _(
                "**Channel Name**"
                "\n"
                "When an AutoRoom is created, a name will be generated for it. How would you like that name to be generated?"
                "\n\n"
                '`username` - Shows up as "{message_author}\'s Room"\n'
                "`game    ` - AutoRoom Owner's playing game, otherwise `username`"
            ).format(message_author=ctx.author.display_name)
        )
        try:
            await ctx.bot.wait_for("message", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send(_("No valid answer was received, canceling setup process."))
            return
        new_source["channel_name_type"] = options[pred.result]

        # Save new source
        await self.config.custom(
            "AUTOROOM_SOURCE", ctx.guild.id, source_voice_channel.id
        ).set(new_source)
        await ctx.send(
            checkmark(
                _(
                    "Settings saved successfully!\n"
                    "Check out `[p]autoroomset modify` for even more AutoRoom Source settings, "
                    "or to make modifications to your above answers."
                )
            )
        )

    @autoroomset.command(aliases=["disable", "delete", "del"])
    async def remove(
        self,
        ctx: commands.Context,
        autoroom_source: discord.VoiceChannel,
    ):
        """Remove an AutoRoom Source."""
        await self.config.custom(
            "AUTOROOM_SOURCE", ctx.guild.id, autoroom_source.id
        ).clear()
        await ctx.send(
            checkmark(
                _(
                    "**{source_channel}** is no longer an AutoRoom Source channel."
                ).format(source_channel=autoroom_source.mention)
            )
        )

    @autoroomset.group(aliases=["edit"])
    async def modify(self, ctx: commands.Context):
        """Modify an existing AutoRoom Source."""

    @modify.command(name="category")
    async def modify_category(
        self,
        ctx: commands.Context,
        autoroom_source: discord.VoiceChannel,
        dest_category: discord.CategoryChannel,
    ):
        """Set the category that AutoRooms will be created in."""
        if await self.get_autoroom_source_config(autoroom_source):
            await self.config.custom(
                "AUTOROOM_SOURCE", ctx.guild.id, autoroom_source.id
            ).dest_category_id.set(dest_category.id)
            good_permissions, details = self.check_perms_source_dest(
                autoroom_source, dest_category, detailed=True
            )
            message = f"**{autoroom_source.mention}** will now create new AutoRooms in the **{dest_category.mention}** category."
            if good_permissions:
                await ctx.send(checkmark(message))
            else:
                await ctx.send(
                    warning(
                        f"{message}"
                        "\n"
                        "Do note, this new category does not have sufficient permissions for me to make AutoRooms. "
                        "Until you fix this, the AutoRoom Source will not work."
                        "\n"
                        f"{details}"
                    )
                )
        else:
            await ctx.send(
                error(
                    f"**{autoroom_source.mention}** is not an AutoRoom Source channel."
                )
            )

    @modify.group(name="type")
    async def modify_type(self, ctx: commands.Context):
        """Choose what type of AutoRoom is created."""

    @modify_type.command(name="public")
    async def modify_type_public(
        self, ctx: commands.Context, autoroom_source: discord.VoiceChannel
    ):
        """Rooms will be open to all. AutoRoom Owner has control over room."""
        await self._save_public_private(ctx, autoroom_source, "public")

    @modify_type.command(name="locked")
    async def modify_type_locked(
        self, ctx: commands.Context, autoroom_source: discord.VoiceChannel
    ):
        """Rooms will be visible to all, but not joinable. AutoRoom Owner can allow users in."""
        await self._save_public_private(ctx, autoroom_source, "locked")

    @modify_type.command(name="private")
    async def modify_type_private(
        self, ctx: commands.Context, autoroom_source: discord.VoiceChannel
    ):
        """Rooms will be hidden. AutoRoom Owner can allow users in."""
        await self._save_public_private(ctx, autoroom_source, "private")

    @modify_type.command(name="server")
    async def modify_type_server(
        self, ctx: commands.Context, autoroom_source: discord.VoiceChannel
    ):
        """Rooms will be open to all, but the server owns the AutoRoom (so they can't be modified)."""
        await self._save_public_private(ctx, autoroom_source, "server")

    async def _save_public_private(
        self,
        ctx: commands.Context,
        autoroom_source: discord.VoiceChannel,
        room_type: str,
    ):
        """Save the public/private setting."""
        if await self.get_autoroom_source_config(autoroom_source):
            await self.config.custom(
                "AUTOROOM_SOURCE", ctx.guild.id, autoroom_source.id
            ).room_type.set(room_type)
            await ctx.send(
                checkmark(
                    _(
                        "**{source_channel}** will now create `{room_type}` AutoRooms."
                    ).format(
                        source_channel=autoroom_source.mention, room_type=room_type
                    )
                )
            )
        else:
            await ctx.send(
                error(
                    _("**{source_channel}** is not an AutoRoom Source channel.").format(
                        source_channel=autoroom_source.mention
                    )
                )
            )

    @modify.group(name="name")
    async def modify_name(self, ctx: commands.Context):
        """Set the default name format of an AutoRoom."""

    @modify_name.command(name="username")
    async def modify_name_username(
        self, ctx: commands.Context, autoroom_source: discord.VoiceChannel
    ):
        """Default format: PhasecoreX's Room.

        Custom format example:
        `{{username}}'s Room{% if dupenum > 1 %} ({{dupenum}}){% endif %}`
        """
        await self._save_room_name(ctx, autoroom_source, "username")

    @modify_name.command(name="game")
    async def modify_name_game(
        self, ctx: commands.Context, autoroom_source: discord.VoiceChannel
    ):
        """The users current playing game, otherwise the username format.

        Custom format example:
        `{{game}}{% if not game %}{{username}}'s Room{% endif %}{% if dupenum > 1 %} ({{dupenum}}){% endif %}`
        """
        await self._save_room_name(ctx, autoroom_source, "game")

    @modify_name.command(name="custom")
    async def modify_name_custom(
        self,
        ctx: commands.Context,
        autoroom_source: discord.VoiceChannel,
        *,
        template: str,
    ):
        """A custom channel name.

        Use `{{ expressions }}` to print variables and `{% statements %}` to do basic evaluations on variables.

        Variables supported:
        - `username` - AutoRoom Owner's username
        - `game    ` - AutoRoom Owner's game
        - `dupenum ` - An incrementing number that starts at 1, useful for un-duplicating channel names

        Statements supported:
        - `if/elif/else/endif`
        - Example: `{% if dupenum > 1 %}DupeNum is {{dupenum}}, which is greater than 1{% endif %}`
        - Another example: `{% if not game %}User isn't playing a game!{% endif %}`

        It's kinda like Jinja2, but way simpler. Check out [the readme](https://github.com/PhasecoreX/PCXCogs/tree/master/autoroom/README.md) for more info.
        """
        await self._save_room_name(ctx, autoroom_source, "custom", template)

    async def _save_room_name(
        self,
        ctx: commands.Context,
        autoroom_source: discord.VoiceChannel,
        room_type: str,
        template: str = None,
    ):
        """Save the room name type."""
        if await self.get_autoroom_source_config(autoroom_source):
            data = self.get_template_data(ctx.author)
            if template:
                template = template.replace("\n", " ")
                try:
                    # Validate template
                    self.format_template_room_name(template, data)
                except RuntimeError as rte:
                    await ctx.send(
                        error(
                            _(
                                "Hmm... that doesn't seem to be a valid template:"
                                "\n\n"
                                "`{runtime_error}`"
                                "\n\n"
                                "If you need some help, take a look at "
                                "[the readme](https://github.com/PhasecoreX/PCXCogs/tree/master/autoroom/README.md)."
                            ).format(runtime_error=str(rte))
                        )
                    )
                    return
                await self.config.custom(
                    "AUTOROOM_SOURCE", ctx.guild.id, autoroom_source.id
                ).channel_name_format.set(template)
            else:
                await self.config.custom(
                    "AUTOROOM_SOURCE", ctx.guild.id, autoroom_source.id
                ).channel_name_format.clear()
            await self.config.custom(
                "AUTOROOM_SOURCE", ctx.guild.id, autoroom_source.id
            ).channel_name_type.set(room_type)
            message = _(
                "New AutoRooms created by **{source_channel}** "
                "will use the **{room_type}** format"
            ).format(
                source_channel=autoroom_source.mention, room_type=room_type.capitalize()
            )
            if template:
                message += f":\n`{template}`"
            else:
                # Load preset template for display purposes
                template = channel_name_template[room_type]
                message += "."
            if "game" not in data:
                data["game"] = _("Example Game")
            message += _("\n\nExample room names:")
            for room_num in range(1, 4):
                message += (
                    f"\n{self.format_template_room_name(template, data, room_num)}"
                )
            await ctx.send(checkmark(message))
        else:
            await ctx.send(
                error(
                    _("**{source_channel}** is not an AutoRoom Source channel.").format(
                        source_channel=autoroom_source.mention
                    )
                )
            )

    @modify.group(name="text")
    async def modify_text(
        self,
        ctx: commands.Context,
    ):
        """Manage if a text channel should be created as well."""

    @modify_text.command(name="enable")
    async def modify_text_enable(
        self,
        ctx: commands.Context,
        autoroom_source: discord.VoiceChannel,
    ):
        """Enable creating a text channel with the AutoRoom."""
        if await self.get_autoroom_source_config(autoroom_source):
            await self.config.custom(
                "AUTOROOM_SOURCE", ctx.guild.id, autoroom_source.id
            ).text_channel.set(True)
            await ctx.send(
                checkmark(
                    _(
                        "New AutoRooms created by **{source_channel}** will now get their own text channel."
                    ).format(source_channel=autoroom_source.mention)
                )
            )
        else:
            await ctx.send(
                error(
                    _("**{source_channel}** is not an AutoRoom Source channel.").format(
                        source_channel=autoroom_source.mention
                    )
                )
            )

    @modify_text.command(name="disable")
    async def modify_text_disable(
        self,
        ctx: commands.Context,
        autoroom_source: discord.VoiceChannel,
    ):
        """Disable creating a text channel with the AutoRoom."""
        if await self.get_autoroom_source_config(autoroom_source):
            await self.config.custom(
                "AUTOROOM_SOURCE", ctx.guild.id, autoroom_source.id
            ).text_channel.clear()
            await ctx.send(
                checkmark(
                    _(
                        "New AutoRooms created by **{source_channel}** will no longer get their own text channel."
                    ).format(source_channel=autoroom_source.mention)
                )
            )
        else:
            await ctx.send(
                error(
                    _("**{source_channel}** is not an AutoRoom Source channel.").format(
                        source_channel=autoroom_source.mention
                    )
                )
            )

    @modify_text.group(name="hint")
    async def modify_text_hint(
        self,
        ctx: commands.Context,
    ):
        """Configure sending an introductory message to the text channel."""

    @modify_text_hint.command(name="set")
    async def modify_text_hint_set(
        self,
        ctx: commands.Context,
        autoroom_source: discord.VoiceChannel,
        *,
        hint_text: str,
    ):
        """Send a message to the newly generated text channel.

        This can have template variables and statements, which you can learn more
        about by looking at `[p]autoroomset modify name custom`, or by looking at
        [the readme](https://github.com/PhasecoreX/PCXCogs/tree/master/autoroom/README.md).
        """
        if await self.get_autoroom_source_config(autoroom_source):
            data = self.get_template_data(ctx.author)
            try:
                # Validate template
                hint_text_formatted = self.template.render(hint_text, data)
            except RuntimeError as rte:
                await ctx.send(
                    error(
                        _(
                            "Hmm... that doesn't seem to be a valid template:"
                            "\n\n"
                            "`{runtime_error}`"
                            "\n\n"
                            "If you need some help, take a look at "
                            "[the readme](https://github.com/PhasecoreX/PCXCogs/tree/master/autoroom/README.md)."
                        ).format(runtime_error=str(rte))
                    )
                )
                return

            await self.config.custom(
                "AUTOROOM_SOURCE", ctx.guild.id, autoroom_source.id
            ).text_channel_hint.set(hint_text)

            await ctx.send(
                checkmark(
                    _(
                        "New AutoRooms created by **{source_channel}** will have the following message sent to their text channel:"
                        "\n\n"
                        "{message}"
                    ).format(
                        source_channel=autoroom_source.mention,
                        message=hint_text_formatted,
                    )
                )
            )
        else:
            await ctx.send(
                error(
                    _("**{source_channel}** is not an AutoRoom Source channel.").format(
                        source_channel=autoroom_source.mention
                    )
                )
            )

    @modify_text_hint.command(name="disable")
    async def modify_text_hint_disable(
        self,
        ctx: commands.Context,
        autoroom_source: discord.VoiceChannel,
    ):
        """Disable sending a message to the newly generated text channel."""
        if await self.get_autoroom_source_config(autoroom_source):
            await self.config.custom(
                "AUTOROOM_SOURCE", ctx.guild.id, autoroom_source.id
            ).text_channel_hint.clear()
            await ctx.send(
                checkmark(
                    _(
                        "New AutoRooms created by **{source_channel}** will no longer have a message sent to their text channel."
                    ).format(source_channel=autoroom_source.mention)
                )
            )
        else:
            await ctx.send(
                error(
                    _("**{source_channel}** is not an AutoRoom Source channel.").format(
                        source_channel=autoroom_source.mention
                    )
                )
            )

    @modify.command(
        name="defaults", aliases=["bitrate", "memberrole", "other", "perms", "users"]
    )
    async def modify_defaults(self, ctx: commands.Context):
        """Learn how AutoRoom defaults are set."""
        await ctx.send(
            info(
                _(
                    "**Bitrate/User Limit**"
                    "\n"
                    "Default bitrate and user limit settings are copied from the AutoRoom Source to the resulting AutoRoom."
                    "\n\n"
                    "**Member Roles**"
                    "\n"
                    "Only members that can view and join an AutoRoom Source will be able to join its resulting AutoRooms. "
                    "If you would like to limit AutoRooms to only allow certain members, simply deny the everyone role "
                    "from viewing/connecting to the AutoRoom Source and allow your member roles to view/connect to it."
                    "\n\n"
                    "**Permissions**"
                    "\n"
                    "All permission overwrites (except for Manage Roles) will be copied from the AutoRoom Source "
                    "to the resulting AutoRoom. Every permission overwrite you want copied over, regardless if it is "
                    "allowed or denied, must be allowed for the bot. It can either be allowed for the bot in the "
                    "destination category or server-wide with the roles it has. `[p]autoroomset permissions` will "
                    "show what permissions will be copied over."
                )
            )
        )

    async def _check_all_perms(self, guild: discord.Guild, detailed=False):
        """Check all permissions for all AutoRooms in a guild."""
        result_required = True
        result_optional = True
        result_list = []
        avcs = await self.get_all_autoroom_source_configs(guild)
        for avc_id, avc_settings in avcs.items():
            autoroom_source = guild.get_channel(avc_id)
            category_dest = guild.get_channel(avc_settings["dest_category_id"])
            if autoroom_source and category_dest:
                if detailed:
                    (
                        required_check,
                        optional_check,
                        detail,
                    ) = self.check_perms_source_dest(
                        autoroom_source,
                        category_dest,
                        with_manage_roles_guild=avc_settings["room_type"] != "server",
                        with_text_channel=avc_settings["text_channel"],
                        with_optional_clone_perms=True,
                        split_required_optional_check=True,
                        detailed=True,
                    )
                    result_list.append(detail)
                    result_required = result_required and required_check
                    result_optional = result_optional and optional_check
                else:
                    required_check, optional_check = self.check_perms_source_dest(
                        autoroom_source,
                        category_dest,
                        with_manage_roles_guild=avc_settings["room_type"] != "server",
                        with_text_channel=avc_settings["text_channel"],
                        with_optional_clone_perms=True,
                        split_required_optional_check=True,
                    )
                    result_required = result_required and required_check
                    result_optional = result_optional and optional_check
                    if not result_required and not result_optional:
                        return result_required, result_optional
        if detailed:
            return result_required, result_optional, result_list
        else:
            return result_required, result_optional
