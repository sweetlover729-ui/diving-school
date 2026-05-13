"""
入学文书 API - 潜水培训系统
包含4份文书的模版管理、学员填写、教练审批、PDF生成
"""
import base64
import os
import re
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, delete, select
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.admin.shared import require_admin, require_staff, require_student
from app.core.database import get_db
from app.core.docx_parser import DocumentParser
from app.models.class_system import (
    Class,
    ClassMember,
    DocumentResponse,
    DocumentTemplate,
    StudentDocumentStatus,
    User,
    UserRole,
)

router = APIRouter(tags=["入学文书"])

# ===== 常量 =====
SIGNATURE_DIR = "/Users/wjjmac/localserver/diving.school/backend/static/signatures/"
DOCUMENT_DIR = "/Users/wjjmac/localserver/diving.school/backend/static/documents/"

# ===== Pydantic Models =====

class FieldSchemaItem(BaseModel):
    id: str
    type: str
    label: str | None = None
    question: str | None = None
    required: bool | None = False
    options: list[str] | None = None
    field: str | None = None
    source: str | None = None


class TemplateUpdateRequest(BaseModel):
    fields_schema: list[dict] | None = None
    coach_choices: list[dict] | None = None
    course_choices: list[dict] | None = None
    institution_name: str | None = None
    is_required: bool | None = None
    is_active: bool | None = None


class DocumentSubmitRequest(BaseModel):
    answers: dict
    signature_base64: str | None = None  # base64 PNG 数据


class RejectRequest(BaseModel):
    reason: str


class TemplateResponse(BaseModel):
    id: int
    name: str
    doc_type: str
    description: str | None
    static_html: str | None
    fields_schema: list[dict] | None
    coach_choices: list[dict] | None
    course_choices: list[dict] | None
    institution_name: str | None
    is_required: bool
    is_active: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    template_id: int
    template_name: str
    doc_type: str
    status: str
    answers: dict | None
    submitted_at: datetime | None
    review_comment: str | None
    is_required: bool

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(BaseModel):
    template: TemplateResponse
    response: dict | None
    status: str
    student_profile: dict | None = None
    courses: list[dict] | None = None  # 课程列表（用于学员选择）
    instructors: list[dict] | None = None  # 教练列表（用于学员选择）
    institution_choices: list[dict] | None = None  # 潜水培训机构列表（用于学员选择）
    class_info: dict | None = None  # 班级信息（用于 readonly_static 字段）


class ResponseListItem(BaseModel):
    id: int
    student_id: int
    student_name: str
    template_id: int
    template_name: str
    doc_type: str
    status: str
    submitted_at: datetime | None
    class_id: int | None
    class_name: str | None

    model_config = ConfigDict(from_attributes=True)


class ResponseDetail(BaseModel):
    id: int
    student_id: int
    student_name: str
    student_id_card: str | None
    student_phone: str | None
    template_id: int
    template_name: str
    doc_type: str
    answers: dict | None
    signature_image: str | None
    snapshot_name: str | None
    snapshot_id_number: str | None
    snapshot_phone: str | None
    snapshot_instructor_name: str | None
    status: str
    submitted_at: datetime | None
    reviewed_by: int | None
    review_comment: str | None
    reviewed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ===== 工具函数 =====

def mask_id_number(id_number: str) -> str:
    """脱敏身份证号（中间8位）"""
    if not id_number or len(id_number) < 10:
        return id_number
    return id_number[:6] + "********" + id_number[14:]


def calc_age_from_id_card(id_card: str) -> int | None:
    """从身份证号推算年龄"""
    if not id_card or len(id_card) != 18:
        return None
    try:
        birth_year = int(id_card[6:10])
        birth_month = int(id_card[10:12])
        birth_day = int(id_card[12:14])
        now = datetime.now()
        age = now.year - birth_year
        if (now.month, now.day) < (birth_month, birth_day):
            age -= 1
        return age
    except (ValueError, IndexError):
        return None


def extract_birth_date_from_id(id_card: str) -> str | None:
    """从身份证号提取出生日期"""
    if not id_card or len(id_card) != 18:
        return None
    try:
        year = id_card[6:10]
        month = id_card[10:12]
        day = id_card[12:14]
        return f"{year}年{month}月{day}日"
    except (ValueError, IndexError):
        return None


async def ensure_directories():
    """确保目录存在"""
    os.makedirs(SIGNATURE_DIR, exist_ok=True)
    os.makedirs(DOCUMENT_DIR, exist_ok=True)


async def save_signature_image(student_id: int, template_id: int, base64_data: str) -> str:
    """保存签名图片"""
    await ensure_directories()

    # 创建学员目录
    student_dir = os.path.join(SIGNATURE_DIR, str(student_id))
    os.makedirs(student_dir, exist_ok=True)

    # 解析 base64
    if base64_data.startswith("data:image"):
        base64_data = base64_data.split(",")[1]

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{template_id}_{timestamp}.png"
    filepath = os.path.join(student_dir, filename)

    # 保存文件
    image_data = base64.b64decode(base64_data)
    with open(filepath, "wb") as f:
        f.write(image_data)

    # 返回相对路径（用于数据库存储）
    return f"signatures/{student_id}/{filename}"


async def get_student_class_info(db: AsyncSession, student_id: int) -> dict | None:
    """获取学员所属班级信息"""
    result = await db.execute(
        select(Class, ClassMember)
        .join(ClassMember, Class.id == ClassMember.class_id)
        .where(ClassMember.user_id == student_id)
        .options(selectinload(Class.instructor))
    )
    row = result.first()
    if row:
        cls, member = row
        return {
            "class_id": cls.id,
            "class_name": cls.name,
            "instructor_id": cls.instructor_id,
            "instructor_name": cls.instructor.name if cls.instructor else None,
            "start_time": cls.start_time,
            "end_time": cls.end_time,
            "courses": cls.courses or []  # 班级分配的课程
        }
    return None


