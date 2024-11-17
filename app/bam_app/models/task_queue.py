from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Column, Integer, String, ForeignKey, Enum as SqlEnum
from sqlalchemy.orm import relationship

from bam_app.models.core import BaseModel
from bam_core.utils.etc import now_utc


class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class TaskQueue(BaseModel):
    __tablename__ = "task_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_name = Column(String, nullable=False)
    task_data = Column(String, nullable=True)
    logs = Column(String, nullable=True)
    status = Column(SqlEnum(TaskStatus), default=TaskStatus.QUEUED)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, onupdate=now_utc)

    user = relationship("User", back_populates="tasks")

    def __repr__(self):
        return f"<TaskQueue(id={self.id}, task_name={self.task_name}, status={self.status}, user_id={self.user_id})>"

    @classmethod
    def pop_task(cls, session):
        """
        Get the next task in the queue and mark it as running.
        """
        task = (
            session.query(cls)
            .filter_by(status=TaskStatus.QUEUED)
            .order_by(cls.created_at)
            .first()
        )
        if task:
            task.status = TaskStatus.RUNNING
            task.updated_at = now_utc()
            session.commit()
        return task

    @classmethod
    def add_task(cls, session, task_name, user_id, task_data=None):
        task = cls(task_name=task_name, task_data=task_data, user_id=user_id)
        session.add(task)
        session.commit()
        return task

    @classmethod
    def get_task(cls, session, task_id: int):
        """
        Get a task by ID.
        """
        return session.query(cls).filter_by(id=task_id).first()

    @classmethod
    def update_task_status(cls, session, task_id, status):
        """
        Update the status of a task.
        """
        task = cls.get_task(session, task_id)
        if task:
            task.status = status
            task.updated_at = now_utc()
            session.commit()
        return task

    @classmethod
    def update_task_logs(cls, session, task_id, logs):
        """
        Update the logs of a task.
        """
        task = cls.get_task(session, task_id)
        if task:
            task.logs = logs
            task.updated_at = now_utc()
            session.commit()
        return task

    @classmethod
    def complete_task(cls, session, task_id):
        return cls.update_task_status(session, task_id, TaskStatus.SUCCESS)

    @classmethod
    def fail_task(cls, session, task_id):
        return cls.update_task_status(session, task_id, TaskStatus.ERROR)

    @classmethod
    def get_pending_tasks(cls, session):
        return session.query(cls).filter_by(status=TaskStatus.QUEUED).all()

    @classmethod
    def get_running_tasks(cls, session):
        return session.query(cls).filter_by(status=TaskStatus.RUNNING).all()

    @classmethod
    def get_completed_tasks(cls, session):
        return session.query(cls).filter_by(status=TaskStatus.SUCCESS).all()

    @classmethod
    def get_failed_tasks(cls, session):
        return session.query(cls).filter_by(status=TaskStatus.ERROR).all()
