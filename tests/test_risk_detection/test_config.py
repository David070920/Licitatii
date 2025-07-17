"""
Test configuration and utilities for risk detection tests
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from unittest.mock import Mock

from app.db.models import (
    Tender, TenderBid, TenderAward, Company, ContractingAuthority, 
    CPVCode, User, TenderRiskScore
)
from app.services.risk_detection.base import RiskDetectionConfig, RiskDetectionResult


class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_contracting_authority(
        id: int = 1,
        name: str = "Test Authority",
        county: str = "BUCHAREST",
        city: str = "Bucharest"
    ) -> ContractingAuthority:
        """Create a test contracting authority"""
        return ContractingAuthority(
            id=id,
            name=name,
            county=county,
            city=city,
            cui=f"RO{id:08d}",
            address=f"Test Address {id}",
            contact_email=f"contact{id}@authority.gov.ro",
            authority_type="NATIONAL"
        )
    
    @staticmethod
    def create_company(
        id: int = 1,
        name: str = "Test Company",
        county: str = "BUCHAREST"
    ) -> Company:
        """Create a test company"""
        return Company(
            id=id,
            name=name,
            cui=f"RO{id:08d}",
            county=county,
            city="Bucharest",
            address=f"Test Company Address {id}",
            contact_email=f"contact{id}@company.ro",
            company_type="SRL",
            company_size="MEDIUM"
        )
    
    @staticmethod
    def create_tender(
        id: str = "test-tender-1",
        title: str = "Test Tender",
        estimated_value: Decimal = Decimal("100000"),
        contracting_authority: ContractingAuthority = None,
        cpv_code: str = "45000000",
        tender_type: str = "OPEN",
        publication_date: datetime = None,
        bids: List[TenderBid] = None
    ) -> Tender:
        """Create a test tender"""
        
        if contracting_authority is None:
            contracting_authority = TestDataFactory.create_contracting_authority()
        
        if publication_date is None:
            publication_date = datetime.utcnow()
        
        tender = Tender(
            id=id,
            title=title,
            estimated_value=estimated_value,
            contracting_authority=contracting_authority,
            contracting_authority_id=contracting_authority.id,
            cpv_code=cpv_code,
            tender_type=tender_type,
            procedure_type="OPEN",
            publication_date=publication_date,
            submission_deadline=publication_date + timedelta(days=30),
            status="ACTIVE",
            currency="RON",
            source_system="SICAP",
            external_id=f"EXT_{id}",
            description=f"Description for {title}",
            bids=bids or []
        )
        
        return tender
    
    @staticmethod
    def create_tender_bid(
        id: str = "test-bid-1",
        tender: Tender = None,
        company: Company = None,
        bid_amount: Decimal = Decimal("95000"),
        is_winner: bool = False,
        status: str = "VALID"
    ) -> TenderBid:
        """Create a test tender bid"""
        
        if company is None:
            company = TestDataFactory.create_company()
        
        return TenderBid(
            id=id,
            tender=tender,
            company=company,
            company_id=company.id,
            bid_amount=bid_amount,
            currency="RON",
            bid_date=datetime.utcnow(),
            status=status,
            is_winner=is_winner,
            execution_period_days=365,
            evaluation_score=Decimal("85.0") if is_winner else Decimal("75.0")
        )
    
    @staticmethod
    def create_tender_award(
        id: str = "test-award-1",
        tender: Tender = None,
        company: Company = None,
        awarded_amount: Decimal = Decimal("95000")
    ) -> TenderAward:
        """Create a test tender award"""
        
        if company is None:
            company = TestDataFactory.create_company()
        
        return TenderAward(
            id=id,
            tender=tender,
            company=company,
            company_id=company.id,
            awarded_amount=awarded_amount,
            currency="RON",
            award_date=datetime.utcnow(),
            contract_start_date=datetime.utcnow() + timedelta(days=30),
            contract_end_date=datetime.utcnow() + timedelta(days=395),
            contract_value=awarded_amount,
            status="ACTIVE",
            contract_number=f"CONTRACT_{id}"
        )
    
    @staticmethod
    def create_user(
        id: str = "test-user-1",
        email: str = "test@example.com",
        first_name: str = "Test",
        last_name: str = "User"
    ) -> User:
        """Create a test user"""
        return User(
            id=id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            hashed_password="hashed_password",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            login_count=0
        )
    
    @staticmethod
    def create_tender_risk_score(
        tender: Tender = None,
        overall_risk_score: Decimal = Decimal("65.0"),
        risk_level: str = "MEDIUM",
        single_bidder_risk: Decimal = Decimal("70.0"),
        price_anomaly_risk: Decimal = Decimal("30.0"),
        frequency_risk: Decimal = Decimal("50.0"),
        geographic_risk: Decimal = Decimal("20.0"),
        risk_flags: List[str] = None
    ) -> TenderRiskScore:
        """Create a test tender risk score"""
        
        if risk_flags is None:
            risk_flags = ["SINGLE_BIDDER", "PRICE_ANOMALY"]
        
        return TenderRiskScore(
            tender=tender,
            tender_id=tender.id if tender else "test-tender-1",
            overall_risk_score=overall_risk_score,
            risk_level=risk_level,
            single_bidder_risk=single_bidder_risk,
            price_anomaly_risk=price_anomaly_risk,
            frequency_risk=frequency_risk,
            geographic_risk=geographic_risk,
            analysis_date=datetime.utcnow(),
            analysis_version="1.0.0",
            risk_flags=risk_flags,
            auto_generated=True,
            detailed_analysis={
                "individual_scores": {
                    "single_bidder": float(single_bidder_risk),
                    "price_anomaly": float(price_anomaly_risk),
                    "frequent_winner": float(frequency_risk),
                    "geographic_clustering": float(geographic_risk)
                }
            }
        )
    
    @staticmethod
    def create_risk_detection_result(
        risk_score: float = 65.0,
        risk_level: str = "MEDIUM",
        risk_flags: List[str] = None,
        confidence: float = 0.8,
        algorithm: str = "test_algorithm"
    ) -> RiskDetectionResult:
        """Create a test risk detection result"""
        
        if risk_flags is None:
            risk_flags = ["SINGLE_BIDDER", "PRICE_ANOMALY"]
        
        return RiskDetectionResult(
            risk_score=risk_score,
            risk_level=risk_level,
            risk_flags=risk_flags,
            detailed_analysis={
                "algorithm": algorithm,
                "analysis_type": "test",
                "analysis_date": datetime.utcnow().isoformat()
            },
            confidence=confidence
        )


class TestScenarios:
    """Common test scenarios for risk detection"""
    
    @staticmethod
    def create_single_bidder_scenario() -> Dict[str, Any]:
        """Create a single bidder test scenario"""
        
        authority = TestDataFactory.create_contracting_authority()
        company = TestDataFactory.create_company()
        tender = TestDataFactory.create_tender(
            id="single-bidder-tender",
            title="Single Bidder Tender",
            estimated_value=Decimal("500000"),
            contracting_authority=authority
        )
        
        bid = TestDataFactory.create_tender_bid(
            id="single-bid",
            tender=tender,
            company=company,
            bid_amount=Decimal("480000"),
            is_winner=True
        )
        
        tender.bids = [bid]
        
        return {
            "tender": tender,
            "authority": authority,
            "company": company,
            "bid": bid,
            "expected_risk_level": "HIGH",
            "expected_flags": ["SINGLE_BIDDER"]
        }
    
    @staticmethod
    def create_multiple_bidder_scenario() -> Dict[str, Any]:
        """Create a multiple bidder test scenario"""
        
        authority = TestDataFactory.create_contracting_authority()
        tender = TestDataFactory.create_tender(
            id="multi-bidder-tender",
            title="Multiple Bidder Tender",
            estimated_value=Decimal("300000"),
            contracting_authority=authority
        )
        
        companies = [
            TestDataFactory.create_company(id=1, name="Company 1"),
            TestDataFactory.create_company(id=2, name="Company 2"),
            TestDataFactory.create_company(id=3, name="Company 3"),
            TestDataFactory.create_company(id=4, name="Company 4")
        ]
        
        bids = []
        for i, company in enumerate(companies):
            bid = TestDataFactory.create_tender_bid(
                id=f"bid-{i+1}",
                tender=tender,
                company=company,
                bid_amount=Decimal(str(290000 + i * 5000)),
                is_winner=(i == 0)
            )
            bids.append(bid)
        
        tender.bids = bids
        
        return {
            "tender": tender,
            "authority": authority,
            "companies": companies,
            "bids": bids,
            "expected_risk_level": "LOW",
            "expected_flags": []
        }
    
    @staticmethod
    def create_high_value_tender_scenario() -> Dict[str, Any]:
        """Create a high-value tender test scenario"""
        
        authority = TestDataFactory.create_contracting_authority()
        company = TestDataFactory.create_company()
        tender = TestDataFactory.create_tender(
            id="high-value-tender",
            title="High Value Tender",
            estimated_value=Decimal("5000000"),  # 5M RON
            contracting_authority=authority
        )
        
        bid = TestDataFactory.create_tender_bid(
            id="high-value-bid",
            tender=tender,
            company=company,
            bid_amount=Decimal("4800000"),
            is_winner=True
        )
        
        tender.bids = [bid]
        
        return {
            "tender": tender,
            "authority": authority,
            "company": company,
            "bid": bid,
            "expected_risk_level": "HIGH",
            "expected_flags": ["SINGLE_BIDDER", "HIGH_VALUE_SINGLE_BIDDER"]
        }
    
    @staticmethod
    def create_frequent_winner_scenario() -> Dict[str, Any]:
        """Create a frequent winner test scenario"""
        
        authority = TestDataFactory.create_contracting_authority()
        company = TestDataFactory.create_company(id=1, name="Frequent Winner Co")
        
        # Create multiple tenders won by the same company
        tenders = []
        for i in range(5):
            tender = TestDataFactory.create_tender(
                id=f"frequent-winner-tender-{i}",
                title=f"Tender {i}",
                estimated_value=Decimal("200000"),
                contracting_authority=authority,
                publication_date=datetime.utcnow() - timedelta(days=i * 30)
            )
            
            bid = TestDataFactory.create_tender_bid(
                id=f"frequent-winner-bid-{i}",
                tender=tender,
                company=company,
                bid_amount=Decimal(str(190000 + i * 1000)),
                is_winner=True
            )
            
            tender.bids = [bid]
            tenders.append(tender)
        
        return {
            "tenders": tenders,
            "authority": authority,
            "company": company,
            "expected_risk_level": "HIGH",
            "expected_flags": ["HIGH_WIN_RATE", "FREQUENT_WINNER"]
        }
    
    @staticmethod
    def create_price_anomaly_scenario() -> Dict[str, Any]:
        """Create a price anomaly test scenario"""
        
        authority = TestDataFactory.create_contracting_authority()
        company = TestDataFactory.create_company()
        
        # Create a tender with unusually low winning bid
        tender = TestDataFactory.create_tender(
            id="price-anomaly-tender",
            title="Price Anomaly Tender",
            estimated_value=Decimal("1000000"),
            contracting_authority=authority
        )
        
        bid = TestDataFactory.create_tender_bid(
            id="anomaly-bid",
            tender=tender,
            company=company,
            bid_amount=Decimal("500000"),  # 50% of estimated value
            is_winner=True
        )
        
        tender.bids = [bid]
        
        return {
            "tender": tender,
            "authority": authority,
            "company": company,
            "bid": bid,
            "expected_risk_level": "HIGH",
            "expected_flags": ["PRICE_ANOMALY", "ESTIMATED_VALUE_ANOMALY"]
        }


class MockDatabaseSession:
    """Mock database session for testing"""
    
    def __init__(self):
        self.data = {
            "tenders": {},
            "companies": {},
            "authorities": {},
            "risk_scores": {},
            "bids": {},
            "awards": {}
        }
        self.queries = []
    
    def add(self, obj):
        """Mock add operation"""
        self.queries.append(("add", obj))
    
    def commit(self):
        """Mock commit operation"""
        self.queries.append(("commit",))
    
    def refresh(self, obj):
        """Mock refresh operation"""
        self.queries.append(("refresh", obj))
    
    def query(self, model):
        """Mock query operation"""
        return MockQuery(model, self)
    
    def close(self):
        """Mock close operation"""
        self.queries.append(("close",))


class MockQuery:
    """Mock database query for testing"""
    
    def __init__(self, model, session):
        self.model = model
        self.session = session
        self.filters = []
        self.joins = []
        self.orders = []
        self.limit_value = None
    
    def filter(self, *args):
        """Mock filter operation"""
        self.filters.extend(args)
        return self
    
    def join(self, *args):
        """Mock join operation"""
        self.joins.extend(args)
        return self
    
    def order_by(self, *args):
        """Mock order_by operation"""
        self.orders.extend(args)
        return self
    
    def limit(self, value):
        """Mock limit operation"""
        self.limit_value = value
        return self
    
    def all(self):
        """Mock all operation"""
        return []
    
    def first(self):
        """Mock first operation"""
        return None
    
    def count(self):
        """Mock count operation"""
        return 0


@pytest.fixture
def risk_config():
    """Fixture for risk detection configuration"""
    return RiskDetectionConfig()


@pytest.fixture
def mock_db_session():
    """Fixture for mock database session"""
    return MockDatabaseSession()


@pytest.fixture
def test_data_factory():
    """Fixture for test data factory"""
    return TestDataFactory()


@pytest.fixture
def test_scenarios():
    """Fixture for test scenarios"""
    return TestScenarios()


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow