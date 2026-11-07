from fastapi import APIRouter, Depends, HTTPException, Response
from app.database import MongoSession as Session

from app.database import get_db
from app.dependencies import require_group
from app.models.group import FamilyGroup, GroupInvitation, GroupMember
from app.models.user import User, UserAvatar
from app.schemas.groups import GroupPayload, InvitePayload
from app.security import current_user

router = APIRouter()


@router.get("/api/groups")
def list_groups(db: Session = Depends(get_db), user: User = Depends(current_user)):
    memberships = db.find(GroupMember, {"user_id": user.id})
    groups = db.find(FamilyGroup, {"id": {"$in": [m.group_id for m in memberships]}}, sort=[("id", 1)])
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
    memberships = db.find(GroupMember, {"group_id": group_id})
    user_ids = [m.user_id for m in memberships]
    users = db.find(User, {"id": {"$in": user_ids}}, sort=[("username", 1)])
    # Query IDs only, avoiding loading every member's image for the list.
    avatar_ids = set(db.values(UserAvatar, "user_id", {"user_id": {"$in": user_ids}}))
    return [{"id": u.id, "username": u.username, "is_owner": u.id == group.owner_id,
             "avatar_url": f"/api/groups/{group_id}/members/{u.id}/avatar" if u.id in avatar_ids else None}
            for u in users]


@router.get("/api/groups/{group_id}/members/{member_id}/avatar")
def member_avatar(group_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_group(db, group_id, user)
    if db.get(GroupMember, (group_id, member_id)) is None:
        raise HTTPException(404, "Member not found")
    avatar = db.get(UserAvatar, member_id)
    if avatar is None:
        raise HTTPException(404, "Avatar not found")
    return Response(avatar.image, media_type="image/png", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/api/groups/{group_id}/invitations", status_code=201)
def invite(group_id: int, payload: InvitePayload, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_group(db, group_id, user, owner=True)
    target = db.one(User, {"username": payload.username.strip().lower()})
    if target is None:
        raise HTTPException(404, "User not found")
    if db.get(GroupMember, (group_id, target.id)) or db.get(GroupInvitation, (group_id, target.id)):
        raise HTTPException(409, "User is already a member or invited")
    db.add(GroupInvitation(group_id=group_id, user_id=target.id))
    db.commit()
    return {"username": target.username}


@router.get("/api/invitations")
def invitations(db: Session = Depends(get_db), user: User = Depends(current_user)):
    invitations = db.find(GroupInvitation, {"user_id": user.id})
    groups = db.find(FamilyGroup, {"id": {"$in": [i.group_id for i in invitations]}})
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
