from sqlalchemy import Column, DateTime, Integer, String
from werkzeug.security import generate_password_hash, check_password_hash

from bam_app.settings import PASSWORD_SALT
from bam_app.models.core import BaseModel
from bam_core.utils.etc import now_utc


class User(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, onupdate=now_utc)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password + PASSWORD_SALT)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash, password + PASSWORD_SALT
        )

    def add_user(self, session, username, password):
        user = User(username=username)
        user.set_password(password)
        session.add(user)
        session.commit()
        return user

    def get_user(self, session, username):
        return session.query(User).filter_by(username=username).first()
