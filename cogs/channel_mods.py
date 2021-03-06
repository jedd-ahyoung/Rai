import discord
from discord.ext import commands
from .utils import helper_functions as hf
import re

import os
dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SP_SERV = 243838819743432704
JP_SERV = 189571157446492161

def any_channel_mod_check(ctx):
    if ctx.command.name == 'staffping':
        if ctx.guild.id == JP_SERV:
            return hf.submod_check(ctx)
    if ctx.guild.id != SP_SERV:
        return
    if hf.submod_check(ctx):
        return True
    chmd_config = ctx.bot.db['channel_mods'][str(SP_SERV)]
    helper_role = ctx.guild.get_role(591745589054668817)
    for ch_id in chmd_config:
        if ctx.author.id in chmd_config[ch_id]:
            if helper_role:
                if helper_role in ctx.author.roles:
                    return True
            else:
                return True


class ChannelMods(commands.Cog):
    """Commands that channel mods can use in their specific channels only. For adding channel \
    mods, see `;help channel_mod`. Submods and admins can also use these commands."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if not ctx.guild:
            return
        if str(ctx.guild.id) not in self.bot.db['mod_channel'] and ctx.command.name != 'set_mod_channel':
            await hf.safe_send(ctx, "Please set a mod channel using `;set_mod_channel`.")
            return
        if not hf.submod_check(ctx):
            if ctx.author.id in self.bot.db['channel_mods'].get(str(ctx.guild.id), {}).get(str(ctx.channel.id), {}):
                return True
            if ctx.channel.id == self.bot.db['submod_channel'].get(str(ctx.guild.id), None):
                return True
        else:
            return True
        if ctx.command.name == 'role':
            return True

    @commands.command(name="delete", aliases=['del'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True, manage_messages=True)
    async def msg_delete(self, ctx, *ids):
        """A command to delete messages for submods.  Usage: `;del <list of IDs>`\n\n
        Example: `;del 589654995956269086 589654963337166886 589654194189893642`"""
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        await hf.safe_send(ctx.author, f"I'm gonna delete your message to potentially keep your privacy, but in case "
                                       f"something goes wrong, here was what you sent: \n{ctx.message.content}")
        msgs = []
        failed_ids = []
        invalid_ids = []

        if len(ids) == 1:
            if not 17 < len(ids[0]) < 22:
                try:
                    int(ids[0])
                except ValueError:
                    pass
                else:
                    await hf.safe_send(ctx, "This is a command to delete a certain message by specifying its "
                                            f"message ID. \n\nMaybe you meant to use `;clear {ids[0]}`?")

        # search ctx.channel for the ids
        for msg_id in ids:
            try:
                msg_id = int(msg_id)
                if not 17 < len(str(msg_id)) < 22:
                    raise ValueError
                msg = await ctx.channel.fetch_message(msg_id)
                msgs.append(msg)
            except discord.NotFound:
                failed_ids.append(msg_id)
            except (discord.HTTPException, ValueError):
                invalid_ids.append(msg_id)

        if invalid_ids:
            await hf.safe_send(ctx, f"The following IDs were not properly formatted: "
                                    f"`{'`, `'.join([str(i) for i in invalid_ids])}`")

        # search every channel, not just ctx.channel for the missing IDs
        if failed_ids:
            for channel in ctx.guild.text_channels:
                for msg_id in failed_ids.copy():
                    try:
                        msg = await channel.fetch_message(msg_id)
                        msgs.append(msg)
                        failed_ids.remove(msg_id)
                    except discord.NotFound:
                        break
                    except discord.Forbidden:
                        break
                if not failed_ids:
                    break
        if failed_ids:
            await hf.safe_send(ctx, f"Unable to find ID(s) `{'`, `'.join([str(i) for i in failed_ids])}`.")

        if not msgs:
            return  # no messages found

        emb = discord.Embed(title=f"Deleted messages in #{msg.channel.name}", color=discord.Color(int('ff0000', 16)),
                            description=f"")
        embeds = []
        for msg_index in range(len(msgs)):
            msg = msgs[msg_index]
            jump_url = ''
            async for msg_history in msg.channel.history(limit=1, before=msg):
                jump_url = msg_history.jump_url
            try:
                await msg.delete()
            except discord.NotFound:
                continue
            except discord.Forbidden:
                await ctx.send(f"I lack the permission to delete messages in {msg.channel.mention}.")
                return
            if msg.embeds:
                for embed in msg.embeds:
                    embeds.append(embed)
                    emb.add_field(name=f"Embed deleted", value=f"Content shown below ([Jump URL]({jump_url}))")
            if msg.content:
                emb.add_field(name=f"Message {msg_index} by {str(msg.author)} ({msg.author.id})",
                              value=f"{msg.content}"[:1008 - len(jump_url)] + f" ([Jump URL]({jump_url}))")
            if msg.content[1009:]:
                emb.add_field(name=f"continued", value=f"...{msg.content[1009-len(jump_url):len(jump_url)+1024]}")
            if msg.attachments:
                x = [f"{att.filename}: {att.proxy_url}" for att in msg.attachments]
                if not msg.content:
                    name = f"Message attachments by {str(msg.author)} (might expire soon):"
                else:
                    name = "Attachments (might expire soon):"
                emb.add_field(name=name, value='\n'.join(x))
            emb.timestamp = msg.created_at
        emb.set_footer(text=f"Deleted by {str(ctx.author)} - Message sent at:")
        if str(ctx.guild.id) in self.bot.db['submod_channel']:
            channel = self.bot.get_channel(self.bot.db['submod_channel'][str(ctx.guild.id)])
            if not channel:
                await hf.safe_send(ctx, "I couldn't find the channel you had set as your submod channel. Please "
                                        "set it again.")
                del(self.bot.db['submod_channel'][str(ctx.guild.id)])
                return
        elif str(ctx.guild.id) in self.bot.db['mod_channel']:
            channel = self.bot.get_channel(self.bot.db['mod_channel'][str(ctx.guild.id)])
            if not channel:
                await hf.safe_send(ctx, "I couldn't find the channel you had set as your submod channel. Please "
                                        "set it again.")
                del(self.bot.db['submod_channel'][str(ctx.guild.id)])
                return
        else:
            await hf.safe_send(ctx, "Please set either a mod channel or a submod channel with "
                                    "`;set_mod_channel` or `;set_submod_channel`")
            return

        await hf.safe_send(channel, embed=emb)
        if embeds:
            for embed in embeds:
                if not embed:
                    continue
                await hf.safe_send(channel, embed=embed)

    @commands.command(name="pin")
    # @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    async def pin_message(self, ctx, *args):
        """Pin a message. Type the message ID afterwards like `;pin 700749853021438022` or include no ID to pin
        the last message in the channel (just type `;pin`). To pin a message from another channel, type either
        `;pin <channel_id> <message_id>` or `;pin <channel_id>-<message_id>` (with a dash in the middle)."""
        to_be_pinned_msg = None
        if len(args) == 0:
            async for message in ctx.channel.history(limit=2):
                if message.content == ';pin':
                    continue
                to_be_pinned_msg = message
        elif len(args) == 1:
            if re.search('^\d{17,22}$', args[0]):
                try:
                    to_be_pinned_msg = await ctx.channel.fetch_message(args[0])
                except discord.NotFound:
                    await hf.safe_send(ctx, "I couldn't find the message you were looking for.")
                    return
            elif re.search('^\d{17,22}-\d{17,22}$', args[0]):
                channel_id = int(args[0].split('-')[0])
                channel = ctx.guild.get_channel(channel_id)
                if not channel:
                    await hf.safe_send(ctx, "I couldn't find the channel you specified!")
                    return
                message_id = int(args[0].split('-')[1])
                to_be_pinned_msg = await channel.fetch_message(message_id)
            else:
                await hf.safe_send(ctx, "Please input a valid ID")
                return
        elif len(args) == 2:
            channel_id = int(args[0])
            channel = ctx.guild.get_channel(channel_id)
            if not channel:
                await hf.safe_send(ctx, "I couldn't find the channel you specified!")
                return
            message_id = int(args[1])
            to_be_pinned_msg = await channel.fetch_message(message_id)
        else:
            await hf.safe_send(ctx, "You gave too many arguments!")
            return

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        try:
            await to_be_pinned_msg.pin()
        except discord.Forbidden:
            await hf.safe_send(ctx, "I lack permission to pin messages in this channel")

    @commands.command()
    async def log(self, ctx, user, *, reason="None"):
        warn = self.bot.get_command('warn')
        if reason:
            reason += ' -s'
        else:
            reason = ' -s'
        await ctx.invoke(warn, user, reason=reason)

    @commands.command(aliases=['channel_helper', 'cm', 'ch'])
    @hf.is_admin()
    async def channel_mod(self, ctx, *, user):
        """Assigns a channel mod"""
        config = self.bot.db['channel_mods'].setdefault(str(ctx.guild.id), {})
        user = await hf.member_converter(ctx, user)
        if not user:
            await ctx.invoke(self.list_channel_mods)
            return
        if str(ctx.channel.id) in config:
            if user.id in config[str(ctx.channel.id)]:
                await hf.safe_send(ctx, "That user is already a channel mod in this channel.")
                return
            else:
                config[str(ctx.channel.id)].append(user.id)
        else:
            config[str(ctx.channel.id)] = [user.id]
        await ctx.message.delete()
        await hf.safe_send(ctx, f"Set {user.name} as a channel mod for this channel", delete_after=5.0)

    @commands.command(aliases=['list_channel_helpers', 'lcm', 'lch'])
    async def list_channel_mods(self, ctx):
        """Lists current channel mods"""
        output_msg = '```md\n'
        if str(ctx.guild.id) not in self.bot.db['channel_mods']:
            return
        for channel_id in self.bot.db['channel_mods'][str(ctx.guild.id)]:
            channel = self.bot.get_channel(int(channel_id))
            output_msg += f"#{channel.name}\n"
            for user_id in self.bot.db['channel_mods'][str(ctx.guild.id)][channel_id]:
                user = self.bot.get_user(int(user_id))
                if not user:
                    await hf.safe_send(ctx, f"<@{user_id}> was not found.  Removing from list...")
                    self.bot.db['channel_mods'][str(ctx.guild.id)][channel_id].remove(user_id)
                    continue
                output_msg += f"{user.display_name}\n"
            output_msg += '\n'
        output_msg += '```'
        await hf.safe_send(ctx, output_msg)

    @commands.command(aliases=['rcm', 'rch'])
    @hf.is_admin()
    async def remove_channel_mod(self, ctx, user):
        """Removes a channel mod. You must do this in the channel they're a channel mod in."""
        config = self.bot.db['channel_mods'].setdefault(str(ctx.guild.id), {})
        user_obj = await hf.member_converter(ctx, user)
        if user_obj:
            user_id = user_obj.id
            user_name = user_obj.name
        else:
            try:
                user_id = int(user)
                user_name = user
            except ValueError:
                await hf.safe_send(ctx, "I couldn't parse the user you listed and couldn't find them in the server. "
                                        "Please check your input.", delete_after=5.0)
                return
            await hf.safe_send(ctx, "Note: I couldn't find that user in the server.", delete_after=5.0)
        if str(ctx.channel.id) in config:
            if user_id not in config[str(ctx.channel.id)]:
                await hf.safe_send(ctx, "That user is not a channel mod in this channel. You must call this command "
                                        "in their channel.")
                return
            else:
                config[str(ctx.channel.id)].remove(user_id)
                if not config[str(ctx.channel.id)]:
                    del config[str(ctx.channel.id)]
        else:
            return
        await ctx.message.delete()
        await hf.safe_send(ctx, f"Removed {user_name} as a channel mod for this channel", delete_after=5.0)

    @commands.command(aliases=['staff'])
    @commands.check(any_channel_mod_check)
    async def staffrole(self, ctx):
        """You can add/remove the staff role from yourself with this"""
        staffrole = ctx.guild.get_role(642782671109488641)
        if staffrole in ctx.author.roles:
            await ctx.author.remove_roles(staffrole)
            await hf.safe_send(ctx, "I've removed the staff role from you")
        else:
            await ctx.author.add_roles(staffrole)
            await hf.safe_send(ctx, "I've given you the staff role.")

    @commands.command()
    @commands.check(any_channel_mod_check)
    async def staffping(self, ctx):
        """Subscribe yourself to staff ping notifications in your DM for when the staff role is pinged on this server"""
        subscribed_users = self.bot.db['staff_ping'][str(ctx.guild.id)]
        if ctx.author.id in subscribed_users:
            subscribed_users.remove(ctx.author.id)
            await hf.safe_send(ctx, "You will no longer receive notifications for staff pings.")
        else:
            subscribed_users.append(ctx.author.id)
            await hf.safe_send(ctx, "You will receive notifications for staff pings.")

    @commands.command(aliases=['r', 't', 'tag'])
    @commands.check(any_channel_mod_check)
    async def role(self, ctx, *, args):
        """Assigns a role to a user. Type `;role <user> <tag codes>`. You can specify\
        multiple languages, fluent languages, or "None" to take away roles. Username must not have spaces or be \
        surrounded with quotation marks.

        If you don't specify a user, then it will find the last user in the channel without a role. *If you do this,\
        you can only specify one role!*

        __Tag codes:__
        - English Native: `english`,  `en`,  `ne`,  `e`
        - Spanish Native: `spanish`,  `sn`,  `ns`,  `s`
        - Other Language: `other`,  `ol`,  `o`
        - Fluency roles: `ee`,  `ae`,  `ie`,  `be`,  `es`,  `as`,  `is`,  `bs`
        (Expert, Advanced, Intermediate, Beginner for English and Spanish)
        - Learning Roles: `le`,  `ls`
        - Remove all roles: `none`,  `n`

        __Examples:__
        - `;role @Ryry013 e` → *Gives English to Ryry013*
        - `;role spanish`  → *Gives to the last roleless user in the channel*
        - `;r Abelian e o as` → *Give English, Other, and Advanced Spanish*
        - `;r "Long name" e` → *Give English to "Long name"*
        - `;r Ryry013 none` → *Take away all roles from Ryry013*"""
        if ctx.guild.id != SP_SERV:
            return
        english = ctx.guild.get_role(243853718758359040)
        spanish = ctx.guild.get_role(243854128424550401)
        other = ctx.guild.get_role(247020385730691073)

        expertenglish = ctx.guild.get_role(709499333266899115)
        advancedenglish = ctx.guild.get_role(708704078540046346)
        intermediateenglish = ctx.guild.get_role(708704480161431602)
        beginnerenglish = ctx.guild.get_role(708704491180130326)

        expertspanish = ctx.guild.get_role(709497363810746510)
        advancedspanish = ctx.guild.get_role(708704473358532698)
        intermediatespanish = ctx.guild.get_role(708704486994215002)
        beginnerspanish = ctx.guild.get_role(708704495302869003)

        learningenglish = ctx.guild.get_role(247021017740869632)
        learningspanish = ctx.guild.get_role(297415063302832128)

        language_roles = [english, spanish, other]
        all_roles = [english, spanish, other,
                     expertenglish, advancedenglish, intermediateenglish, beginnerenglish,
                     expertspanish, advancedspanish, intermediatespanish, beginnerspanish,
                     learningenglish, learningspanish]
        langs_dict = {'english': english, 'e': english, 'en': english, 'ne': english, 
                      's': spanish,  'spanish': spanish,  'sn': spanish,  'ns': spanish,
                      'other': other, 'ol': other, 'o': other,
                      'ee': expertenglish, 'ae': advancedenglish, 'ie': intermediateenglish, 'be': beginnerenglish,
                      'es': expertspanish, 'as': advancedspanish, 'is': intermediatespanish, 'bs': beginnerspanish,
                      'le': learningenglish, 'ls': learningspanish, 
                      'none': None, 'n': None}

        args = args.split()
        if len(args) > 1:  # ;r ryry013 english
            user = await hf.member_converter(ctx, args[0])
            if not user:
                return
            langs = [lang.casefold() for lang in args[1:]]

        elif len(args) == 1:  # something like ;r english
            if args[0].casefold() in ['none', 'n']:
                await hf.safe_send(ctx, "You can't use `none` and not specify a name.")
                return
            langs = [args[0].casefold()]

            user = None  # if it goes through 10 messages and finds no users without a role, it'll default here
            async for message in ctx.channel.history(limit=10):
                found = None
                for role in language_roles:  # check if they already have a role
                    if role in message.author.roles:
                        found = True
                if not found:
                    user = message.author
            if not user:
                await hf.safe_send(ctx, "I couldn't find any users in the last ten messages without a native role.")
                return

        else:  # no args
            await hf.safe_send(ctx, "Gimme something at least! Run `;help role`")
            return

        langs = [lang.casefold() for lang in langs]
        if 'none' in langs or 'n' in langs:
            none = True
            if len(langs) > 1:
                await hf.safe_send(ctx, "If you specify `none`, please don't specify other languages too. "
                                        "That's confusing!")
                return
        else:
            none = False

        for lang in langs:
            if lang not in langs_dict:
                await hf.safe_send(ctx, "I couldn't tell which language you're trying to assign. Type `;r help`")
                return
        if not user:
            await hf.safe_send(ctx, "I couldn't tell who you wanted to assign the role to. `;r <name> <lang>`")
            return

        # right now, user=a member object, lansg=a list of strings the user typed o/e/s/other/english/spanish/etc
        langs = [langs_dict[lang] for lang in langs]  # now langs is a list of role objects
        removed = []
        for role in all_roles:
            if role in user.roles:
                removed.append(role)
        if removed:
            await user.remove_roles(*removed)
        if not none:
            await user.add_roles(*langs)

        if none and not removed:
            await hf.safe_send(ctx, "There were no roles to remove!")
        elif none and removed:
            await hf.safe_send(ctx, f"I've removed the roles of {', '.join([r.mention for r in removed])} from "
                                    f"{user.display_name}.")
        elif removed:
            await hf.safe_send(ctx, f"I assigned {', '.join([r.mention for r in langs])} instead of "
                                    f"{', '.join([r.mention for r in removed])} to {user.display_name}.")
        else:
            await hf.safe_send(ctx, f"I assigned {', '.join([r.mention for r in langs])} to {user.display_name}.")

    @commands.group(aliases=['warnlog', 'ml', 'wl'], invoke_without_command=True)
    async def modlog(self, ctx, id):
        """View modlog of a user"""
        if str(ctx.guild.id) not in ctx.bot.db['modlog']:
            return
        config = ctx.bot.db['modlog'][str(ctx.guild.id)]
        member = await hf.member_converter(ctx, id)
        if member:
            name = f"{member.name}#{member.discriminator} ({member.id})"
            user_id = str(member.id)
        else:
            try:
                user = await self.bot.fetch_user(int(id))
                name = f"{user.name}#{user.discriminator} ({user.id})"
                user_id = id
            except discord.NotFound:
                name = user_id = id
            except discord.HTTPException:
                await hf.safe_send(ctx, "Your ID was not properly formatted. Try again.")
                return
            except ValueError:
                await hf.safe_send(ctx, "I couldn't find the user you were looking for. If they left the server, "
                                        "use an ID")
                return
        if user_id not in config:
            em = hf.red_embed(f"{name} was not found in the modlog.")
            await hf.safe_send(ctx, embed=em)
            return
        config = config[user_id]
        emb = hf.green_embed(f"Modlog for {name}")
        list_length = len(config[-25:])  # this is to prevent the invisible character on the last entry
        index = 1
        for entry in config[-25:]:
            name = f"{config.index(entry) + 1}) {entry['type']}"
            if entry['silent']:
                name += " (silent)"
            value = f"{entry['date']}\n"
            if entry['length']:
                value += f"*For {entry['length']}*\n"
            if entry['reason']:
                value += f"__Reason__: {entry['reason']}\n"
            if entry['jump_url']:
                value += f"[Jump URL]({entry['jump_url']})\n"
            if index < list_length:
                value += "⠀"  # invisible character to guarantee the empty new line
                index += 1
            emb.add_field(name=name,
                          value=value[:1024],
                          inline=False)
        await hf.safe_send(ctx, embed=emb)

    @modlog.command(name='delete', aliases=['del'])
    @hf.is_admin()
    async def modlog_delete(self, ctx, user, index):
        """Delete a modlog entry.  Do `;modlog delete user -all` to clear all warnings from a user.
        Alias: `;ml del`"""
        if str(ctx.guild.id) not in ctx.bot.db['modlog']:
            return
        config = ctx.bot.db['modlog'][str(ctx.guild.id)]
        member = await hf.member_converter(ctx, user)
        if member:
            user_id = str(member.id)
        else:
            user_id = user
        if user_id not in config:
            await hf.safe_send(ctx, "That user was not found in the modlog")
            return
        config = config[user_id]
        if index in ['-a', '-all']:
            del config
            await hf.safe_send(ctx, embed=hf.red_embed(f"Deleted all modlog entries for <@{user_id}>."))
        else:
            try:
                del config[int(index) - 1]
            except IndexError:
                await hf.safe_send(ctx, "I couldn't find that log ID, try doing `;modlog` on the user.")
                return
            except ValueError:
                await hf.safe_send(ctx, "Sorry I couldn't  understand what you were trying to do")
                return
            await ctx.message.add_reaction('✅')

    @modlog.command(name="edit", aliases=['reason'])
    @hf.is_admin()
    async def modlog_edit(self, ctx, user, index: int, *, reason):
        """Edit the reason for a selected modlog.  Example: `;ml edit ryry 2 trolling in voice channels`."""
        if str(ctx.guild.id) not in ctx.bot.db['modlog']:
            return
        config = ctx.bot.db['modlog'][str(ctx.guild.id)]
        member = await hf.member_converter(ctx, user)
        if member:
            user_id = str(member.id)
        else:
            user_id = user
        if user_id not in config:
            await hf.safe_send(ctx, "That user was not found in the modlog")
            return
        config = config[user_id]
        old_reason = config[index - 1]['reason']
        config[index - 1]['reason'] = reason
        await hf.safe_send(ctx, embed=hf.green_embed(f"Changed the reason for entry #{index} from "
                                                     f"```{old_reason}```to```{reason}```"))

    @commands.command()
    @hf.is_admin()
    async def reason(self, ctx, user, index: int, *, reason):
        """Shortcut for `;modlog reason`"""
        await ctx.invoke(self.modlog_edit, user, index, reason=reason)

def setup(bot):
    bot.add_cog(ChannelMods(bot))
