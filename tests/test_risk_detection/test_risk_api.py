"""
Tests for Risk Analysis API Endpoints
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.db.models import User, Tender, TenderRiskScore, ContractingAuthority
from app.services.risk_detection.base import RiskDetectionResult


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create mock user"""
    return User(
        id="test-user-id",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True
    )


@pytest.fixture
def mock_tender():
    """Create mock tender"""
    authority = ContractingAuthority(
        id=1,
        name="Test Authority",
        county="BUCHAREST"
    )
    
    return Tender(
        id="test-tender-id",
        title="Test Tender",
        estimated_value=Decimal("100000"),
        contracting_authority=authority,
        publication_date=datetime.utcnow(),
        bids=[]
    )


@pytest.fixture
def mock_risk_result():
    """Create mock risk analysis result"""
    return RiskDetectionResult(
        risk_score=65.0,
        risk_level="MEDIUM",
        risk_flags=["SINGLE_BIDDER", "PRICE_ANOMALY"],
        detailed_analysis={
            "individual_scores": {
                "single_bidder": 70.0,
                "price_anomaly": 30.0,
                "frequent_winner": 50.0,
                "geographic_clustering": 20.0
            },
            "algorithm_weights": {
                "single_bidder": 0.25,
                "price_anomaly": 0.30,
                "frequent_winner": 0.25,
                "geographic_clustering": 0.20
            }
        },
        confidence=0.8
    )


