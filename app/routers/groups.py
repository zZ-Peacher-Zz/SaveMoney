from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_group
from app.models.group import FamilyGroup, GroupInvitation, GroupMember
from app.models.user import User
from app.schemas.groups import GroupPayload, InvitePayload
from app.security import current_user

router = APIRouter()


@router.get("/api/groups")
def list_groups(db: Session = Depends(get_db), user: User = Depends(current_user)):
    groups = db.scalars(select(FamilyGroup).join(GroupMember, GroupMember.group_id == FamilyGroup.id)
                        .where(GroupMember.user_id == user.id).order_by(FamilyGroup.id)).all()
    return [{"id": g.id, "name": g.name, "is_owner": g.owner_id == user.id} for g in groups]


@router.post("/api/groups", status_code=201)
def create_group(payload: GroupPayload, db: Session = Depends(get_db), user: User = Depends(current_user)):
    group = FamilyGroup(name=payload.name, owner_id=user.id)
    db.add(group)
    db.flush()
    db.add(GroupMember(group_id=group.id, user_id=user.id))
    db.commit()
    return {"id": group.id, "name": group.name, "is_owner": True}


@router.get("/api/groups/{group_id}/members")
def members(group_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    group = require_group(db, group_id, user)
    users = db.scalars(select(User).join(GroupMember, GroupMember.user_id == User.id)
                       .where(GroupMember.group_id == group_id).order_by(User.username)).all()
    return [{"id": u.id, "username": u.username, "is_owner": u.id == group.owner_id} for u in users]


@router.post("/api/groups/{group_id}/invitations", status_code=201)
def invite(group_id: int, payload: InvitePayload, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_group(db, group_id, user, owner=True)
    target = db.scalar(select(User).where(User.username == payload.username.strip().lower()))
    if target is None:
        raise HTTPException(404, "User not found")
    if db.get(GroupMember, (group_id, target.id)) or db.get(GroupInvitation, (group_id, target.id)):
        raise HTTPException(409, "User is already a member or invited")
    db.add(GroupInvitation(group_id=group_id, user_id=target.id))
    db.commit()
    return {"username": target.username}


@router.get("/api/invitations")
def invitations(db: Session = Depends(get_db), user: User = Depends(current_user)):
    groups = db.scalars(select(FamilyGroup).join(GroupInvitation, GroupInvitation.group_id == FamilyGroup.id)
                        .where(GroupInvitation.user_id == user.id)).all()
    return [{"group_id": g.id, "name": g.name} for g in groups]


@router.post("/api/invitations/{group_id}/accept", status_code=204)
def accept_invitation(group_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    invitation = db.get(GroupInvitation, (group_id, user.id))
    if invitation is None:
        raise HTTPException(404, "Invitation not found")
    db.add(GroupMember(group_id=group_id, user_id=user.id))
    db.delete(invitation)
    db.commit()


@router.delete("/api/invitations/{group_id}", status_code=204)
def decline_invitation(group_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    invitation = db.get(GroupInvitation, (group_id, user.id))
    if invitation is None:
        raise HTTPException(404, "Invitation not found")
    db.delete(invitation)
    db.commit()


@router.delete("/api/groups/{group_id}/members/{member_id}", status_code=204)
def remove_member(group_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    group = require_group(db, group_id, user, owner=True)
    if member_id == group.owner_id:
        raise HTTPException(400, "The owner cannot be removed")
    member = db.get(GroupMember, (group_id, member_id))
    if member is None:
        raise HTTPException(404, "Member not found")
    db.delete(member)
    db.commit()
