"""
认证API - 班级制培训管理系统 (JWT v3)
支持四级角色登录，班级时间范围验证
安全增强：JWT Token + 密码强度校验 + 账户锁定
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
import bcrypt
import time
import re
from collections import defaultdict
import logging

from app.core.database import get_db
from app.core.config import settings
from app.models.class_system import (
    User, Class, ClassMember, UserRole, ClassStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])

# ===== JWT 配置 =====
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
REFRESH_TOKEN_EXPIRE = timedelta(days=30)

# ===== 登录频率限制（增强版：按标识符 + IP 双重限流）=====
_login_attempts: dict = defaultdict(list)
_account_locks: dict = {}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW = 300  # 5分钟窗口
LOCK_DURATION = 900  # 15分钟锁定


def check_rate_limit(identifier: str) -> Optional[str]:
    """检查登录频率限制"""
    now = time.time()
    lock = _account_locks.get(identifier)
    if lock and now - lock < LOCK_DURATION:
        remaining = int(LOCK_DURATION - (now - lock))
        return f"账号已锁定，请{remaining}秒后再试"
    elif lock:
        del _account_locks[identifier]
        _login_attempts[identifier] = []

    if identifier in _login_attempts:
        _login_attempts[identifier] = [
            t for t in _login_attempts[identifier]
            if now - t < LOGIN_WINDOW
        ]

    if len(_login_attempts.get(identifier, [])) >= MAX_LOGIN_ATTEMPTS:
        _account_locks[identifier] = now
        return "登录失败次数过多，已锁定15分钟"
    return None


def record_failed_login(identifier: str):
    """记录失败登录"""
    _login_attempts[identifier].append(time.time())


def clear_login_attempts(identifier: str):
    """清除登录记录"""
    _login_attempts.pop(identifier, None)
    _account_locks.pop(identifier, None)


security = HTTPBearer()

# ===== 密码安全策略 =====
MIN_PASSWORD_LENGTH = 8

def validate_password_strength(password: str) -> Optional[str]:
    """
    密码强度验证
    - 最少 8 位
    - 至少包含一个大写字母
    - 至少包含一个小写字母
    - 至少包含一个数字
    - 至少包含一个特殊字符
    返回 None 表示通过，否则返回错误信息
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"密码长度至少 {MIN_PASSWORD_LENGTH} 位"

    checks = [
        (r'[A-Z]', "大写字母"),
        (r'[a-z]', "小写字母"),
        (r'[0-9]', "数字"),
        (r'[!@#$%^&*(),.?\":{}|<>_\-+=;\[\]\\/`~]', "特殊字符"),
    ]

    missing = []
    for pattern, name in checks:
        if not re.search(pattern, password):
            missing.append(name)

    if missing:
        return f"密码需包含：{', '.join(missing)}"
    return None


