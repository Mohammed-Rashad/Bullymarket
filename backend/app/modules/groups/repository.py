from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.groups.models import (
    Group,
    GroupMember,
    MemberRole,
    MembershipStatus,
)


async def create_group(
    session: AsyncSession,
    *,
    name: str,
    description: str | None,
    image_url: str | None,
    creator_id: UUID,
    invite_code: str,
) -> tuple[Group, GroupMember]:
    group = Group(
        name=name.strip(),
        description=description,
        image_url=image_url,
        created_by=creator_id,
        invite_code=invite_code,
    )
    session.add(group)
    await session.flush()
    membership = GroupMember(
        group_id=group.id,
        user_id=creator_id,
        role=MemberRole.ADMIN,
        status=MembershipStatus.ACTIVE,
    )
    session.add(membership)
    await session.flush()
    return group, membership


async def get_group(session: AsyncSession, group_id: UUID) -> Group | None:
    return await session.get(Group, group_id)


async def get_group_by_invite(session: AsyncSession, invite_code: str) -> Group | None:
    return await session.scalar(select(Group).where(Group.invite_code == invite_code))


async def get_membership(
    session: AsyncSession, group_id: UUID, user_id: UUID
) -> GroupMember | None:
    return await session.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )


async def list_user_groups(
    session: AsyncSession, user_id: UUID
) -> list[tuple[Group, GroupMember]]:
    rows = await session.execute(
        select(Group, GroupMember)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(
            GroupMember.user_id == user_id,
        )
        .order_by(Group.created_at.desc())
    )
    return list(rows.tuples())


async def list_members(session: AsyncSession, group_id: UUID) -> list[GroupMember]:
    return list(
        await session.scalars(
            select(GroupMember)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.joined_at)
        )
    )
