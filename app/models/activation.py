import uuid
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class ActivationCodeStatus(enum.Enum):
    """激活码状态枚举"""
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"


class ActivationCode(Base):
    """激活码表模型"""
    __tablename__ = "activation_codes"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="激活码唯一标识"
    )
    code = Column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
        comment="激活码字符串"
    )
    total_uses = Column(
        Integer,
        default=5,
        comment="总使用次数"
    )
    used_count = Column(
        Integer,
        default=0,
        comment="已使用次数"
    )
    status = Column(
        Enum(ActivationCodeStatus),
        default=ActivationCodeStatus.ACTIVE,
        comment="激活码状态"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间"
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="过期时间"
    )

    # 关联关系
    user_activations = relationship("UserActivation", back_populates="activation_code")

    def __repr__(self):
        return f"<ActivationCode(id={self.id}, code={self.code})>"


class UserActivation(Base):
    """用户激活记录表模型"""
    __tablename__ = "user_activations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="记录唯一标识"
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联用户ID"
    )
    activation_code_id = Column(
        UUID(as_uuid=True),
        ForeignKey("activation_codes.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联激活码ID"
    )
    remaining_uses = Column(
        Integer,
        default=5,
        comment="剩余使用次数"
    )
    activated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="激活时间"
    )

    # 关联关系
    user = relationship("User", back_populates="user_activations")
    activation_code = relationship("ActivationCode", back_populates="user_activations")

    def __repr__(self):
        return f"<UserActivation(id={self.id}, user_id={self.user_id}, remaining_uses={self.remaining_uses})>"
