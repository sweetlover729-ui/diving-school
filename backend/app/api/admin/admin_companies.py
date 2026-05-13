"""
管理员-单位管理
"""

from fastapi import APIRouter

from .shared import *

router = APIRouter(prefix="", tags=["管理员-单位管理"])

# ============================
# 管理员-单位管理
# ============================
# ===== COMPANIES (2 endpoints) =====
# ============================

@router.get("/companies")
async def list_companies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """List Companies"""
    result = await db.execute(
        sql_text("""
            SELECT c.id, c.name, c.province, c.city, c.contact, c.phone,
                   (SELECT COUNT(*) FROM users u WHERE u.company_id = c.id AND u.is_active = true) as student_count
            FROM companies c
            ORDER BY c.id DESC
        """)
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/companies")
async def create_company(
    req: CompanyCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Create Company"""
    company = Company(
        name=req.name, province=req.province, city=req.city,
        contact=req.contact, phone=req.phone
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return {"id": company.id, "name": company.name}


@router.put("/companies/{company_id}")
async def update_company(
    company_id: int,
    req: CompanyCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Update Company"""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="单位不存在")
    for key in ["name", "province", "city", "contact", "phone"]:
        val = getattr(req, key, None)
        if val is not None:
            setattr(company, key, val)
    await db.commit()
    return {"success": True}


@router.delete("/companies/{company_id}")
async def delete_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    """Delete Company"""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="单位不存在")
    await db.delete(company)
    await db.commit()
    return {"success": True}


# ============================
# ============================

