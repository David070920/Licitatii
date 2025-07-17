"""
Tests for Composite Risk Scorer
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch

from app.services.risk_detection.composite_risk_scorer import CompositeRiskScorer
from app.services.risk_detection.base import RiskDetectionConfig, RiskDetectionResult
from app.db.models import Tender, TenderRiskScore, Company, ContractingAuthority


class TestCompositeRiskScorer:
    """Test cases for CompositeRiskScorer"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return RiskDetectionConfig()
    
    @pytest.fixture
    def scorer(self, config):
        """Create CompositeRiskScorer instance"""
        return CompositeRiskScorer(config)
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock()
    
    @pytest.fixture
    def sample_tender(self):
        """Create sample tender"""
        authority = ContractingAuthority(
            id=1,
            name="Test Authority",
            county="BUCHAREST"
        )
        
        return Tender(
            id="test-tender-1",
            title="Test Tender",
            estimated_value=Decimal("100000"),
            contracting_authority=authority,
            publication_date=datetime.utcnow(),
            bids=[]
        )
    
    @pytest.fixture
    def sample_results(self):
        """Create sample algorithm results"""
        return {
            "single_bidder": RiskDetectionResult(
                risk_score=70.0,
                risk_level="HIGH",
                risk_flags=["SINGLE_BIDDER", "HIGH_VALUE_SINGLE_BIDDER"],
                detailed_analysis={"algorithm": "single_bidder"},
                confidence=0.9
            ),
            "price_anomaly": RiskDetectionResult(
                risk_score=30.0,
                risk_level="MEDIUM",
                risk_flags=["PRICE_ANOMALY"],
                detailed_analysis={"algorithm": "price_anomaly"},
                confidence=0.8
            ),
            "frequent_winner": RiskDetectionResult(
                risk_score=50.0,
                risk_level="MEDIUM",
                risk_flags=["HIGH_WIN_RATE"],
                detailed_analysis={"algorithm": "frequent_winner"},
                confidence=0.7
            ),
            "geographic": RiskDetectionResult(
                risk_score=20.0,
                risk_level="LOW",
                risk_flags=["LOCAL_CONCENTRATION"],
                detailed_analysis={"algorithm": "geographic"},
                confidence=0.6
            )
        }
    
    def test_composite_score_calculation(self, scorer, sample_tender, sample_results, mock_db):
        """Test composite score calculation"""
        
        # Mock individual detectors
        with patch.object(scorer.single_bidder_detector, 'analyze_tender', return_value=sample_results["single_bidder"]), \
             patch.object(scorer.price_anomaly_detector, 'analyze_tender', return_value=sample_results["price_anomaly"]), \
             patch.object(scorer.frequent_winner_detector, 'analyze_tender', return_value=sample_results["frequent_winner"]), \
             patch.object(scorer.geographic_clustering_detector, 'analyze_tender', return_value=sample_results["geographic"]):
            
            # Act
            result = scorer.analyze_tender(sample_tender, mock_db)
            
            # Assert
            assert result.risk_score > 0
            assert result.risk_level in ["HIGH", "MEDIUM", "LOW", "MINIMAL"]
            assert len(result.risk_flags) > 0
            assert "individual_scores" in result.detailed_analysis
            assert "algorithm_weights" in result.detailed_analysis
            assert "confidence" in result.detailed_analysis
    
    def test_risk_amplification_multiple_high_risk(self, scorer, sample_tender, mock_db):
        """Test risk amplification when multiple algorithms detect high risk"""
        
        # Create results with multiple high-risk algorithms
        high_risk_results = {
            "single_bidder": RiskDetectionResult(
                risk_score=80.0,
                risk_level="HIGH",
                risk_flags=["SINGLE_BIDDER"],
                detailed_analysis={"algorithm": "single_bidder"},
                confidence=0.9
            ),
            "price_anomaly": RiskDetectionResult(
                risk_score=75.0,
                risk_level="HIGH",
                risk_flags=["PRICE_ANOMALY"],
                detailed_analysis={"algorithm": "price_anomaly"},
                confidence=0.8
            ),
            "frequent_winner": RiskDetectionResult(
                risk_score=85.0,
                risk_level="HIGH",
                risk_flags=["HIGH_WIN_RATE"],
                detailed_analysis={"algorithm": "frequent_winner"},
                confidence=0.9
            ),
            "geographic": RiskDetectionResult(
                risk_score=20.0,
                risk_level="LOW",
                risk_flags=[],
                detailed_analysis={"algorithm": "geographic"},
                confidence=0.6
            )
        }
        
        with patch.object(scorer.single_bidder_detector, 'analyze_tender', return_value=high_risk_results["single_bidder"]), \
             patch.object(scorer.price_anomaly_detector, 'analyze_tender', return_value=high_risk_results["price_anomaly"]), \
             patch.object(scorer.frequent_winner_detector, 'analyze_tender', return_value=high_risk_results["frequent_winner"]), \
             patch.object(scorer.geographic_clustering_detector, 'analyze_tender', return_value=high_risk_results["geographic"]):
            
            # Act
            result = scorer.analyze_tender(sample_tender, mock_db)
            
            # Assert
            assert result.risk_score > 80  # Should be amplified
            assert result.detailed_analysis["risk_amplification_applied"] == True
    
    def test_critical_flag_combination_amplification(self, scorer, sample_tender, mock_db):
        """Test amplification for critical flag combinations"""
        
        # Create results with critical flag combination
        critical_results = {
            "single_bidder": RiskDetectionResult(
                risk_score=60.0,
                risk_level="MEDIUM",
                risk_flags=["SINGLE_BIDDER"],
                detailed_analysis={"algorithm": "single_bidder"},
                confidence=0.9
            ),
            "price_anomaly": RiskDetectionResult(
                risk_score=30.0,
                risk_level="MEDIUM",
                risk_flags=[],
                detailed_analysis={"algorithm": "price_anomaly"},
                confidence=0.8
            ),
            "frequent_winner": RiskDetectionResult(
                risk_score=50.0,
                risk_level="MEDIUM",
                risk_flags=["HIGH_WIN_RATE"],
                detailed_analysis={"algorithm": "frequent_winner"},
                confidence=0.7
            ),
            "geographic": RiskDetectionResult(
                risk_score=20.0,
                risk_level="LOW",
                risk_flags=[],
                detailed_analysis={"algorithm": "geographic"},
                confidence=0.6
            )
        }
        
        with patch.object(scorer.single_bidder_detector, 'analyze_tender', return_value=critical_results["single_bidder"]), \
             patch.object(scorer.price_anomaly_detector, 'analyze_tender', return_value=critical_results["price_anomaly"]), \
             patch.object(scorer.frequent_winner_detector, 'analyze_tender', return_value=critical_results["frequent_winner"]), \
             patch.object(scorer.geographic_clustering_detector, 'analyze_tender', return_value=critical_results["geographic"]):
            
            # Act
            result = scorer.analyze_tender(sample_tender, mock_db)
            
            # Assert
            # Should be amplified due to SINGLE_BIDDER + HIGH_WIN_RATE combination
            assert result.risk_score > 45  # Base weighted score would be around 42.5
            assert result.detailed_analysis["risk_amplification_applied"] == True
    
    def test_confidence_calculation(self, scorer, sample_tender, sample_results, mock_db):
        """Test confidence calculation"""
        
        with patch.object(scorer.single_bidder_detector, 'analyze_tender', return_value=sample_results["single_bidder"]), \
             patch.object(scorer.price_anomaly_detector, 'analyze_tender', return_value=sample_results["price_anomaly"]), \
             patch.object(scorer.frequent_winner_detector, 'analyze_tender', return_value=sample_results["frequent_winner"]), \
             patch.object(scorer.geographic_clustering_detector, 'analyze_tender', return_value=sample_results["geographic"]):
            
            # Act
            result = scorer.analyze_tender(sample_tender, mock_db)
            
            # Assert
            assert 0.0 <= result.confidence <= 1.0
            assert result.detailed_analysis["confidence"] == result.confidence
    
    def test_batch_analysis(self, scorer, mock_db):
        """Test batch analysis"""
        
        # Create sample tenders
        tenders = []
        for i in range(3):
            tender = Tender(
                id=f"tender-{i}",
                title=f"Tender {i}",
                estimated_value=Decimal("100000"),
                publication_date=datetime.utcnow(),
                bids=[]
            )
            tenders.append(tender)
        
        # Mock individual detector batch methods
        mock_results = [
            RiskDetectionResult(
                risk_score=50.0,
                risk_level="MEDIUM",
                risk_flags=["TEST_FLAG"],
                detailed_analysis={"algorithm": "test"},
                confidence=0.8
            )
        ] * 3
        
        with patch.object(scorer.single_bidder_detector, 'analyze_batch', return_value=mock_results), \
             patch.object(scorer.price_anomaly_detector, 'analyze_batch', return_value=mock_results), \
             patch.object(scorer.frequent_winner_detector, 'analyze_batch', return_value=mock_results), \
             patch.object(scorer.geographic_clustering_detector, 'analyze_batch', return_value=mock_results):
            
            # Act
            results = scorer.analyze_batch(tenders, mock_db)
            
            # Assert
            assert len(results) == 3
            for result in results:
                assert result.risk_score > 0
                assert result.risk_level in ["HIGH", "MEDIUM", "LOW", "MINIMAL"]
    
    def test_save_risk_score(self, scorer, sample_tender, sample_results, mock_db):
        """Test saving risk score to database"""
        
        # Create composite result
        composite_result = RiskDetectionResult(
            risk_score=65.0,
            risk_level="MEDIUM",
            risk_flags=["SINGLE_BIDDER", "PRICE_ANOMALY"],
            detailed_analysis={
                "individual_scores": {
                    "single_bidder": 70.0,
                    "price_anomaly": 30.0,
                    "frequent_winner": 50.0,
                    "geographic_clustering": 20.0
                }
            },
            confidence=0.8
        )
        
        # Mock database operations
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        # Act
        risk_score = scorer.save_risk_score(sample_tender, composite_result, mock_db)
        
        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert risk_score.overall_risk_score == Decimal("65.0")
        assert risk_score.risk_level == "MEDIUM"
    
    def test_update_algorithm_weights(self, scorer):
        """Test updating algorithm weights"""
        
        # Act
        new_weights = {
            "single_bidder_weight": 0.3,
            "price_anomaly_weight": 0.4
        }
        scorer.update_algorithm_weights(new_weights)
        
        # Assert
        assert scorer.weights["single_bidder"] == 0.3
        assert scorer.weights["price_anomaly"] == 0.4
        # Check that weights are normalized
        assert abs(sum(scorer.weights.values()) - 1.0) < 0.001
    
    def test_update_algorithm_weights_invalid(self, scorer):
        """Test updating algorithm weights with invalid values"""
        
        # Act & Assert
        with pytest.raises(ValueError):
            scorer.update_algorithm_weights({"single_bidder_weight": 1.5})  # > 1.0
        
        with pytest.raises(ValueError):
            scorer.update_algorithm_weights({"single_bidder_weight": -0.1})  # < 0.0
    
    def test_get_algorithm_info(self, scorer):
        """Test getting algorithm information"""
        
        # Act
        info = scorer.get_algorithm_info()
        
        # Assert
        assert info["name"] == "Composite Risk Scorer"
        assert "version" in info
        assert "description" in info
        assert "component_algorithms" in info
        assert "scoring_methodology" in info
        assert "current_weights" in info
        assert len(info["component_algorithms"]) == 4
    
    def test_generate_risk_summary(self, scorer, sample_results):
        """Test generating risk summary"""
        
        # Create composite result
        composite_result = RiskDetectionResult(
            risk_score=65.0,
            risk_level="MEDIUM",
            risk_flags=["SINGLE_BIDDER", "HIGH_WIN_RATE", "PRICE_ANOMALY"],
            detailed_analysis={
                "individual_scores": {
                    "single_bidder": 70.0,
                    "price_anomaly": 30.0,
                    "frequent_winner": 50.0,
                    "geographic_clustering": 20.0
                }
            },
            confidence=0.8
        )
        
        # Act
        summary = scorer.generate_risk_summary(composite_result)
        
        # Assert
        assert summary["overall_risk_score"] == 65.0
        assert summary["risk_level"] == "MEDIUM"
        assert summary["confidence"] == 0.8
        assert "primary_risk_factors" in summary
        assert "total_risk_flags" in summary
        assert "critical_flags" in summary
        assert "recommendations" in summary
        assert len(summary["primary_risk_factors"]) > 0
    
    def test_risk_level_determination(self, scorer, sample_tender, mock_db):
        """Test risk level determination based on score"""
        
        # Test different score ranges
        test_cases = [
            (90.0, "HIGH"),
            (65.0, "MEDIUM"),
            (25.0, "LOW"),
            (10.0, "MINIMAL")
        ]
        
        for score, expected_level in test_cases:
            # Create result with specific score
            mock_result = RiskDetectionResult(
                risk_score=score,
                risk_level=expected_level,
                risk_flags=[],
                detailed_analysis={"algorithm": "test"},
                confidence=0.8
            )
            
            with patch.object(scorer.single_bidder_detector, 'analyze_tender', return_value=mock_result), \
                 patch.object(scorer.price_anomaly_detector, 'analyze_tender', return_value=mock_result), \
                 patch.object(scorer.frequent_winner_detector, 'analyze_tender', return_value=mock_result), \
                 patch.object(scorer.geographic_clustering_detector, 'analyze_tender', return_value=mock_result):
                
                # Act
                result = scorer.analyze_tender(sample_tender, mock_db)
                
                # Assert
                assert scorer._get_composite_risk_level(score) == expected_level
    
    def test_flag_deduplication(self, scorer, sample_tender, mock_db):
        """Test that duplicate flags are removed"""
        
        # Create results with duplicate flags
        duplicate_results = {
            "single_bidder": RiskDetectionResult(
                risk_score=50.0,
                risk_level="MEDIUM",
                risk_flags=["SINGLE_BIDDER", "HIGH_VALUE"],
                detailed_analysis={"algorithm": "single_bidder"},
                confidence=0.9
            ),
            "price_anomaly": RiskDetectionResult(
                risk_score=30.0,
                risk_level="MEDIUM",
                risk_flags=["HIGH_VALUE", "PRICE_ANOMALY"],  # HIGH_VALUE is duplicate
                detailed_analysis={"algorithm": "price_anomaly"},
                confidence=0.8
            ),
            "frequent_winner": RiskDetectionResult(
                risk_score=40.0,
                risk_level="MEDIUM",
                risk_flags=["HIGH_WIN_RATE"],
                detailed_analysis={"algorithm": "frequent_winner"},
                confidence=0.7
            ),
            "geographic": RiskDetectionResult(
                risk_score=20.0,
                risk_level="LOW",
                risk_flags=[],
                detailed_analysis={"algorithm": "geographic"},
                confidence=0.6
            )
        }
        
        with patch.object(scorer.single_bidder_detector, 'analyze_tender', return_value=duplicate_results["single_bidder"]), \
             patch.object(scorer.price_anomaly_detector, 'analyze_tender', return_value=duplicate_results["price_anomaly"]), \
             patch.object(scorer.frequent_winner_detector, 'analyze_tender', return_value=duplicate_results["frequent_winner"]), \
             patch.object(scorer.geographic_clustering_detector, 'analyze_tender', return_value=duplicate_results["geographic"]):
            
            # Act
            result = scorer.analyze_tender(sample_tender, mock_db)
            
            # Assert
            assert result.risk_flags.count("HIGH_VALUE") == 1  # Should appear only once
            assert "SINGLE_BIDDER" in result.risk_flags
            assert "PRICE_ANOMALY" in result.risk_flags
            assert "HIGH_WIN_RATE" in result.risk_flags
    
    def test_scoring_methodology_info(self, scorer):
        """Test scoring methodology information"""
        
        # Act
        methodology = scorer._get_scoring_methodology()
        
        # Assert
        assert "description" in methodology
        assert "algorithms" in methodology
        assert "risk_thresholds" in methodology
        assert "amplification_factors" in methodology
        assert len(methodology["algorithms"]) == 4
        
        # Check algorithm weights
        for algorithm_info in methodology["algorithms"].values():
            assert "weight" in algorithm_info
            assert "description" in algorithm_info