async def get_instructor_students(db: AsyncSession, instructor_id: int) -> list[int]:
    """获取教练所带班级的所有学员ID
    
    教练通过 class_members 表关联（role='INSTRUCTOR'），
    然后查询同一班级的学员（role='STUDENT'）
    """
    # 1. 获取教练所在的班级ID列表
    class_result = await db.execute(
        select(ClassMember.class_id)
        .where(
            and_(
                ClassMember.user_id == instructor_id,
                ClassMember.role == UserRole.INSTRUCTOR
            )
        )
    )
    class_ids = [row[0] for row in class_result.all()]

    if not class_ids:
        return []

    # 2. 查询这些班级的所有学员ID
    student_result = await db.execute(
        select(ClassMember.user_id)
        .where(
            and_(
                ClassMember.class_id.in_(class_ids),
                ClassMember.role == UserRole.STUDENT
            )
        )
    )
    return [row[0] for row in student_result.all()]


# ===== 模版初始化数据 =====

DEFAULT_TEMPLATES = [
    {
        "name": "潜水员健康声明书暨健康调查问卷",
        "doc_type": "health",
        "description": "用于评估学员潜水健康状况",
        "sort_order": 1,
        "fields_schema": [
            {"id": "q1", "type": "yesno", "question": "是否已怀孕或计划怀孕", "required": True},
            {"id": "q2", "type": "yesno", "question": "眼前发黑或昏厥（完全或部分丧失意识）", "required": True},
            {"id": "q3", "type": "yesno", "question": "目前正在服用处方药吗（节育药品除外）", "required": True},
            {"id": "q4", "type": "yesno", "question": "时常或严重受到晕动病（晕车、晕船等）侵扰", "required": True},
            {"id": "q5", "type": "yesno", "question": "是否已过45岁并存在以下情况：吸烟、胆固醇过高、有心脏病或中风家族病史、无法进行适度活动", "required": True},
            {"id": "q6", "type": "yesno", "question": "经常背部疼痛", "required": True},
            {"id": "q7", "type": "yesno", "question": "背部或脊椎是否进行过手术", "required": True},
            {"id": "q8", "type": "yesno", "question": "是否患有或曾经患有心脏病", "required": True},
            {"id": "q9", "type": "yesno", "question": "是否患有糖尿病", "required": True},
            {"id": "q10", "type": "yesno", "question": "是否患有高血压或使用药物控制血压过高", "required": True},
            {"id": "q11", "type": "yesno", "question": "是否患有哮喘、心肌梗塞、心绞痛、心脏或血管手术", "required": True},
            {"id": "q12", "type": "yesno", "question": "是否有肺部疾病、气胸、周期性复发的耳部疾病", "required": True},
            {"id": "q13", "type": "yesno", "question": "是否有精神或心理问题（如恐慌症、幽闭恐惧症或广场恐惧症）", "required": True},
            {"id": "agree", "type": "agreement_checkbox", "required": True, "label": "同意声明"},
            {"id": "signature", "type": "signature", "required": True, "label": "手写签名"},
            {"id": "id_number", "type": "id_number", "required": True, "label": "身份证号码"},
            {"id": "phone", "type": "phone", "required": True, "label": "电话号码"}
        ],
        "static_html": """
        潜水员健康声明书暨健康调查问卷

        请仔细阅读以下健康问题，如实回答。如果对任何问题的回答为"是"，您需要寻求医生的进一步评估。

        潜水是一项有一定风险的活动，良好的健康状况是安全潜水的前提。
        """
    },
    {
        "name": "一般免责和风险承担协议书",
        "doc_type": "waiver",
        "description": "学员确认了解并承担潜水风险",
        "sort_order": 2,
        "fields_schema": [
            {"id": "course_name", "type": "select_course", "required": True, "label": "参加课程名称"},
            {"id": "student_name", "type": "profile_auto", "field": "name", "required": True, "label": "学员姓名"},
            {"id": "instructor_name", "type": "select_instructor", "required": True, "label": "教练姓名"},
            {"id": "instructor_code", "type": "instructor_auto", "source": "instructor_name", "required": True, "label": "教练编号"},
            {"id": "institution", "type": "profile_institution", "required": True, "label": "潜水培训机构"},
            {"id": "dive_site", "type": "text", "required": True, "label": "潜水场所"},
            {"id": "agree", "type": "agreement_checkbox", "required": True, "label": "同意声明"},
            {"id": "signature", "type": "signature", "required": True, "label": "手写签名"},
            {"id": "id_number", "type": "id_number", "required": True, "label": "身份证号码"},
            {"id": "phone", "type": "phone", "required": True, "label": "电话号码"},
            {"id": "date", "type": "date_auto", "required": True, "label": "填写日期"}
        ],
        "static_html": """
        一般免责和风险承担协议书

        本人自愿参加潜水培训活动，充分了解潜水运动存在的风险，包括但不限于：溺水、气压伤、减压病、海洋生物伤害等。

        本人声明：身体健康，无任何不适宜潜水的疾病或身体状况。

        本人承诺：遵守潜水安全规则，听从教练指导，对自身安全负责。
        """
    },
    {
        "name": "中国潜水同意书",
        "doc_type": "agreement",
        "description": "中国潜水活动标准同意书",
        "sort_order": 3,
        "fields_schema": [
            {"id": "unit_name", "type": "readonly_static", "label": "单位名称", "required": False},
            {"id": "course_session", "type": "readonly_static", "label": "第几期", "required": False},
            {"id": "course_start", "type": "readonly_static", "label": "开课日期", "required": False},
            {"id": "course_end", "type": "readonly_static", "label": "结束日期", "required": False},
            {"id": "name", "type": "profile_auto", "field": "name", "required": True, "label": "姓名（中文）"},
            {"id": "name_pinyin", "type": "text", "required": False, "label": "姓名（拼音）"},
            {"id": "gender", "type": "radio", "options": ["男", "女"], "required": True, "label": "性别"},
            {"id": "birth_date", "type": "id_auto", "required": True, "label": "出生年月"},
            {"id": "occupation", "type": "text", "required": False, "label": "职业"},
            {"id": "position", "type": "text", "required": False, "label": "职务"},
            {"id": "phone", "type": "phone", "required": True, "label": "手机"},
            {"id": "work_address", "type": "text", "required": False, "label": "工作地址"},
            {"id": "work_phone", "type": "phone", "required": False, "label": "工作电话"},
            {"id": "home_address", "type": "text", "required": False, "label": "自宅地址"},
            {"id": "home_phone", "type": "phone", "required": False, "label": "自宅电话"},
            {"id": "emergency_contact", "type": "text", "required": True, "label": "紧急联络人"},
            {"id": "emergency_relation", "type": "text", "required": True, "label": "关系"},
            {"id": "emergency_address", "type": "text", "required": False, "label": "联络人地址"},
            {"id": "emergency_phone", "type": "phone", "required": True, "label": "联络人电话"},
            {"id": "diving_exp", "type": "radio", "options": ["有", "无"], "required": True, "label": "是否曾学习潜水"},
            {"id": "diving_level", "type": "text", "required": False, "label": "潜水级别/证照"},
            {"id": "guardian_signature", "type": "guardian_signature", "required": False, "label": "亲属/监护人签名（未成年者填写）"}
        ],
        "static_html": """
        中国潜水同意书

        本同意书用于记录学员的基本信息、紧急联系人及潜水经历，确保培训过程的安全与合规。

        未成年学员须由监护人签字确认。
        """
    },
    {
        "name": "潜水（应急救援）培训学员问卷调查",
        "doc_type": "questionnaire",
        "description": "学员背景及能力调查",
        "sort_order": 4,
        "fields_schema": [
            {"id": "name", "type": "profile_auto", "field": "name", "required": True, "label": "姓名（中文+拼音）"},
            {"id": "age", "type": "text", "required": True, "label": "年龄"},
            {"id": "gender", "type": "select", "options": ["男", "女"], "required": True, "label": "性别"},
            {"id": "education", "type": "select", "options": ["初中", "中技/高中", "大专", "本科", "硕士", "博士"], "required": True, "label": "教育程度"},
            {"id": "phone", "type": "phone", "required": True, "label": "个人电话"},
            {"id": "email", "type": "text", "required": False, "label": "电子邮箱"},
            {"id": "q_diving_knowledge", "type": "radio", "options": ["A、是", "B、否"], "required": True, "label": "是否对潜水有认知"},
            {"id": "q_science_background", "type": "multi_checkbox", "options": ["A、数学", "B、物理", "C、化学", "D、生物"], "required": False, "label": "曾参与的理科科目"},
            {"id": "q_swimming", "type": "radio", "options": ["A、曾参加比赛", "B、熟练", "C、一般", "D、刚学会", "E、还不会"], "required": True, "label": "是否懂得游泳"},
            {"id": "q_strokes", "type": "multi_checkbox", "options": ["A、蛙泳", "B、自由泳", "C、蝶泳", "D、蹼泳", "E、其它泳姿"], "required": False, "label": "懂的泳姿"},
            {"id": "q_certified_diver", "type": "radio", "options": ["A、是", "B、否"], "required": True, "label": "是否持有潜水员资格"},
            {"id": "q_cert_type", "type": "text", "required": False, "label": "潜水资格类别及最高证书"},
            {"id": "q_scuba_exp", "type": "radio", "options": ["A、是", "B、否"], "required": True, "label": "是否体验过水肺潜水"},
            {"id": "q_snorkel_exp", "type": "radio", "options": ["A、是", "B、否"], "required": True, "label": "是否体验过浮潜"},
            {"id": "q_water_ability", "type": "radio", "options": ["A、非常好", "B、好", "C、一般", "D、刚学会", "E、还不会"], "required": True, "label": "水性如何"},
            {"id": "q_welding_exp", "type": "radio_text", "options": ["A、有", "B、没有"], "required": False, "label": "电焊接经验"},
            {"id": "q_cutting_exp", "type": "radio_text", "options": ["A、有", "B、没有"], "required": False, "label": "金属热切割经验"},
            {"id": "q_underwater_exp", "type": "radio_text", "options": ["A、有", "B、没有"], "required": False, "label": "水下作业经验"},
            {"id": "q_drowning_exp", "type": "radio_text", "options": ["A、有", "B、没有"], "required": False, "label": "溺水经历"},
            {"id": "q_fear_water", "type": "radio", "options": ["A、有", "B、没有", "C、不知道"], "required": True, "label": "是否恐水"},
            {"id": "q_fear_dark", "type": "radio", "options": ["A、有", "B、没有", "C、不一定"], "required": True, "label": "是否怕黑"},
            {"id": "q_faced_corpse", "type": "radio", "options": ["A、有", "B、没有"], "required": True, "label": "是否面对过尸体"},
            {"id": "q_fear_corpse", "type": "radio", "options": ["A、有", "B、没有", "C、不一定"], "required": True, "label": "面对尸体会否恐惧"},
            {"id": "q_vision", "type": "multi_text", "options": ["A、近视", "B、远视", "C、近视+远视", "D、正常", "E、散光"], "required": False, "label": "视力情况"},
            {"id": "q_swim500", "type": "text", "required": False, "label": "500米游泳时间（成绩）"},
            {"id": "q_treading", "type": "text", "required": False, "label": "踩水时间"},
            {"id": "height", "type": "text", "required": False, "label": "身高（cm）"},
            {"id": "weight", "type": "text", "required": False, "label": "体重（kg）"},
            {"id": "shoe_size", "type": "text", "required": False, "label": "鞋码"},
            {"id": "extra_qualifications", "type": "textarea", "required": False, "label": "其他个人技能或资格证书"},
            {"id": "signature", "type": "signature", "required": True},
            {"id": "date", "type": "date_auto", "required": True}
        ],
        "static_html": """
        潜水（应急救援）培训学员问卷调查

        本调查用于了解学员的基本情况、游泳能力、潜水经历及心理状态，以便开展针对性培训。

        请如实填写，如有不实，可能影响培训效果及安全。
        """
    }
]