class TestRiskAnalysisEndpoints:
    """Test risk analysis API endpoints"""
    
    @patch('app.auth.security.get_current_user')
    @patch('app.core.database.get_db')
    @patch('app.api.v1.endpoints.risk.get_risk_analyzer')
    def test_analyze_tender_success(self, mock_get_analyzer, mock_get_db, mock_get_user, 
                                   client, mock_user, mock_tender, mock_risk_result):
        """Test successful tender analysis"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_tender
        
        mock_analyzer = Mock()
        mock_analyzer.analyze_tender.return_value = mock_risk_result
        mock_get_analyzer.return_value = mock_analyzer
        
        # Act
        response = client.post(
            "/api/v1/risk/analyze",
            json={
                "tender_id": "test-tender-id",
                "force_refresh": False
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tender_id"] == "test-tender-id"
        assert data["risk_score"] == 65.0
        assert data["risk_level"] == "MEDIUM"
        assert "SINGLE_BIDDER" in data["risk_flags"]
        assert data["confidence"] == 0.8
    
    @patch('app.auth.security.get_current_user')
    @patch('app.core.database.get_db')
    def test_analyze_tender_not_found(self, mock_get_db, mock_get_user, client, mock_user):
        """Test analysis of non-existent tender"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        response = client.post(
            "/api/v1/risk/analyze",
            json={
                "tender_id": "non-existent-tender",
                "force_refresh": False
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Tender not found" in response.json()["detail"]
    
    @patch('app.auth.security.get_current_user')
    @patch('app.core.database.get_db')
    @patch('app.api.v1.endpoints.risk.get_risk_analyzer')
    def test_get_risk_statistics(self, mock_get_analyzer, mock_get_db, mock_get_user, 
                                client, mock_user):
        """Test getting risk statistics"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_analyzer = Mock()
        mock_stats = {
            "period_days": 30,
            "total_analyzed": 100,
            "avg_overall_score": 45.5,
            "risk_level_distribution": {
                "counts": {"HIGH": 10, "MEDIUM": 30, "LOW": 60},
                "percentages": {"HIGH": 10.0, "MEDIUM": 30.0, "LOW": 60.0}
            },
            "algorithm_performance": {
                "single_bidder": {"avg_score": 40.0, "max_score": 80.0},
                "price_anomaly": {"avg_score": 35.0, "max_score": 75.0}
            },
            "top_risk_flags": [("SINGLE_BIDDER", 25), ("PRICE_ANOMALY", 20)],
            "high_risk_rate": 10.0,
            "analysis_date": datetime.utcnow().isoformat()
        }
        mock_analyzer.get_risk_statistics.return_value = mock_stats
        mock_get_analyzer.return_value = mock_analyzer
        
        # Act
        response = client.get("/api/v1/risk/statistics?days=30")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["period_days"] == 30
        assert data["total_analyzed"] == 100
        assert data["avg_overall_score"] == 45.5
        assert data["high_risk_rate"] == 10.0
    
    @patch('app.auth.security.get_current_user')
    @patch('app.core.database.get_db')
    @patch('app.api.v1.endpoints.risk.get_risk_analyzer')
    def test_get_high_risk_tenders(self, mock_get_analyzer, mock_get_db, mock_get_user, 
                                  client, mock_user):
        """Test getting high-risk tenders"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_analyzer = Mock()
        mock_high_risk_tenders = [
            {
                "tender_id": "tender-1",
                "title": "High Risk Tender 1",
                "contracting_authority": "Authority 1",
                "estimated_value": 500000.0,
                "overall_risk_score": 85.0,
                "risk_level": "HIGH",
                "risk_flags": ["SINGLE_BIDDER", "HIGH_VALUE"],
                "analysis_date": datetime.utcnow().isoformat(),
                "publication_date": datetime.utcnow().isoformat()
            },
            {
                "tender_id": "tender-2",
                "title": "High Risk Tender 2",
                "contracting_authority": "Authority 2",
                "estimated_value": 300000.0,
                "overall_risk_score": 80.0,
                "risk_level": "HIGH",
                "risk_flags": ["PRICE_ANOMALY", "HIGH_WIN_RATE"],
                "analysis_date": datetime.utcnow().isoformat(),
                "publication_date": datetime.utcnow().isoformat()
            }
        ]
        mock_analyzer.get_high_risk_tenders.return_value = mock_high_risk_tenders
        mock_get_analyzer.return_value = mock_analyzer
        
        # Act
        response = client.get("/api/v1/risk/high-risk-tenders?limit=10")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["tender_id"] == "tender-1"
        assert data[0]["risk_level"] == "HIGH"
        assert data[0]["overall_risk_score"] == 85.0
    
    @patch('app.auth.security.get_current_user')
    @patch('app.core.database.get_db')
    @patch('app.api.v1.endpoints.risk.get_risk_analyzer')
    def test_get_algorithm_performance(self, mock_get_analyzer, mock_get_db, mock_get_user, 
                                      client, mock_user):
        """Test getting algorithm performance"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_analyzer = Mock()
        mock_performance = {
            "single_bidder": {
                "avg_score": 40.0,
                "max_score": 80.0,
                "min_score": 10.0,
                "total_analyses": 100,
                "high_risk_count": 20,
                "medium_risk_count": 30,
                "low_risk_count": 50
            },
            "price_anomaly": {
                "avg_score": 35.0,
                "max_score": 75.0,
                "min_score": 5.0,
                "total_analyses": 100,
                "high_risk_count": 15,
                "medium_risk_count": 35,
                "low_risk_count": 50
            }
        }
        mock_analyzer.get_algorithm_performance.return_value = mock_performance
        mock_get_analyzer.return_value = mock_analyzer
        
        # Act
        response = client.get("/api/v1/risk/algorithm-performance")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "algorithm_performance" in data
        assert "single_bidder" in data["algorithm_performance"]
        assert "price_anomaly" in data["algorithm_performance"]
    
    @patch('app.auth.security.get_current_user')
    @patch('app.api.v1.endpoints.risk.get_risk_analyzer')
    def test_get_system_info(self, mock_get_analyzer, mock_get_user, client, mock_user):
        """Test getting system information"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        
        mock_analyzer = Mock()
        mock_system_info = {
            "system_version": "1.0.0",
            "composite_scorer_info": {
                "name": "Composite Risk Scorer",
                "version": "1.0.0",
                "description": "Combines multiple risk detection algorithms"
            },
            "configuration": {
                "single_bidder_threshold": 0.8,
                "price_anomaly_z_threshold": 2.0,
                "high_risk_threshold": 70.0
            }
        }
        mock_analyzer.get_system_info.return_value = mock_system_info
        mock_get_analyzer.return_value = mock_analyzer
        
        # Act
        response = client.get("/api/v1/risk/system-info")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "system_info" in data
        assert data["system_info"]["system_version"] == "1.0.0"
    
    @patch('app.auth.security.get_current_user')
    @patch('app.core.database.get_db')
    @patch('app.api.v1.endpoints.risk.get_risk_analyzer')
    def test_reanalyze_tender(self, mock_get_analyzer, mock_get_db, mock_get_user, 
                             client, mock_user, mock_risk_result):
        """Test reanalyzing a tender"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_analyzer = Mock()
        mock_analyzer.reanalyze_tender.return_value = mock_risk_result
        mock_get_analyzer.return_value = mock_analyzer
        
        # Act
        response = client.post("/api/v1/risk/reanalyze/test-tender-id")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tender_id"] == "test-tender-id"
        assert data["risk_score"] == 65.0
        assert data["risk_level"] == "MEDIUM"
        assert "analysis_date" in data
    
    @patch('app.auth.security.get_current_user')
    @patch('app.core.database.get_db')
    @patch('app.api.v1.endpoints.risk.get_risk_analyzer')
    def test_reanalyze_tender_not_found(self, mock_get_analyzer, mock_get_db, mock_get_user, 
                                       client, mock_user):
        """Test reanalyzing non-existent tender"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_analyzer = Mock()
        mock_analyzer.reanalyze_tender.side_effect = ValueError("Tender with ID non-existent not found")
        mock_get_analyzer.return_value = mock_analyzer
        
        # Act
        response = client.post("/api/v1/risk/reanalyze/non-existent")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Tender with ID non-existent not found" in response.json()["detail"]
    
    @patch('app.auth.security.get_current_user')
    @patch('app.services.tasks.risk_analysis.analyze_new_tenders.delay')
    def test_trigger_batch_analysis(self, mock_task, mock_get_user, client, mock_user):
        """Test triggering batch analysis"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        mock_task.return_value = None
        
        # Act
        response = client.post("/api/v1/risk/batch-analyze?batch_size=50")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Batch analysis task scheduled"
        assert data["batch_size"] == 50
        mock_task.assert_called_once_with(50)
    
    @patch('app.auth.security.get_current_user')
    @patch('app.services.tasks.risk_analysis.periodic_risk_assessment.delay')
    def test_trigger_periodic_assessment(self, mock_task, mock_get_user, client, mock_user):
        """Test triggering periodic assessment"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        mock_task.return_value = None
        
        # Act
        response = client.post("/api/v1/risk/periodic-assessment?days_lookback=30")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Periodic assessment task scheduled"
        assert data["days_lookback"] == 30
        mock_task.assert_called_once_with(30)
    
    @patch('app.auth.security.get_current_user')
    @patch('app.api.v1.endpoints.risk.get_risk_analyzer')
    def test_get_risk_configuration(self, mock_get_analyzer, mock_get_user, client, mock_user):
        """Test getting risk configuration"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        
        mock_analyzer = Mock()
        mock_config = Mock()
        mock_config.single_bidder_threshold = 0.8
        mock_config.price_anomaly_z_threshold = 2.0
        mock_config.high_risk_threshold = 70.0
        mock_config.medium_risk_threshold = 40.0
        mock_config.low_risk_threshold = 20.0
        mock_analyzer.config = mock_config
        mock_get_analyzer.return_value = mock_analyzer
        
        # Act
        response = client.get("/api/v1/risk/configuration")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "configuration" in data
        assert data["configuration"]["single_bidder_threshold"] == 0.8
        assert data["configuration"]["high_risk_threshold"] == 70.0
    
    @patch('app.auth.security.get_current_user')
    @patch('app.api.v1.endpoints.risk.get_risk_analyzer')
    def test_update_risk_configuration(self, mock_get_analyzer, mock_get_user, client, mock_user):
        """Test updating risk configuration"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        
        mock_analyzer = Mock()
        mock_analyzer.validate_configuration.return_value = {"valid": True, "issues": [], "warnings": []}
        mock_analyzer.update_configuration.return_value = None
        mock_get_analyzer.return_value = mock_analyzer
        
        # Act
        response = client.put(
            "/api/v1/risk/configuration",
            json={
                "single_bidder_threshold": 0.9,
                "high_risk_threshold": 75.0
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Configuration updated successfully"
        assert "single_bidder_threshold" in data["updated_fields"]
        assert "high_risk_threshold" in data["updated_fields"]
    
    @patch('app.auth.security.get_current_user')
    @patch('app.api.v1.endpoints.risk.get_risk_analyzer')
    def test_validate_risk_configuration(self, mock_get_analyzer, mock_get_user, client, mock_user):
        """Test validating risk configuration"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        
        mock_analyzer = Mock()
        mock_validation = {
            "valid": True,
            "issues": [],
            "warnings": ["Algorithm weights sum to 1.01, not 1.0"]
        }
        mock_analyzer.validate_configuration.return_value = mock_validation
        mock_get_analyzer.return_value = mock_analyzer
        
        # Act
        response = client.post("/api/v1/risk/validate-configuration")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["validation_result"]["valid"] == True
        assert len(data["validation_result"]["warnings"]) == 1
    
    @patch('app.auth.security.get_current_user')
    @patch('app.core.database.get_db')
    def test_get_tender_risk_history(self, mock_get_db, mock_get_user, client, mock_user, mock_tender):
        """Test getting tender risk history"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_tender
        
        # Mock risk history
        mock_history = [
            Mock(
                analysis_date=datetime.utcnow(),
                overall_risk_score=Decimal("65.0"),
                risk_level="MEDIUM",
                single_bidder_risk=Decimal("70.0"),
                price_anomaly_risk=Decimal("30.0"),
                frequency_risk=Decimal("50.0"),
                geographic_risk=Decimal("20.0"),
                risk_flags=["SINGLE_BIDDER", "PRICE_ANOMALY"],
                analysis_version="1.0.0"
            )
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_history
        
        # Act
        response = client.get("/api/v1/risk/tender/test-tender-id/risk-history")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tender_id"] == "test-tender-id"
        assert data["tender_title"] == "Test Tender"
        assert len(data["risk_history"]) == 1
        assert data["risk_history"][0]["risk_level"] == "MEDIUM"
    
    @patch('app.auth.security.get_current_user')
    @patch('app.core.database.get_db')
    @patch('app.api.v1.endpoints.risk.get_risk_analyzer')
    def test_get_risk_summary_report(self, mock_get_analyzer, mock_get_db, mock_get_user, 
                                    client, mock_user):
        """Test getting risk summary report"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_analyzer = Mock()
        mock_stats = {
            "period_days": 30,
            "total_analyzed": 100,
            "avg_overall_score": 45.5,
            "high_risk_rate": 10.0,
            "analysis_date": datetime.utcnow().isoformat()
        }
        mock_high_risk_tenders = [
            {
                "tender_id": "tender-1",
                "title": "High Risk Tender",
                "overall_risk_score": 85.0,
                "risk_level": "HIGH"
            }
        ]
        mock_algorithm_performance = {
            "single_bidder": {"avg_score": 40.0}
        }
        
        mock_analyzer.get_risk_statistics.return_value = mock_stats
        mock_analyzer.get_high_risk_tenders.return_value = mock_high_risk_tenders
        mock_analyzer.get_algorithm_performance.return_value = mock_algorithm_performance
        mock_get_analyzer.return_value = mock_analyzer
        
        # Act
        response = client.get("/api/v1/risk/reports/summary?days=30")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "report" in data
        assert data["report"]["report_type"] == "summary"
        assert data["report"]["period_days"] == 30
        assert "statistics" in data["report"]
        assert "top_high_risk_tenders" in data["report"]
        assert "recommendations" in data["report"]


class TestRiskApiValidation:
    """Test API validation and error handling"""
    
    @patch('app.auth.security.get_current_user')
    def test_analyze_tender_invalid_request(self, mock_get_user, client, mock_user):
        """Test analysis with invalid request data"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        
        # Act
        response = client.post(
            "/api/v1/risk/analyze",
            json={}  # Missing required tender_id
        )
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.auth.security.get_current_user')
    def test_get_statistics_invalid_days(self, mock_get_user, client, mock_user):
        """Test getting statistics with invalid days parameter"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        
        # Act
        response = client.get("/api/v1/risk/statistics?days=0")  # Invalid: days must be >= 1
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.auth.security.get_current_user')
    def test_update_configuration_invalid_values(self, mock_get_user, client, mock_user):
        """Test updating configuration with invalid values"""
        
        # Arrange
        mock_get_user.return_value = mock_user
        
        # Act
        response = client.put(
            "/api/v1/risk/configuration",
            json={
                "single_bidder_threshold": 1.5,  # Invalid: must be <= 1.0
                "high_risk_threshold": -10.0     # Invalid: must be >= 0
            }
        )
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoints"""
        
        # Act
        response = client.get("/api/v1/risk/statistics")
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestRiskApiIntegration:
    """Integration tests for Risk API"""
    
    def test_full_analysis_workflow(self, client):
        """Test complete analysis workflow"""
        # This would test the full workflow from tender creation to risk analysis
        # Requires proper test database setup
        pass
    
    def test_concurrent_analysis_requests(self, client):
        """Test handling of concurrent analysis requests"""
        # This would test the system's ability to handle multiple simultaneous requests
        pass
    
    def test_api_performance_under_load(self, client):
        """Test API performance under load"""
        # This would test the API's performance with many requests
        pass