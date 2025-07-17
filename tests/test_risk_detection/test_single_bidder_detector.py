"""
Tests for Single Bidder Detection Algorithm
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from app.services.risk_detection.single_bidder_detector import SingleBidderDetector
from app.services.risk_detection.base import RiskDetectionConfig
from app.db.models import Tender, TenderBid, Company, ContractingAuthority, CPVCode


class TestSingleBidderDetector:
    """Test cases for SingleBidderDetector"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return RiskDetectionConfig()
    
    @pytest.fixture
    def detector(self, config):
        """Create SingleBidderDetector instance"""
        return SingleBidderDetector(config)
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_tender(self):
        """Create sample tender"""
        authority = ContractingAuthority(
            id=1,
            name="Test Authority",
            county="BUCHAREST",
            city="Bucharest"
        )
        
        tender = Tender(
            id="test-tender-1",
            title="Test Tender",
            estimated_value=Decimal("100000"),
            contracting_authority=authority,
            contracting_authority_id=1,
            cpv_code="45000000",
            publication_date=datetime.utcnow(),
            tender_type="OPEN",
            procedure_type="OPEN",
            status="ACTIVE",
            bids=[]
        )
        
        return tender
    
    @pytest.fixture
    def sample_company(self):
        """Create sample company"""
        return Company(
            id=1,
            name="Test Company",
            cui="RO12345678",
            county="BUCHAREST"
        )
    
    def test_no_bids_analysis(self, detector, sample_tender, mock_db):
        """Test analysis of tender with no bids"""
        
        # Arrange
        sample_tender.bids = []
        
        # Act
        result = detector.analyze_tender(sample_tender, mock_db)
        
        # Assert
        assert result.risk_score == 0.0
        assert result.risk_level == "MINIMAL"
        assert "NO_BIDS" in result.risk_flags
        assert result.detailed_analysis["bid_count"] == 0
    
    def test_single_bidder_detection(self, detector, sample_tender, sample_company, mock_db):
        """Test detection of single bidder tender"""
        
        # Arrange
        bid = TenderBid(
            id="bid-1",
            tender=sample_tender,
            company=sample_company,
            bid_amount=Decimal("95000"),
            status="VALID",
            is_winner=True
        )
        sample_tender.bids = [bid]
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Act
        result = detector.analyze_tender(sample_tender, mock_db)
        
        # Assert
        assert result.risk_score > 0
        assert "SINGLE_BIDDER" in result.risk_flags
        assert result.detailed_analysis["bid_count"] == 1
    
    def test_multiple_bidders_low_risk(self, detector, sample_tender, sample_company, mock_db):
        """Test analysis of tender with multiple bidders"""
        
        # Arrange
        companies = [
            Company(id=1, name="Company 1", cui="RO1"),
            Company(id=2, name="Company 2", cui="RO2"),
            Company(id=3, name="Company 3", cui="RO3"),
            Company(id=4, name="Company 4", cui="RO4")
        ]
        
        bids = []
        for i, company in enumerate(companies):
            bid = TenderBid(
                id=f"bid-{i+1}",
                tender=sample_tender,
                company=company,
                bid_amount=Decimal(str(95000 + i * 1000)),
                status="VALID",
                is_winner=(i == 0)
            )
            bids.append(bid)
        
        sample_tender.bids = bids
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Act
        result = detector.analyze_tender(sample_tender, mock_db)
        
        # Assert
        assert result.risk_score == 0.0
        assert "SINGLE_BIDDER" not in result.risk_flags
        assert result.detailed_analysis["bid_count"] == 4
    
    def test_high_value_single_bidder_amplification(self, detector, sample_tender, sample_company, mock_db):
        """Test risk amplification for high-value single bidder tenders"""
        
        # Arrange
        sample_tender.estimated_value = Decimal("2000000")  # High value
        
        bid = TenderBid(
            id="bid-1",
            tender=sample_tender,
            company=sample_company,
            bid_amount=Decimal("1900000"),
            status="VALID",
            is_winner=True
        )
        sample_tender.bids = [bid]
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Act
        result = detector.analyze_tender(sample_tender, mock_db)
        
        # Assert
        assert result.risk_score > 60  # Should be amplified
        assert "SINGLE_BIDDER" in result.risk_flags
        assert result.detailed_analysis["risk_factors"]["high_value_single_bidder"] == True
    
    def test_historical_context_analysis(self, detector, sample_tender, sample_company, mock_db):
        """Test historical context analysis"""
        
        # Arrange
        sample_tender.bids = [TenderBid(
            id="bid-1",
            tender=sample_tender,
            company=sample_company,
            bid_amount=Decimal("95000"),
            status="VALID",
            is_winner=True
        )]
        
        # Mock historical tenders with high single bidder rate
        historical_tenders = []
        for i in range(10):
            historical_tender = Tender(
                id=f"hist-{i}",
                contracting_authority_id=1,
                publication_date=datetime.utcnow() - timedelta(days=30 + i),
                bids=[TenderBid(id=f"hist-bid-{i}", bid_amount=Decimal("10000"))]
            )
            historical_tenders.append(historical_tender)
        
        mock_db.query.return_value.filter.return_value.all.return_value = historical_tenders
        
        # Act
        result = detector.analyze_tender(sample_tender, mock_db)
        
        # Assert
        assert result.risk_score > 0
        assert "historical_context" in result.detailed_analysis
        assert result.detailed_analysis["historical_context"]["total_historical_tenders"] == 10
    
    def test_cpv_context_analysis(self, detector, sample_tender, sample_company, mock_db):
        """Test CPV context analysis"""
        
        # Arrange
        sample_tender.bids = [TenderBid(
            id="bid-1",
            tender=sample_tender,
            company=sample_company,
            bid_amount=Decimal("95000"),
            status="VALID",
            is_winner=True
        )]
        
        # Mock CPV tenders with different bidding patterns
        cpv_tenders = []
        for i in range(5):
            cpv_tender = Tender(
                id=f"cpv-{i}",
                cpv_code="45000000",
                publication_date=datetime.utcnow() - timedelta(days=10 + i),
                bids=[
                    TenderBid(id=f"cpv-bid-{i}-1", bid_amount=Decimal("10000")),
                    TenderBid(id=f"cpv-bid-{i}-2", bid_amount=Decimal("11000")),
                    TenderBid(id=f"cpv-bid-{i}-3", bid_amount=Decimal("12000"))
                ]
            )
            cpv_tenders.append(cpv_tender)
        
        mock_db.query.return_value.filter.return_value.all.return_value = cpv_tenders
        
        # Act
        result = detector.analyze_tender(sample_tender, mock_db)
        
        # Assert
        assert result.risk_score > 0
        cpv_context = result.detailed_analysis["historical_context"]["cpv_context"]
        assert cpv_context["cpv_total_tenders"] == 5
        assert cpv_context["cpv_avg_bid_count"] == 3
    
    def test_batch_analysis(self, detector, mock_db):
        """Test batch analysis of multiple tenders"""
        
        # Arrange
        tenders = []
        for i in range(3):
            tender = Tender(
                id=f"tender-{i}",
                title=f"Tender {i}",
                estimated_value=Decimal("100000"),
                contracting_authority_id=1,
                publication_date=datetime.utcnow(),
                bids=[TenderBid(
                    id=f"bid-{i}",
                    bid_amount=Decimal("95000"),
                    status="VALID"
                )] if i == 0 else [  # First tender has single bidder
                    TenderBid(id=f"bid-{i}-1", bid_amount=Decimal("95000"), status="VALID"),
                    TenderBid(id=f"bid-{i}-2", bid_amount=Decimal("96000"), status="VALID")
                ]
            )
            tenders.append(tender)
        
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Act
        results = detector.analyze_batch(tenders, mock_db)
        
        # Assert
        assert len(results) == 3
        assert results[0].risk_score > 0  # Single bidder
        assert results[1].risk_score < results[0].risk_score  # Multiple bidders
        assert results[2].risk_score < results[0].risk_score  # Multiple bidders
    
    def test_algorithm_info(self, detector):
        """Test algorithm info retrieval"""
        
        # Act
        info = detector.get_algorithm_info()
        
        # Assert
        assert info["name"] == "Single Bidder Detection"
        assert "version" in info
        assert "description" in info
        assert "risk_factors" in info
        assert "parameters" in info
    
    def test_risk_level_calculation(self, detector):
        """Test risk level calculation"""
        
        # Test different score ranges
        assert detector.get_risk_level(80) == "HIGH"
        assert detector.get_risk_level(50) == "MEDIUM"
        assert detector.get_risk_level(25) == "LOW"
        assert detector.get_risk_level(10) == "MINIMAL"
    
    def test_z_score_calculation(self, detector):
        """Test z-score calculation"""
        
        # Test normal case
        z_score = detector.calculate_z_score(15, 10, 5)
        assert z_score == 1.0
        
        # Test zero standard deviation
        z_score = detector.calculate_z_score(10, 10, 0)
        assert z_score == 0.0
    
    def test_normalize_score(self, detector):
        """Test score normalization"""
        
        # Test normal range
        normalized = detector.normalize_score(0.5, 0, 1)
        assert normalized == 50.0
        
        # Test clamping
        normalized = detector.normalize_score(2.0, 0, 1)
        assert normalized == 100.0
        
        normalized = detector.normalize_score(-1.0, 0, 1)
        assert normalized == 0.0
    
    def test_open_procedure_amplification(self, detector, sample_tender, sample_company, mock_db):
        """Test risk amplification for open procedures with single bidder"""
        
        # Arrange
        sample_tender.tender_type = "OPEN"
        sample_tender.procedure_type = "OPEN"
        sample_tender.bids = [TenderBid(
            id="bid-1",
            tender=sample_tender,
            company=sample_company,
            bid_amount=Decimal("95000"),
            status="VALID",
            is_winner=True
        )]
        
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Act
        result = detector.analyze_tender(sample_tender, mock_db)
        
        # Assert
        assert result.risk_score > 60  # Should be amplified
        assert result.detailed_analysis["risk_factors"]["open_procedure_single_bidder"] == True
    
    def test_frequent_single_bidder_authority(self, detector, sample_tender, sample_company, mock_db):
        """Test detection of authorities with frequent single bidder patterns"""
        
        # Arrange
        sample_tender.bids = [TenderBid(
            id="bid-1",
            tender=sample_tender,
            company=sample_company,
            bid_amount=Decimal("95000"),
            status="VALID",
            is_winner=True
        )]
        
        # Mock historical data showing frequent single bidder pattern
        historical_tenders = []
        for i in range(10):
            historical_tender = Tender(
                id=f"hist-{i}",
                contracting_authority_id=1,
                publication_date=datetime.utcnow() - timedelta(days=30 + i),
                bids=[TenderBid(id=f"hist-bid-{i}", bid_amount=Decimal("10000"))]  # All single bidder
            )
            historical_tenders.append(historical_tender)
        
        mock_db.query.return_value.filter.return_value.all.return_value = historical_tenders
        
        # Act
        result = detector.analyze_tender(sample_tender, mock_db)
        
        # Assert
        assert result.risk_score > 70  # Should be high risk
        assert "FREQUENT_SINGLE_BIDDER_AUTHORITY" in result.risk_flags
        assert result.detailed_analysis["historical_context"]["single_bidder_rate"] > 0.5


@pytest.mark.integration
class TestSingleBidderDetectorIntegration:
    """Integration tests for SingleBidderDetector"""
    
    def test_real_database_integration(self, detector, db_session):
        """Test with real database (requires test database setup)"""
        # This would require actual database setup
        # Implementation depends on test database configuration
        pass
    
    def test_performance_with_large_dataset(self, detector, mock_db):
        """Test performance with large dataset"""
        
        # Arrange
        tenders = []
        for i in range(1000):
            tender = Tender(
                id=f"tender-{i}",
                title=f"Tender {i}",
                estimated_value=Decimal("100000"),
                contracting_authority_id=1,
                publication_date=datetime.utcnow(),
                bids=[TenderBid(
                    id=f"bid-{i}",
                    bid_amount=Decimal("95000"),
                    status="VALID"
                )]
            )
            tenders.append(tender)
        
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Act
        start_time = datetime.utcnow()
        results = detector.analyze_batch(tenders, mock_db)
        end_time = datetime.utcnow()
        
        # Assert
        assert len(results) == 1000
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time < 60  # Should complete within 60 seconds