async def init_templates(db: AsyncSession) -> list[DocumentTemplate]:
    """初始化4份模版"""
    result = await db.execute(select(DocumentTemplate))
    existing = result.scalars().all()

    if len(existing) >= 4:
        return list(existing)

    # 创建缺失的模版
    created = []
    for template_data in DEFAULT_TEMPLATES:
        # 检查是否已存在
        existing_template = next(
            (t for t in existing if t.doc_type == template_data["doc_type"]),
            None
        )
        if existing_template:
            created.append(existing_template)
            continue

        template = DocumentTemplate(
            name=template_data["name"],
            doc_type=template_data["doc_type"],
            description=template_data.get("description"),
            static_html=template_data.get("static_html", ""),
            fields_schema=template_data.get("fields_schema", []),
            sort_order=template_data.get("sort_order", 0),
            is_required=True,
            is_active=True
        )
        db.add(template)
        created.append(template)

    await db.commit()
    for t in created:
        await db.refresh(t)

    return created


# ===== 管理员接口 =====

@router.get("/admin/document-templates", response_model=list[TemplateResponse])
async def get_templates(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_staff)
):
    """管理员获取/初始化4份文书模版列表"""

    templates = await init_templates(db)
    return templates


@router.get("/admin/document-templates/{template_id}", response_model=TemplateResponse)
async def get_template_detail(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_staff)
):
    """获取单个文书模版详情"""

    result = await db.execute(
        select(DocumentTemplate).where(DocumentTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模版不存在")

    return TemplateResponse.model_validate(template)


@router.put("/admin/document-templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    request: TemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """管理员更新模版"""

    result = await db.execute(
        select(DocumentTemplate).where(DocumentTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模版不存在")

    if request.fields_schema is not None:
        template.fields_schema = request.fields_schema
    if request.coach_choices is not None:
        template.coach_choices = request.coach_choices
    if request.course_choices is not None:
        template.course_choices = request.course_choices
    if request.institution_name is not None:
        template.institution_name = request.institution_name
    if request.is_required is not None:
        template.is_required = request.is_required
    if request.is_active is not None:
        template.is_active = request.is_active

    template.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(template)

    return template


@router.post("/admin/document-templates/parse", response_model=dict)
async def parse_document_template(
    file: UploadFile = File(...),
    current_user = Depends(require_admin)
):
    """上传DOCX文件并自动解析表单字段"""

    # 验证文件类型
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="只支持DOCX文件")

    # 保存临时文件
    temp_path = f"/tmp/{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 解析文档
        parser = DocumentParser(temp_path)
        schema = parser.generate_schema()

        return {
            "success": True,
            "filename": file.filename,
            "schema": schema
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/admin/document-templates", response_model=TemplateResponse)
async def create_template(
    name: str,
    doc_type: str,
    description: str | None = None,
    is_required: bool = True,
    file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """创建新文书模板（支持上传DOCX自动解析）"""

    fields_schema = None

    # 如果上传了文件，自动解析
    if file and file.filename.endswith('.docx'):
        temp_path = f"/tmp/{file.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            parser = DocumentParser(temp_path)
            schema = parser.generate_schema()
            fields_schema = schema.get("fields", [])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # 创建模板
    template = DocumentTemplate(
        name=name,
        doc_type=doc_type,
        description=description,
        fields_schema=fields_schema or [],
        is_required=is_required,
        is_active=True,
        sort_order=0,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return template


@router.delete("/admin/document-templates/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """删除文书模板"""

    result = await db.execute(
        select(DocumentTemplate).where(DocumentTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模版不存在")

    try:
        # 先删除关联的文书填写记录
        await db.execute(delete(DocumentResponse).where(DocumentResponse.template_id == template_id))
        await db.delete(template)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"删除失败：{str(e)}")

    return {"success": True, "message": "删除成功"}


# ===== 学员接口 =====

@router.get("/students/me/documents", response_model=list[DocumentStatusResponse])
async def get_my_documents(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_student)
):
    """学员获取自己班级关联的文书填写状态"""

    # 查找学员所属班级
    member_result = await db.execute(
        select(ClassMember).where(ClassMember.user_id == current_user.id)
    )
    membership = member_result.scalars().first()
    if not membership:
        return []  # 未分配班级，无文书

    # 获取班级关联的文书模板ID（class_documents表暂未创建，兜底空列表）
    try:
        async with db.begin_nested():
            cd_result = await db.execute(
                sql_text("SELECT template_id FROM class_documents WHERE class_id = :cid"),
                {"cid": membership.class_id}
            )
            template_ids = [row[0] for row in cd_result.fetchall() if row[0]]
    except Exception:
        template_ids = []

    if not template_ids:
        return []  # 班级无关联文书

    # 获取这些模板
    templates_result = await db.execute(
        select(DocumentTemplate).where(DocumentTemplate.id.in_(template_ids))
    )
    templates = templates_result.scalars().all()

    # 获取所有填写记录
    result = await db.execute(
        select(DocumentResponse)
        .where(DocumentResponse.student_id == current_user.id)
    )
    responses = {r.template_id: r for r in result.scalars().all()}

    # 构建返回列表
    status_list = []
    for template in templates:
        response = responses.get(template.id)

        # 脱敏处理 answers
        masked_answers = None
        if response and response.answers:
            masked_answers = response.answers.copy()
            # 脱敏身份证号
            if "id_number" in masked_answers:
                masked_answers["id_number"] = mask_id_number(masked_answers["id_number"])

        status_list.append(DocumentStatusResponse(
            template_id=template.id,
            template_name=template.name,
            doc_type=template.doc_type,
            status=response.status if response else "pending",
            answers=masked_answers,
            submitted_at=response.submitted_at if response else None,
            review_comment=response.review_comment if response else None,
            is_required=template.is_required,
        ))

    return status_list


@router.get("/students/me/documents/{template_id}", response_model=DocumentDetailResponse)
async def get_my_document_detail(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_student)
):
    """学员获取单份文书详情"""

    # 获取模版
    result = await db.execute(
        select(DocumentTemplate).where(DocumentTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模版不存在")

    # 获取填写记录
    result = await db.execute(
        select(DocumentResponse)
        .where(
            and_(
                DocumentResponse.student_id == current_user.id,
                DocumentResponse.template_id == template_id
            )
        )
    )
    response = result.scalar_one_or_none()

    # 构建返回
    response_data = None
    status = "pending"
    if response:
        status = response.status
        # 脱敏身份证号
        masked_answers = response.answers.copy() if response.answers else {}
        if "id_number" in masked_answers:
            masked_answers["id_number"] = mask_id_number(masked_answers["id_number"])

        response_data = {
            "id": response.id,
            "answers": masked_answers,
            "signature_image": response.signature_image,
            "status": response.status,
            "submitted_at": response.submitted_at,
            "review_comment": response.review_comment
        }

    # 获取课程列表：优先从班级分配获取，其次从全局课程设置获取
    course_list = []

    # 1. 先找学员所在的班级
    from app.models.class_system import Class, ClassMember
    result = await db.execute(
        select(ClassMember).where(ClassMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()

    if member:
        # 2. 获取班级分配的课程
        cls = await db.get(Class, member.class_id)
        if cls and cls.courses:
            # 只返回启用状态的课程
            course_list = [c for c in cls.courses if c.get("is_active", True)]

    # 3. 如果班级没有分配课程，fallback到全局课程设置
    if not course_list:
        courses_result = await db.execute(
            select(DocumentTemplate).where(DocumentTemplate.doc_type == "waiver")
        )
        course_template = courses_result.scalar_one_or_none()
        if course_template and course_template.course_choices:
            course_list = [c for c in course_template.course_choices if c.get("is_active", True)]

    # 获取教练列表：从班级关联的教练获取，其次从全局教练设置获取
    instructor_list = []

    if member:
        # 从 class_members 表查询该班级的教练
        from app.models.class_system import ClassMember
        from app.models.class_system import User as MemberUser
        cm_result = await db.execute(
            select(ClassMember).where(
                and_(
                    ClassMember.class_id == member.class_id,
                    ClassMember.role == UserRole.INSTRUCTOR
                )
            )
        )
        cm = cm_result.scalar_one_or_none()
        if cm:
            instructor_user = await db.get(MemberUser, cm.user_id)
            if instructor_user:
                # 获取教练所属单位名称
                company_name = None
                if instructor_user.company_id:
                    from app.models.class_system import Company
                    company = await db.get(Company, instructor_user.company_id)
                    if company:
                        company_name = company.name
                instructor_list = [{
                    "id": instructor_user.id,
                    "name": instructor_user.name,
                    "code": instructor_user.instructor_code or str(instructor_user.id),
                    "institution": instructor_user.training_institution or company_name or "",
                    "phone": instructor_user.phone or "",
                }]

    # 如果班级没有教练，fallback到全局教练设置（coach_choices）
    if not instructor_list:
        if template.coach_choices:
            instructor_list = [c for c in template.coach_choices if c.get("is_active", True)]

    # 获取潜水培训机构选项（优先从教练所属单位获取，其次查公司表）
    institution_choices = []
    from app.models.class_system import Company
    companies_result = await db.execute(select(Company))
    companies = companies_result.scalars().all()
    institution_choices = [{"id": c.id, "name": c.name} for c in companies]

    # 获取班级信息（用于 readonly_static 字段显示）
    class_info_data = None
    if member:
        cls = await db.get(Class, member.class_id)
        if cls:
            # 获取单位名称（从班级名称，Class模型没有company_id字段）
            unit_name = cls.name  # 默认使用班级名称

            class_info_data = {
                "class_id": cls.id,
                "class_name": cls.name,
                "unit_name": unit_name,
                "course_session": "",  # 第几期 - Class模型没有session_number字段
                "course_start": cls.start_time.strftime("%Y-%m-%d") if cls.start_time else None,
                "course_end": cls.end_time.strftime("%Y-%m-%d") if cls.end_time else None,
            }

    return DocumentDetailResponse(
        template=TemplateResponse.from_orm(template),
        response=response_data,
        status=status,
        student_profile={
            "name": current_user.name,
            "id_card": current_user.id_card,
            "phone": current_user.phone
        },
        courses=course_list,
        instructors=instructor_list,
        institution_choices=institution_choices,
        class_info=class_info_data
    )


@router.post("/students/me/documents/{template_id}")
async def submit_document(
    template_id: int,
    request: DocumentSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_student)
):
    """学员提交/更新填写内容"""

    # 获取模版
    result = await db.execute(
        select(DocumentTemplate).where(DocumentTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模版不存在")

    # 检查是否已有填写记录
    result = await db.execute(
        select(DocumentResponse)
        .where(
            and_(
                DocumentResponse.student_id == current_user.id,
                DocumentResponse.template_id == template_id
            )
        )
    )
    response = result.scalar_one_or_none()

    # 处理签名图片
    signature_path = None
    if request.signature_base64:
        signature_path = await save_signature_image(
            current_user.id,
            template_id,
            request.signature_base64
        )

    # 获取学员班级信息（用于快照教练）
    class_info = await get_student_class_info(db, current_user.id)

    # 准备快照数据
    snapshot_name = request.answers.get("name") or current_user.name
    snapshot_id_number = request.answers.get("id_number") or current_user.id_card
    snapshot_phone = request.answers.get("phone") or current_user.phone
    snapshot_instructor_id = class_info.get("instructor_id") if class_info else None
    snapshot_instructor_name = class_info.get("instructor_name") if class_info else None

    # 自动处理特殊字段
    answers = request.answers.copy()

    # id_auto: 从身份证提取出生日期
    for field in (template.fields_schema or []):
        if field.get("type") == "id_auto" and field.get("id") not in answers:
            id_number = answers.get("id_number") or current_user.id_card
            if id_number:
                answers[field["id"]] = extract_birth_date_from_id(id_number)

        # date_auto: 自动填入当前日期
        if field.get("type") == "date_auto" and field.get("id") not in answers:
            answers[field["id"]] = datetime.now().strftime("%Y年%m月%d日")

        # profile_auto: 从用户信息自动填充
        if field.get("type") == "profile_auto":
            field_name = field.get("field")
            if field_name == "name" and field.get("id") not in answers:
                answers[field["id"]] = current_user.name

        # select_course: 自动填入班级分配的课程（学员不能自选）
        if field.get("type") == "select_course" and field.get("id") not in answers:
            if class_info and class_info.get("courses"):
                # 班级有分配课程，取第一个作为文书记录
                courses = class_info["courses"]
                if len(courses) == 1:
                    answers[field["id"]] = courses[0]["name"]
                else:
                    answers[field["id"]] = " / ".join(c["name"] for c in courses)

    if response:
        # 更新现有记录
        response.answers = answers
        if signature_path:
            response.signature_image = signature_path
        response.snapshot_name = snapshot_name
        response.snapshot_id_number = snapshot_id_number
        response.snapshot_phone = snapshot_phone
        response.snapshot_instructor_id = snapshot_instructor_id
        response.snapshot_instructor_name = snapshot_instructor_name
        response.status = "submitted"
        response.submitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        response.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        # 创建新记录
        response = DocumentResponse(
            student_id=current_user.id,
            template_id=template_id,
            answers=answers,
            signature_image=signature_path,
            snapshot_name=snapshot_name,
            snapshot_id_number=snapshot_id_number,
            snapshot_phone=snapshot_phone,
            snapshot_instructor_id=snapshot_instructor_id,
            snapshot_instructor_name=snapshot_instructor_name,
            status="submitted",
            submitted_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(response)

    await db.commit()
    await db.refresh(response)

    return {"success": True, "response_id": response.id, "message": "提交成功"}


# ===== 教练/管理员接口 =====

@router.get("/admin/document-responses", response_model=list[ResponseListItem])
async def get_document_responses(
    class_id: int | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_staff)
):
    """教练/管理员获取学员文书填写列表"""

    # 构建基础查询
    query = (
        select(DocumentResponse, DocumentTemplate, User)
        .join(DocumentTemplate, DocumentResponse.template_id == DocumentTemplate.id)
        .join(User, DocumentResponse.student_id == User.id)
    )

    # 教练只能看自己班级的学员
    if current_user.role == UserRole.INSTRUCTOR:
        student_ids = await get_instructor_students(db, current_user.id)
        if not student_ids:
            return []
        query = query.where(DocumentResponse.student_id.in_(student_ids))

    # 筛选状态
    if status:
        query = query.where(DocumentResponse.status == status)

    # 筛选班级
    if class_id:
        # 获取该班级的所有学员
        class_students = await db.execute(
            select(ClassMember.user_id)
            .where(ClassMember.class_id == class_id)
        )
        student_ids = [s[0] for s in class_students.all()]
        if student_ids:
            query = query.where(DocumentResponse.student_id.in_(student_ids))
        else:
            return []

    result = await db.execute(query)
    rows = result.all()

    # 获取学员班级信息
    response_list = []
    for response, template, student in rows:
        # 获取学员所属班级
        class_info = await get_student_class_info(db, student.id)

        response_list.append(ResponseListItem(
            id=response.id,
            student_id=student.id,
            student_name=student.name,
            template_id=template.id,
            template_name=template.name,
            doc_type=template.doc_type,
            status=response.status,
            submitted_at=response.submitted_at,
            class_id=class_info.get("class_id") if class_info else None,
            class_name=class_info.get("class_name") if class_info else None
        ))

    return response_list


@router.get("/admin/document-responses/{response_id}", response_model=ResponseDetail)
async def get_response_detail(
    response_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_staff)
):
    """获取单个填写详情"""

    result = await db.execute(
        select(DocumentResponse, DocumentTemplate, User)
        .join(DocumentTemplate, DocumentResponse.template_id == DocumentTemplate.id)
        .join(User, DocumentResponse.student_id == User.id)
        .where(DocumentResponse.id == response_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")

    response, template, student = row

    # 教练权限检查
    if current_user.role == UserRole.INSTRUCTOR:
        student_ids = await get_instructor_students(db, current_user.id)
        if student.id not in student_ids:
            raise HTTPException(status_code=403, detail="无权访问该学员")

    return ResponseDetail(
        id=response.id,
        student_id=student.id,
        student_name=student.name,
        student_id_card=mask_id_number(student.id_card) if student.id_card else None,
        student_phone=student.phone,
        template_id=template.id,
        template_name=template.name,
        doc_type=template.doc_type,
        answers=response.answers,
        signature_image=response.signature_image,
        snapshot_name=response.snapshot_name,
        snapshot_id_number=mask_id_number(response.snapshot_id_number) if response.snapshot_id_number else None,
        snapshot_phone=response.snapshot_phone,
        snapshot_instructor_name=response.snapshot_instructor_name,
        status=response.status,
        submitted_at=response.submitted_at,
        reviewed_by=response.reviewed_by,
        review_comment=response.review_comment,
        reviewed_at=response.reviewed_at
    )


@router.post("/admin/document-responses/{response_id}/approve")
async def approve_response(
    response_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_staff)
):
    """教练/管理员批准"""

    result = await db.execute(
        select(DocumentResponse)
        .where(DocumentResponse.id == response_id)
    )
    response = result.scalar_one_or_none()
    if not response:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 教练权限检查
    if current_user.role == UserRole.INSTRUCTOR:
        student_ids = await get_instructor_students(db, current_user.id)
        if response.student_id not in student_ids:
            raise HTTPException(status_code=403, detail="无权访问该学员")

    # 检查该学员4份文书是否全部已提交
    all_responses = await db.execute(
        select(DocumentResponse)
        .where(DocumentResponse.student_id == response.student_id)
    )
    responses = all_responses.scalars().all()

    # 获取所有模版数量
    templates = await init_templates(db)

    # 检查是否全部提交
    all_submitted = len(responses) >= len(templates) and all(
        r.status == "submitted" or r.status == "approved" for r in responses
    )

    # 更新该记录状态
    response.status = "approved"
    response.reviewed_by = current_user.id
    response.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # 如果全部提交，更新 StudentDocumentStatus
    if all_submitted:
        # 获取或创建 StudentDocumentStatus
        status_result = await db.execute(
            select(StudentDocumentStatus)
            .where(StudentDocumentStatus.student_id == response.student_id)
        )
        doc_status = status_result.scalar_one_or_none()

        if doc_status:
            doc_status.overall_locked = False
            doc_status.approved_by = current_user.id
            doc_status.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            doc_status = StudentDocumentStatus(
                student_id=response.student_id,
                overall_locked=False,
                approved_by=current_user.id,
                approved_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db.add(doc_status)

    await db.commit()

    return {"success": True, "message": "批准成功", "all_submitted": all_submitted}


@router.post("/admin/document-responses/{response_id}/reject")
async def reject_response(
    response_id: int,
    request: RejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_staff)
):
    """驳回（教练/管理员填写驳回理由）"""

    result = await db.execute(
        select(DocumentResponse)
        .where(DocumentResponse.id == response_id)
    )
    response = result.scalar_one_or_none()
    if not response:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 教练权限检查
    if current_user.role == UserRole.INSTRUCTOR:
        student_ids = await get_instructor_students(db, current_user.id)
        if response.student_id not in student_ids:
            raise HTTPException(status_code=403, detail="无权访问该学员")

    # 更新状态
    response.status = "rejected"
    response.reviewed_by = current_user.id
    response.review_comment = request.reason
    response.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()

    return {"success": True, "message": "已驳回"}


@router.post("/admin/classes/{class_id}/publish-documents")
async def publish_documents_to_class(
    class_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_staff)
):
    """发布文书到班级（管理员/教练）"""

    template_ids = request.get("template_ids", [])
    _due_date = request.get("due_date")  # noqa: F841

    if not template_ids:
        raise HTTPException(status_code=400, detail="请选择要发布的文书")

    # 获取班级
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")

    # 教练权限检查
    if current_user.role == UserRole.INSTRUCTOR:
        result = await db.execute(
            select(ClassMember).where(
                ClassMember.class_id == class_id,
                ClassMember.user_id == current_user.id,
                ClassMember.role == UserRole.INSTRUCTOR
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="您不是该班级的教练")

    # 获取班级所有学员（JOIN users确保用户存在且活跃）
    result = await db.execute(
        select(ClassMember).join(
            User, ClassMember.user_id == User.id
        ).where(
            ClassMember.class_id == class_id,
            ClassMember.role == UserRole.STUDENT,
            User.is_active == True
        )
    )
    students = result.scalars().all()

    # 为每个学员创建文档状态记录（标记为待完成）
    published_count = 0
    for student in students:
        for template_id in template_ids:
            # 检查是否已存在
            result = await db.execute(
                select(DocumentResponse).where(
                    DocumentResponse.student_id == student.user_id,
                    DocumentResponse.template_id == template_id
                )
            )
            if not result.scalar_one_or_none():
                # 创建新的待完成记录
                response = DocumentResponse(
                    student_id=student.user_id,
                    template_id=template_id,
                    status="pending",
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
                )
                db.add(response)
                published_count += 1

    # 先提交文档记录（在 class_documents 之前，避免失败事务污染）
    await db.commit()

    # 同步写入 class_documents 表（表暂未创建，使用独立事务避免污染主事务）
    try:
        for template_id in template_ids:
            try:
                async with db.begin():
                    await db.execute(
                        sql_text(
                            "INSERT INTO class_documents (class_id, template_id, published_at) "
                            "VALUES (:cid, :tid, :now) ON CONFLICT DO NOTHING"
                        ),
                        {"cid": class_id, "tid": template_id, "now": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}
                    )
            except Exception:
                pass  # class_documents 表可能不存在，静默跳过
    except Exception:
        pass  # class_documents 表可能不存在，静默跳过

    return {
        "success": True,
        "message": f"成功发布到 {len(students)} 名学员",
        "published_count": published_count,
        "student_count": len(students)
    }


@router.get("/admin/document-responses/{response_id}/pdf")
async def get_response_pdf(
    response_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_staff)
):
    """生成并返回该学员该份文书的 PDF 文件"""

    result = await db.execute(
        select(DocumentResponse, DocumentTemplate, User)
        .join(DocumentTemplate, DocumentResponse.template_id == DocumentTemplate.id)
        .join(User, DocumentResponse.student_id == User.id)
        .where(DocumentResponse.id == response_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")

    response, template, student = row

    # 教练权限检查
    if current_user.role == UserRole.INSTRUCTOR:
        student_ids = await get_instructor_students(db, current_user.id)
        if student.id not in student_ids:
            raise HTTPException(status_code=403, detail="无权访问该学员")

    # 确保 reportlab 已安装
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab 未安装，请运行: pip install reportlab")

    # 准备目录
    await ensure_directories()
    student_doc_dir = os.path.join(DOCUMENT_DIR, str(student.id))
    os.makedirs(student_doc_dir, exist_ok=True)

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{template.id}_{timestamp}.pdf"
    filepath = os.path.join(student_doc_dir, filename)

    # 创建 PDF
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    # 注册中文字体（尝试使用系统字体）
    font_name = "SimHei"
    try:
        # macOS 系统字体路径
        pdfmetrics.registerFont(TTFont('SimHei', '/System/Library/Fonts/STHeiti Light.ttc'))
    except Exception:
        try:
            # 尝试其他字体
            pdfmetrics.registerFont(TTFont('SimHei', '/System/Library/Fonts/PingFang.ttc'))
        except Exception:
            font_name = "Helvetica"  # 回退到默认字体

    y_position = height - 30 * mm

    # 1. 标题
    c.setFont(font_name, 16)
    c.drawCentredString(width / 2, y_position, template.name)
    y_position -= 15 * mm

    # 2. 分隔线
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    c.line(30 * mm, y_position, width - 30 * mm, y_position)
    y_position -= 10 * mm

    # 3. 正文内容
    c.setFont(font_name, 10)

    # 处理 static_html（去除 HTML 标签）
    static_text = template.static_html or ""
    # 简单去除 HTML 标签
    static_text = re.sub(r'<[^>]+>', '', static_text)
    static_text = static_text.strip()

    # 替换模板变量
    if response.answers:
        for key, value in response.answers.items():
            static_text = static_text.replace(f"{{{{{key}}}}}", str(value) if value else "")

    # 按行绘制
    lines = static_text.split('\n')
    for line in lines:
        if y_position < 30 * mm:
            c.showPage()
            y_position = height - 30 * mm
            c.setFont(font_name, 10)

        # 自动换行
        while len(line) > 60:
            c.drawString(30 * mm, y_position, line[:60])
            line = line[60:]
            y_position -= 6 * mm
        c.drawString(30 * mm, y_position, line)
        y_position -= 6 * mm

    y_position -= 10 * mm

    # 4. 填写字段
    c.setFont(font_name, 11)
    fields_schema = template.fields_schema or []
    answers = response.answers or {}

    for field in fields_schema:
        if y_position < 30 * mm:
            c.showPage()
            y_position = height - 30 * mm
            c.setFont(font_name, 11)

        field_id = field.get("id", "")
        field_label = field.get("label") or field.get("question") or field_id
        field_value = answers.get(field_id, "")

        # 格式化值
        if isinstance(field_value, list):
            field_value = ", ".join(str(v) for v in field_value)
        elif field_value is None:
            field_value = ""

        # 不显示签名字段的内容
        if field.get("type") == "signature":
            continue

        text = f"{field_label}：{field_value}"
        c.drawString(30 * mm, y_position, text)
        y_position -= 7 * mm

    y_position -= 10 * mm

    # 5. 签名图片
    if response.signature_image:
        signature_path = os.path.join(
            "/Users/wjjmac/localserver/diving.school/backend/static/",
            response.signature_image
        )
        if os.path.exists(signature_path):
            try:
                # 添加签名图片
                c.drawImage(signature_path, 30 * mm, y_position - 30 * mm, width=50 * mm, height=30 * mm, preserveAspectRatio=True)
                y_position -= 35 * mm
            except Exception as e:
                c.drawString(30 * mm, y_position, f"[签名图片加载失败: {e}]")
                y_position -= 7 * mm

    # 6. 页脚信息
    y_position -= 10 * mm
    c.setFont(font_name, 9)
    c.setFillColorRGB(0.3, 0.3, 0.3)

    footer_items = [
        f"姓名：{response.snapshot_name or student.name}",
        f"身份证号：{mask_id_number(response.snapshot_id_number or student.id_card) if response.snapshot_id_number or student.id_card else ''}",
        f"电话：{response.snapshot_phone or student.phone}",
        f"日期：{datetime.now().strftime('%Y-%m-%d')}"
    ]

    for item in footer_items:
        if y_position < 20 * mm:
            c.showPage()
            y_position = height - 30 * mm
            c.setFont(font_name, 9)
            c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawString(width - 80 * mm, y_position, item)
        y_position -= 5 * mm

    c.save()

    # 返回 PDF 文件流
    return StreamingResponse(
        open(filepath, "rb"),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{template.name}_{student.name}.pdf"'
        }
    )


# ===== 导出路由 =====

# 学员路由
student_router = APIRouter(prefix="/students/me/documents", tags=["学员-入学文书"])
student_router.add_api_route("/", get_my_documents, methods=["GET"])
student_router.add_api_route("/{template_id}", get_my_document_detail, methods=["GET"])
student_router.add_api_route("/{template_id}", submit_document, methods=["POST"])

# 管理员路由
admin_router = APIRouter(prefix="/admin", tags=["管理员-入学文书"])
admin_router.add_api_route("/document-templates", get_templates, methods=["GET"])
admin_router.add_api_route("/document-templates/{template_id}", get_template_detail, methods=["GET"])
admin_router.add_api_route("/document-templates/{template_id}", update_template, methods=["PUT"])
admin_router.add_api_route("/document-templates/{template_id}", delete_template, methods=["DELETE"])
admin_router.add_api_route("/document-templates", create_template, methods=["POST"])
admin_router.add_api_route("/document-templates/parse", parse_document_template, methods=["POST"])
admin_router.add_api_route("/document-responses", get_document_responses, methods=["GET"])
admin_router.add_api_route("/document-responses/{response_id}", get_response_detail, methods=["GET"])
admin_router.add_api_route("/document-responses/{response_id}/approve", approve_response, methods=["POST"])
admin_router.add_api_route("/document-responses/{response_id}/reject", reject_response, methods=["POST"])
admin_router.add_api_route("/document-responses/{response_id}/pdf", get_response_pdf, methods=["GET"])
admin_router.add_api_route("/classes/{class_id}/publish-documents", publish_documents_to_class, methods=["POST"])
admin_router.add_api_route("/documents", get_document_responses, methods=["GET"])
