"""Authenticated avatar upload, retrieval, and removal."""
from io import BytesIO
import warnings

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserAvatar
from app.security import current_user

router = APIRouter()
MAX_UPLOAD = 5 * 1024 * 1024


def prepare_avatar(data: bytes) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(400, "Please choose a PNG, JPEG or WebP image")
                if image.width * image.height > 16_000_000:
                    raise HTTPException(400, "Image is too large (maximum 16 megapixels)")
                image = ImageOps.exif_transpose(image).convert("RGBA")
                image = ImageOps.fit(image, (256, 256), method=Image.Resampling.LANCZOS)
                output = BytesIO()
                image.save(output, format="PNG")
                return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(400, "Invalid image. Please choose a PNG, JPEG or WebP image")


@router.put("/api/auth/avatar")
async def update_avatar(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "Image must be no larger than 5 MB")
    image = prepare_avatar(bytes(data))
    avatar = db.get(UserAvatar, user.id)
    if avatar is None:
        db.add(UserAvatar(user_id=user.id, image=image))
    else:
        avatar.image = image
    db.commit()
    return {"avatar_url": "/api/auth/avatar"}


@router.get("/api/auth/avatar")
def get_avatar(user: User = Depends(current_user), db: Session = Depends(get_db)):
    avatar = db.get(UserAvatar, user.id)
    if avatar is None:
        raise HTTPException(404, "Avatar not found")
    return Response(avatar.image, media_type="image/png", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.delete("/api/auth/avatar", status_code=204)
def delete_avatar(user: User = Depends(current_user), db: Session = Depends(get_db)):
    avatar = db.get(UserAvatar, user.id)
    if avatar is not None:
        db.delete(avatar)
        db.commit()
