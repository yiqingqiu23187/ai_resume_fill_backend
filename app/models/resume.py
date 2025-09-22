import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Resume(Base):
    """简历表模型"""
    __tablename__ = "resumes"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="简历唯一标识"
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联用户ID"
    )
    personal_info = Column(
        JSON,
        nullable=False,
        comment="个人基本信息JSON"
    )
    education = Column(
        JSON,
        nullable=False,
        comment="教育经历JSON"
    )
    experience = Column(
        JSON,
        nullable=False,
        comment="工作经验JSON"
    )
    skills = Column(
        JSON,
        nullable=False,
        comment="技能信息JSON"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )

    # 关联关系
    user = relationship("User", back_populates="resumes")

    def __repr__(self):
        return f"<Resume(id={self.id}, user_id={self.user_id})>"
