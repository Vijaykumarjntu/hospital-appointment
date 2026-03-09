from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, 
    Boolean, ForeignKey, Text, JSON, Time, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True)
    phone_number = Column(String(20), unique=True, nullable=False)
    preferred_language = Column(String(10), default='en')  # 'en', 'hi', 'ta'
    name = Column(String(100))
    created_at = Column(DateTime, default=func.now())
    last_interaction = Column(DateTime)
    interaction_summary = Column(Text)
    mdata = Column(JSON, default={})
    
    # Relationships
    appointments = relationship("Appointment", back_populates="patient")
    conversation_logs = relationship("ConversationLog", back_populates="patient")
    
    __table_args__ = (
        Index('idx_patients_phone', 'phone_number'),
    )

class Doctor(Base):
    __tablename__ = "doctors"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    specialization = Column(String(100))
    time_slot_duration = Column(Integer, default=30)  # minutes
    buffer_time = Column(Integer, default=5)  # minutes between appointments
    is_active = Column(Boolean, default=True)
    mdata = Column(JSON, default={})
    
    # Relationships
    schedules = relationship("DoctorSchedule", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")

class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"
    
    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    day_of_week = Column(Integer)  # 0=Monday, 6=Sunday
    start_time = Column(Time)
    end_time = Column(Time)
    is_available = Column(Boolean, default=True)
    
    # Relationships
    doctor = relationship("Doctor", back_populates="schedules")
    
    __table_args__ = (
        Index('idx_doctor_schedule', 'doctor_id', 'day_of_week'),
    )

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    appointment_time = Column(DateTime, nullable=False)
    status = Column(String(20), default='scheduled')  # scheduled, confirmed, cancelled, completed, rescheduled
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    cancellation_reason = Column(Text)
    rescheduled_from_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    reminder_called = Column(Boolean, default=False)
    reminder_confirmed = Column(Boolean, default=False)
    mdata = Column(JSON, default={})
    
    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    rescheduled_from = relationship("Appointment", remote_side=[id])
    
    __table_args__ = (
        Index('idx_appointments_patient', 'patient_id'),
        Index('idx_appointments_doctor_time', 'doctor_id', 'appointment_time'),
        Index('idx_appointments_status', 'status'),
        Index('idx_appointments_time', 'appointment_time'),
    )

class TimeSlot(Base):
    __tablename__ = "time_slots"
    
    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    slot_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False)
    booked_by_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_slots_doctor_time', 'doctor_id', 'slot_time'),
        Index('idx_slots_available', 'doctor_id', 'slot_time', 'is_booked'),
        # UniqueConstraint('doctor_id', 'slot_time', name='unique_doctor_slot'),
    )

class ConversationLog(Base):
    __tablename__ = "conversation_logs"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100))
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    direction = Column(String(10))  # 'inbound' or 'outbound'
    language_used = Column(String(10))
    transcript = Column(Text)
    intent = Column(String(50))
    outcome = Column(String(50))
    call_duration = Column(Integer)  # in seconds
    sentiment_score = Column(Integer)  # 1-5
    created_at = Column(DateTime, default=func.now())
    mdata = Column(JSON, default={})
    
    # Relationships
    patient = relationship("Patient", back_populates="conversation_logs")
    
    __table_args__ = (
        Index('idx_logs_session', 'session_id'),
        Index('idx_logs_patient', 'patient_id'),
        Index('idx_logs_created', 'created_at'),
    )