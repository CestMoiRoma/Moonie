"""Placeholder substitution for welcome/goodbye messages.

Supported tokens: {user}, {user_mention}, {user_name}, {server}, {member_count}.
"""

from __future__ import annotations

DEFAULT_WELCOME = "Welcome {user_mention} to **{server}**! You're member #{member_count}. 🎉"
DEFAULT_GOODBYE = "{user_name} has left **{server}**. 👋"


def render_message(template: str, context: dict[str, str | int]) -> str:
    text = template
    for key, value in context.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def member_context(member, *, mention: bool = True) -> dict[str, str | int]:
    """Build a substitution context from a discord.Member (or preview stand-in)."""
    guild = member.guild
    return {
        "user": str(member),
        "user_mention": member.mention if mention else f"@{member}",
        "user_name": member.display_name,
        "server": guild.name,
        "member_count": guild.member_count or 0,
    }
