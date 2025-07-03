from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Roleplay(Base):
    __tablename__ = "roleplays"

    id = Column(Integer, primary_key=True, index=True)
    comprador = Column(String, nullable=False)
    vendedor = Column(String, nullable=False)
    productos = Column(String, nullable=False)  # JSON serializado en string
    costes = Column(String, nullable=False)     # JSON serializado en string
    audio_filename = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    feedback = Column(String, nullable=True, default="")
    nota = Column(String, nullable=True, default="")
