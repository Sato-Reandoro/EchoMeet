from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Summary(Base):
    __tablename__ = 'summaries'

    summary_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    meeting_name = Column(String(255), index=True)  # Ajustar o tamanho se necessário
    summary_text = Column(Text, nullable=True)  # Permitir valores nulos
    dashboard_data = Column(Text, nullable=True)  # Permitir valores nulos
    id_group = Column(Integer, ForeignKey('groups.id'), nullable=False)  # Referenciando a tabela groups

    group = relationship("Group", back_populates="summaries")  # Relacionamento com a tabela Group
