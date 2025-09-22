import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Resume(Base):
    """简历表模型 - 使用灵活的key-value结构"""
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
    title = Column(
        String(200),
        nullable=True,
        comment="简历标题"
    )
    fields = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="简历字段数据JSON - 灵活的key-value结构"
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
    user = relationship("User", back_populates="resumes")

    def __repr__(self):
        return f"<Resume(id={self.id}, title={self.title}, user_id={self.user_id})>"
