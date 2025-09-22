import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class UsageLog(Base):
    """使用日志表模型"""
    __tablename__ = "usage_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="日志唯一标识"
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联用户ID"
    )
    website_url = Column(
        String(500),
        nullable=False,
        comment="使用的网站URL"
    )
    fields_count = Column(
        Integer,
        nullable=False,
        comment="检测到的字段数量"
    )
    success_count = Column(
        Integer,
        nullable=False,
        comment="成功填写的字段数量"
    )
    used_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="使用时间"
    )

    # 关联关系
    user = relationship("User", back_populates="usage_logs")

    def __repr__(self):
        return f"<UsageLog(id={self.id}, user_id={self.user_id}, website_url={self.website_url})>"
