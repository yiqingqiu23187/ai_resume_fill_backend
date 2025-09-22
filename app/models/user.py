import uuid
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum


class UserStatus(enum.Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"


class User(Base):
    """用户表模型"""
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="用户唯一标识"
    )
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="用户邮箱"
    )
    password_hash = Column(
        String(255),
        nullable=False,
        comment="密码哈希值"
    )
    status = Column(
        Enum(UserStatus),
        default=UserStatus.ACTIVE,
        comment="用户状态"
    )
    created_at = Column(
        DateTime(),
        server_default=func.now(),
        comment="创建时间"
    )
    updated_at = Column(
        DateTime(),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )

    # 关联关系
    resumes = relationship("Resume", back_populates="user")
    user_activations = relationship("UserActivation", back_populates="user")
    usage_logs = relationship("UsageLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
