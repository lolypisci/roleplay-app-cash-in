from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Roleplay(Base):
    __tablename__ = "roleplays"
    id = Column(Integer, primary_key=True, index=True)
    comprador = Column(String, index=True)
    vendedor = Column(String, index=True)
    productos = Column(String)  # Stored as JSON string
    costes = Column(String)     # Stored as JSON string
    audio_filename = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    feedback = Column(String, default="")
    nota = Column(String, default="")
