import enum
import uuid
from sqlalchemy import Column, String, Float, Date, Boolean, Integer, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class CostTypeEnum(str, enum.Enum):
    fixed = 'fixed'
    variable = 'variable'
    special = 'special'
    unclassified = 'unclassified'

class Account(Base):
    __tablename__ = 'accounts'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bank_name = Column(String, nullable=False)
    account_type = Column(String, default='Checking')
    iban = Column(String, unique=True, nullable=True)

class Merchant(Base):
    __tablename__ = 'merchants'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    normalized_name = Column(String, unique=True, nullable=False)
    default_main_category = Column(String, nullable=True)
    default_sub_category = Column(String, nullable=True)

class NormalizationAlias(Base):
    __tablename__ = 'normalization_aliases'
    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(String, ForeignKey('merchants.id'), nullable=True)
    regex_pattern = Column(String, nullable=False)
    description = Column(String, nullable=True)

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(String, primary_key=True)  # MD5(date+amount+raw_payee+account_id)
    account_id = Column(String, ForeignKey('accounts.id'), nullable=False)
    merchant_id = Column(String, ForeignKey('merchants.id'), nullable=True)
    
    booking_date = Column(Date, nullable=False)
    valuta_date = Column(Date, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="EUR")
    
    raw_payee = Column(Text, nullable=True)
    raw_purpose = Column(Text, nullable=True)
    
    # Classification Dimensions
    main_category = Column(String, nullable=True)
    sub_category = Column(String, nullable=True)
    cost_type = Column(Enum(CostTypeEnum), default=CostTypeEnum.unclassified)
    
    is_house_related = Column(Boolean, default=False)
    is_travel_related = Column(Boolean, default=False)
    is_internal_transfer = Column(Boolean, default=False)
    
    needs_review = Column(Boolean, default=True)
    review_reason = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class CategorizationRule(Base):
    __tablename__ = 'category_rules'
    id = Column(Integer, primary_key=True, autoincrement=True)
    priority = Column(Integer, default=100)
    regex_pattern = Column(String, nullable=False)
    search_field = Column(String, nullable=False)  # 'raw_payee', 'raw_purpose', or 'any'
    
    assign_main_category = Column(String, nullable=True)
    assign_sub_category = Column(String, nullable=True)
    assign_cost_type = Column(Enum(CostTypeEnum), nullable=True)
    
    set_house_related = Column(Boolean, nullable=True)
    set_travel_related = Column(Boolean, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MonthlySummary(Base):
    __tablename__ = 'monthly_summaries'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, ForeignKey('accounts.id'))
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    
    total_income = Column(Float, default=0.0)
    total_fixed_costs = Column(Float, default=0.0)
    total_variable_costs = Column(Float, default=0.0)
    total_special_costs = Column(Float, default=0.0)
