from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, SessionDependency
from app.modules.groups.models import Group, GroupMember, MembershipStatus
from app.modules.groups.schemas import (
    CreateGroupRequest,
    GroupResponse,
    JoinGroupRequest,
    MemberResponse,
    UpdateMemberRoleRequest,
)
from app.modules.groups.service import (
    create_group,
    join_group,
    list_group_members,
    list_user_groups,
    remove_member,
    update_member_role,
)

router = APIRouter(prefix="/groups", tags=["groups"])


def _member_response(membership: GroupMember, display_name: str) -> MemberResponse:
    return MemberResponse(
        user_id=membership.user_id,
        display_name=display_name,
        role=membership.role,
        status=membership.status,
        joined_at=membership.joined_at,
        removed_at=membership.removed_at,
    )


def _group_response(
    group: Group,
    membership: GroupMember,
    *,
    pending_settlement: bool = False,
) -> GroupResponse:
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        image_url=group.image_url,
        invite_code=(
            group.invite_code
            if membership.status is MembershipStatus.ACTIVE
            else None
        ),
        created_by=group.created_by,
        created_at=group.created_at,
        role=membership.role,
        membership_status=membership.status,
        pending_settlement=pending_settlement,
    )


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group_route(
    payload: CreateGroupRequest,
    session: SessionDependency,
    current_user: CurrentUser,
) -> GroupResponse:
    group, membership = await create_group(
        session,
        name=payload.name,
        description=payload.description,
        image_url=payload.image_url,
        creator_id=current_user.id,
    )
    return _group_response(group, membership)


@router.get("", response_model=list[GroupResponse])
async def list_groups_route(
    session: SessionDependency, current_user: CurrentUser
) -> list[GroupResponse]:
    return [
        _group_response(
            group,
            membership,
            pending_settlement=pending_settlement,
        )
        for group, membership, pending_settlement in await list_user_groups(
            session, current_user.id
        )
    ]


@router.post("/join", response_model=GroupResponse)
async def join_group_route(
    payload: JoinGroupRequest,
    session: SessionDependency,
    current_user: CurrentUser,
) -> GroupResponse:
    group, membership = await join_group(
        session,
        invite_code=payload.invite_code,
        user_id=current_user.id,
    )
    return _group_response(group, membership)


@router.get("/{group_id}/members", response_model=list[MemberResponse])
async def list_members_route(
    group_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> list[MemberResponse]:
    members = await list_group_members(
        session,
        group_id=group_id,
        requesting_user_id=current_user.id,
    )
    return [
        _member_response(membership, display_name)
        for membership, display_name in members
    ]


@router.delete("/{group_id}/members/{member_user_id}", response_model=MemberResponse)
async def remove_member_route(
    group_id: UUID,
    member_user_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> MemberResponse:
    membership, display_name = await remove_member(
        session,
        group_id=group_id,
        member_user_id=member_user_id,
        requesting_user_id=current_user.id,
    )
    return _member_response(membership, display_name)


@router.patch("/{group_id}/members/{member_user_id}", response_model=MemberResponse)
async def update_member_route(
    group_id: UUID,
    member_user_id: UUID,
    payload: UpdateMemberRoleRequest,
    session: SessionDependency,
    current_user: CurrentUser,
) -> MemberResponse:
    membership, display_name = await update_member_role(
        session,
        group_id=group_id,
        member_user_id=member_user_id,
        role=payload.role,
        requesting_user_id=current_user.id,
    )
    return _member_response(membership, display_name)