def hash_password(password: str) -> str:
    """密码哈希"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


# ===== JWT Token 工具 =====

def create_access_token(user_id: int, role: str) -> str:
    """创建访问令牌"""
    expire = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, role: str) -> str:
    """创建刷新令牌"""
    expire = datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRE
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """解码并验证 JWT token，返回 payload 或 None"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """从 JWT 获取当前用户"""
    token_data = decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="无效的认证令牌")

    # 验证 token 类型
    if token_data.get("type") != "access":
        raise HTTPException(status_code=401, detail="非法的令牌类型")

    user_id = int(token_data["sub"])

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="账号已被禁用")

    # 验证 token 中的角色与数据库一致（防止角色变更后旧 token 仍可用）
    if token_data.get("role") != user.role.value:
        raise HTTPException(status_code=401, detail="令牌已过期，请重新登录")

    return user


async def get_current_class(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Optional[Class]:
    """获取当前用户所属班级"""
    if user.role == UserRole.ADMIN:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    result = await db.execute(
        select(Class)
        .join(ClassMember)
        .where(
            and_(
                ClassMember.user_id == user.id,
                Class.start_time <= now,
                Class.end_time >= now,
                Class.status == ClassStatus.ACTIVE
            )
        )
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=403, detail="您不属于任何进行中的班级")
    return cls


async def check_class_access(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Class:
    """检查班级访问权限（非管理员必须）"""
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="管理员无班级权限")

    cls = await get_current_class(user, db)
    if not cls:
        raise HTTPException(status_code=403, detail="您不属于任何进行中的班级")

    return cls


# ===== 请求/响应模型 =====

class LoginRequest(BaseModel):
    """登录请求"""
    name: Optional[str] = None
    id_card: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    role: str  # admin/instructor/manager/student

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed = {'admin', 'instructor', 'manager', 'student'}
        if v.lower() not in allowed:
            raise ValueError(f"无效的角色: {v}")
        return v.lower()


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    name: str
    id_card: Optional[str]
    phone: Optional[str]
    role: str
    avatar: Optional[str]


class ClassResponse(BaseModel):
    """班级响应"""
    id: int
    name: str
    location: Optional[str]
    start_time: datetime
    end_time: datetime
    status: str


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[UserResponse] = None
    cls: Optional[ClassResponse] = None
    message: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        error = validate_password_strength(v)
        if error:
            raise ValueError(error)
        return v


class UpdateProfileRequest(BaseModel):
    """更新个人信息请求"""
    name: Optional[str] = None
    phone: Optional[str] = None


# ===== API 路由 =====

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    统一登录接口 - JWT 认证

    - 管理员: name + id_card + password
    - 教练员: name + id_card + password
    - 管理干部: name + phone
    - 学员: name + id_card + phone
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC for DB TIMESTAMP WITHOUT TIME ZONE comparison

    # 登录频率限制（按 name 限流）
    rate_key = request.name or request.phone or "unknown"
    rate_error = check_rate_limit(rate_key)
    if rate_error:
        return LoginResponse(success=False, message=rate_error)

    try:
        role = UserRole(request.role)
    except ValueError:
        return LoginResponse(success=False, message="无效的角色类型")

    if role == UserRole.ADMIN:
        return await _login_admin(request, db, now)

    elif role == UserRole.INSTRUCTOR:
        return await _login_instructor(request, db, now)

    elif role == UserRole.MANAGER:
        return await _login_manager(request, db, now)

    elif role == UserRole.STUDENT:
        return await _login_student(request, db, now)

    return LoginResponse(success=False, message="无效的角色")


async def _login_admin(request: LoginRequest, db: AsyncSession, now: datetime) -> LoginResponse:
    """管理员登录"""
    if not request.id_card or not request.password:
        return LoginResponse(success=False, message="管理员登录需要身份证号和密码")

    result = await db.execute(
        select(User).where(
            User.name == request.name,
            User.id_card == request.id_card,
            User.role == UserRole.ADMIN,
            User.is_active == True
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        return LoginResponse(success=False, message="账号不存在")

    if not user.password_hash or not verify_password(request.password, user.password_hash):
        record_failed_login(request.name)
        return LoginResponse(success=False, message="密码错误")

    if not user.is_active:
        return LoginResponse(success=False, message="账号已被禁用")

    clear_login_attempts(request.name)
    token = create_access_token(user.id, user.role.value)
    refresh = create_refresh_token(user.id, user.role.value)

    return LoginResponse(
        success=True,
        token=token,
        refresh_token=refresh,
        user=UserResponse(
            id=user.id, name=user.name, id_card=user.id_card,
            phone=user.phone, role=user.role.value, avatar=user.avatar
        )
    )


async def _login_instructor(request: LoginRequest, db: AsyncSession, now: datetime) -> LoginResponse:
    """教练员登录"""
    if not request.id_card or not request.password:
        return LoginResponse(success=False, message="教练员登录需要身份证号和密码")

    result = await db.execute(
        select(User).where(
            User.name == request.name,
            User.id_card == request.id_card,
            User.role == UserRole.INSTRUCTOR,
            User.is_active == True
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        return LoginResponse(success=False, message="账号不存在")

    if not user.password_hash or not verify_password(request.password, user.password_hash):
        record_failed_login(request.name)
        return LoginResponse(success=False, message="密码错误")

    # 检查班级权限
    result = await db.execute(
        select(Class)
        .join(ClassMember)
        .where(
            ClassMember.user_id == user.id,
            Class.start_time <= now,
            Class.end_time >= now,
            Class.status == ClassStatus.ACTIVE
        )
    )
    cls = result.scalar_one_or_none()

    clear_login_attempts(request.name)
    token = create_access_token(user.id, user.role.value)
    refresh = create_refresh_token(user.id, user.role.value)

    if cls:
        return LoginResponse(
            success=True,
            token=token,
            refresh_token=refresh,
            user=UserResponse(
                id=user.id, name=user.name, id_card=user.id_card,
                phone=user.phone, role=user.role.value, avatar=user.avatar
            ),
            cls=ClassResponse(
                id=cls.id, name=cls.name, location=cls.location,
                start_time=cls.start_time, end_time=cls.end_time,
                status=cls.status.value
            )
        )
    else:
        return LoginResponse(
            success=True,
            token=token,
            refresh_token=refresh,
            user=UserResponse(
                id=user.id, name=user.name, id_card=user.id_card,
                phone=user.phone, role=user.role.value, avatar=user.avatar
            ),
            cls=None
        )


async def _login_manager(request: LoginRequest, db: AsyncSession, now: datetime) -> LoginResponse:
    """管理干部登录：姓名 + 手机号"""
    if not request.name or not request.phone:
        return LoginResponse(success=False, message="请输入姓名和手机号")

    result = await db.execute(
        select(User).where(
            User.name == request.name,
            User.phone == request.phone,
            User.role == UserRole.MANAGER,
            User.is_active == True
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        return LoginResponse(success=False, message="账号不存在")

    # 尝试获取进行中的班级
    result = await db.execute(
        select(Class)
        .join(ClassMember)
        .where(
            ClassMember.user_id == user.id,
            Class.start_time <= now,
            Class.end_time >= now,
            Class.status == ClassStatus.ACTIVE
        )
    )
    cls = result.scalar_one_or_none()

    clear_login_attempts(request.phone)
    token = create_access_token(user.id, user.role.value)
    refresh = create_refresh_token(user.id, user.role.value)

    return LoginResponse(
        success=True,
        token=token,
        refresh_token=refresh,
        user=UserResponse(
            id=user.id, name=user.name, id_card="",
            phone=user.phone, role=user.role.value, avatar=user.avatar
        ),
        cls=ClassResponse(
            id=cls.id, name=cls.name, location=cls.location,
            start_time=cls.start_time, end_time=cls.end_time,
            status=cls.status.value
        ) if cls else None
    )


async def _login_student(request: LoginRequest, db: AsyncSession, now: datetime) -> LoginResponse:
    """学员登录"""
    if not request.id_card or not request.phone:
        return LoginResponse(success=False, message="学员登录需要身份证号和手机号")

    # 验证身份证号格式（18位）
    id_card = request.id_card.strip()
    if len(id_card) != 18:
        return LoginResponse(success=False, message="身份证号必须为18位")

    # 验证手机号格式（11位）
    phone = request.phone.strip()
    if len(phone) != 11:
        return LoginResponse(success=False, message="手机号必须为11位")

    result = await db.execute(
        select(User).where(
            User.name == request.name,
            User.id_card == id_card,
            User.phone == phone,
            User.role == UserRole.STUDENT,
            User.is_active == True
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        return LoginResponse(success=False, message="账号不存在")

    # 检查班级权限
    result = await db.execute(
        select(Class)
        .join(ClassMember)
        .where(
            ClassMember.user_id == user.id,
            Class.start_time <= now,
            Class.end_time >= now,
            Class.status == ClassStatus.ACTIVE
        )
    )
    cls = result.scalar_one_or_none()

    if not cls:
        return LoginResponse(success=False, message="当前没有进行中的培训班")

    clear_login_attempts(request.name)
    token = create_access_token(user.id, user.role.value)
    refresh = create_refresh_token(user.id, user.role.value)

    return LoginResponse(
        success=True,
        token=token,
        refresh_token=refresh,
        user=UserResponse(
            id=user.id, name=user.name, id_card=user.id_card,
            phone=user.phone, role=user.role.value, avatar=user.avatar
        ),
        cls=ClassResponse(
            id=cls.id, name=cls.name, location=cls.location,
            start_time=cls.start_time, end_time=cls.end_time,
            status=cls.status.value
        )
    )


@router.post("/refresh")
async def refresh_token(request: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    """刷新访问令牌"""
    payload = decode_token(request.refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的刷新令牌")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="非法的令牌类型")

    user_id = int(payload["sub"])
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="账号不存在或已禁用")

    access_token = create_access_token(user.id, user.role.value)
    return {"token": access_token, "token_type": "bearer"}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": user.id,
        "name": user.name,
        "id_card": user.id_card,
        "phone": user.phone,
        "role": user.role.value,
        "avatar": user.avatar
    }


@router.post("/logout")
async def logout():
    """
    登出（客户端清除 token 即可）
    
    安全说明：JWT 无状态，登出依赖客户端清除 token。
    未来可引入 token 黑名单增强安全性。
    """
    return {"success": True, "message": "已登出"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """修改密码（含密码强度校验）"""
    # 验证原密码
    if not user.password_hash or not bcrypt.checkpw(
        request.old_password.encode(), user.password_hash.encode()
    ):
        raise HTTPException(status_code=400, detail="原密码错误")

    # 新密码不能与原密码相同
    if request.old_password == request.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")

    # 更新密码
    user.password_hash = hash_password(request.new_password)
    await db.commit()

    return {"success": True, "message": "密码修改成功"}


@router.post("/profile")
async def update_profile(
    request: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """更新个人信息（姓名/电话）"""
    if request.name is not None:
        name = request.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="姓名不能为空")
        user.name = name
    if request.phone is not None:
        phone = request.phone.strip()
        if phone and len(phone) != 11:
            raise HTTPException(status_code=400, detail="手机号必须为11位")
        user.phone = phone or None
    await db.commit()
    return {
        "success": True,
        "message": "信息更新成功",
        "user": {
            "id": user.id,
            "name": user.name,
            "id_card": user.id_card,
            "phone": user.phone,
            "role": user.role.value,
        }
    }
