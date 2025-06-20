from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from database import Base

class Roleplay(Base):
    __tablename__ = "roleplays"
    id = Column(Integer, primary_key=True, index=True)
    comprador = Column(String, index=True)
    vendedor = Column(String, index=True)
    productos = Column(Text)  # JSON serializado como texto
    audio_filename = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
