import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.modules.groups import repository
from app.modules.groups.models import Group, GroupMember, MemberRole, MembershipStatus
from app.modules.users.service import list_users_by_ids


async def _members_with_names(
    session: AsyncSession,
    members: list[GroupMember],
) -> list[tuple[GroupMember, str]]:
    users = await list_users_by_ids(session, [member.user_id for member in members])
    display_names = {user.id: user.display_name for user in users}
    try:
        return [(member, display_names[member.user_id]) for member in members]
    except KeyError as exc:
        raise DomainError(
            "invalid_membership",
            "A group membership references a missing user",
            500,
        ) from exc


async def get_membership_state(
    session: AsyncSession, group_id: UUID, user_id: UUID
) -> GroupMember | None:
    return await repository.get_membership(session, group_id, user_id)


async def require_membership(
    session: AsyncSession,
    group_id: UUID,
    user_id: UUID,
    *,
    active: bool = True,
) -> GroupMember:
    membership = await repository.get_membership(session, group_id, user_id)
    if membership is None or (active and membership.status is not MembershipStatus.ACTIVE):
        raise DomainError("not_group_member", "You are not an active member of this group", 403)
    return membership


async def require_admin(
    session: AsyncSession, group_id: UUID, user_id: UUID
) -> GroupMember:
    membership = await require_membership(session, group_id, user_id)
    if membership.role is not MemberRole.ADMIN:
        raise DomainError("admin_required", "A group admin must perform this action", 403)
    return membership


async def create_group(
    session: AsyncSession,
    *,
    name: str,
    description: str | None,
    image_url: str | None,
    creator_id: UUID,
) -> tuple[Group, GroupMember]:
    return await repository.create_group(
        session,
        name=name,
        description=description,
        image_url=image_url,
        creator_id=creator_id,
        invite_code=secrets.token_urlsafe(8),
    )


async def join_group(
    session: AsyncSession, *, invite_code: str, user_id: UUID
) -> tuple[Group, GroupMember]:
    group = await repository.get_group_by_invite(session, invite_code)
    if group is None:
        raise DomainError("invalid_invite", "This group invite code is invalid", 404)
    membership = await repository.get_membership(session, group.id, user_id)
    if membership is None:
        membership = GroupMember(
            group_id=group.id,
            user_id=user_id,
            role=MemberRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )
        session.add(membership)
    elif membership.status is MembershipStatus.ACTIVE:
        raise DomainError("already_member", "You are already a member of this group", 409)
    else:
        raise DomainError(
            "membership_removed",
            "An admin removed you from this group; the shared invite cannot restore access",
            403,
        )
    await session.flush()
    return group, membership


async def list_user_groups(
    session: AsyncSession, user_id: UUID
) -> list[tuple[Group, GroupMember, bool]]:
    rows = await repository.list_user_groups(session, user_id)
    results: list[tuple[Group, GroupMember, bool]] = []
    for group, membership in rows:
        if membership.status is MembershipStatus.ACTIVE:
            results.append((group, membership, False))
            continue
        from app.modules.trading.service import has_unsettled_group_position

        pending = await has_unsettled_group_position(
            session,
            group_id=group.id,
            user_id=user_id,
        )
        if pending:
            results.append((group, membership, True))
    return results


async def list_group_members(
    session: AsyncSession, *, group_id: UUID, requesting_user_id: UUID
) -> list[tuple[GroupMember, str]]:
    await require_membership(session, group_id, requesting_user_id)
    return await _members_with_names(
        session,
        await repository.list_members(session, group_id),
    )


async def remove_member(
    session: AsyncSession,
    *,
    group_id: UUID,
    member_user_id: UUID,
    requesting_user_id: UUID,
) -> tuple[GroupMember, str]:
    await require_admin(session, group_id, requesting_user_id)
    group = await repository.get_group(session, group_id)
    if group is None:
        raise DomainError("group_not_found", "Group not found", 404)
    if group.created_by == member_user_id:
        raise DomainError("creator_cannot_be_removed", "The group creator cannot be removed", 409)
    membership = await repository.get_membership(session, group_id, member_user_id)
    if membership is None or membership.status is MembershipStatus.REMOVED:
        raise DomainError("member_not_found", "Active group member not found", 404)
    membership.status = MembershipStatus.REMOVED
    membership.removed_at = datetime.now(UTC)
    await session.flush()
    return (await _members_with_names(session, [membership]))[0]


async def update_member_role(
    session: AsyncSession,
    *,
    group_id: UUID,
    member_user_id: UUID,
    role: MemberRole,
    requesting_user_id: UUID,
) -> tuple[GroupMember, str]:
    await require_admin(session, group_id, requesting_user_id)
    group = await repository.get_group(session, group_id)
    if group is None:
        raise DomainError("group_not_found", "Group not found", 404)
    if group.created_by == member_user_id and role is not MemberRole.ADMIN:
        raise DomainError(
            "creator_must_remain_admin",
            "The group creator must remain an admin",
            409,
        )
    membership = await require_membership(session, group_id, member_user_id)
    membership.role = role
    await session.flush()
    return (await _members_with_names(session, [membership]))[0]