@pytest.mark.integration
class TestCompositeRiskScorerIntegration:
    """Integration tests for CompositeRiskScorer"""
    
    def test_end_to_end_scoring(self, scorer, sample_tender, mock_db):
        """Test end-to-end scoring with realistic data"""
        
        # This would test the actual integration with all algorithms
        # using more realistic data scenarios
        pass
    
    def test_performance_benchmark(self, scorer, mock_db):
        """Test performance with realistic load"""
        
        # Create large batch of tenders
        tenders = []
        for i in range(100):
            tender = Tender(
                id=f"perf-tender-{i}",
                title=f"Performance Test Tender {i}",
                estimated_value=Decimal("100000"),
                publication_date=datetime.utcnow(),
                bids=[]
            )
            tenders.append(tender)
        
        # Mock all detector methods
        mock_result = RiskDetectionResult(
            risk_score=50.0,
            risk_level="MEDIUM",
            risk_flags=["TEST_FLAG"],
            detailed_analysis={"algorithm": "test"},
            confidence=0.8
        )
        
        with patch.object(scorer.single_bidder_detector, 'analyze_batch', return_value=[mock_result] * 100), \
             patch.object(scorer.price_anomaly_detector, 'analyze_batch', return_value=[mock_result] * 100), \
             patch.object(scorer.frequent_winner_detector, 'analyze_batch', return_value=[mock_result] * 100), \
             patch.object(scorer.geographic_clustering_detector, 'analyze_batch', return_value=[mock_result] * 100):
            
            # Act
            start_time = datetime.utcnow()
            results = scorer.analyze_batch(tenders, mock_db)
            end_time = datetime.utcnow()
            
            # Assert
            assert len(results) == 100
            processing_time = (end_time - start_time).total_seconds()
            assert processing_time < 30  # Should complete within 30 seconds