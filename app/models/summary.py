from sqlalchemy import Column, Integer, String, Text
from app.database.connection import Base

class Summary(Base):
    __tablename__ = 'summaries'

    summary_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    meeting_name = Column(String(255), index=True)  # Ajustar o tamanho se necessário
    summary_text = Column(Text, nullable=True)  # Permitir valores nulos
    dashboard_data = Column(Text, nullable=True)  # Permitir valores nulos
    id_group = Column(Integer)