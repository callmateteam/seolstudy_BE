from fastapi import HTTPException, status
from prisma import Prisma

from app.schemas.material import MaterialCreateRequest


async def get_materials(
    db: Prisma,
    subject: str | None = None,
    material_type: str | None = None,
):
    where: dict = {}
    if subject:
        where["subject"] = subject
    if material_type:
        where["type"] = material_type

    return await db.material.find_many(
        where=where,
        order={"createdAt": "desc"},
    )


async def get_material(db: Prisma, material_id: str):
    material = await db.material.find_unique(where={"id": material_id})
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MATERIAL_001", "message": "학습지를 찾을 수 없습니다"},
        )
    return material


async def create_material(db: Prisma, data: MaterialCreateRequest):
    return await db.material.create(
        data={
            "title": data.title,
            "type": data.type,
            "subject": data.subject,
            "abilityTags": data.abilityTags,
            "difficulty": data.difficulty,
            "contentUrl": data.contentUrl,
        }
    )
