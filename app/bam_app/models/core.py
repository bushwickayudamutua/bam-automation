from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bam_app.settings import DATABASE_URL

BaseModel = declarative_base()

engine = create_engine(DATABASE_URL)
BaseModel.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
