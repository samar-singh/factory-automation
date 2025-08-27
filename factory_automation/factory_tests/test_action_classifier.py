"""
Unit tests for Action Classification System
Phase 2 - PLAN-2025-01-TWOTIER
"""

import pytest
from factory_automation.factory_agents.action_classifier import (
    ActionClassifier,
    ActionType,
    ActionCategory,
)
from factory_automation.factory_agents.tools.tool_factory import ToolFactory


class TestActionClassifier:
    """Test the action classification system"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.classifier = ActionClassifier()
    
    def test_irreversible_actions_classification(self):
        """Test that known irreversible actions are classified correctly"""
        irreversible_actions = [
            "send_email_response",
            "send_customer_email",
            "reserve_inventory_final",
            "process_payment",
            "confirm_order",
        ]
        
        for action in irreversible_actions:
            result = self.classifier.classify_action(action)
            assert result == ActionType.IRREVERSIBLE, f"{action} should be irreversible"
            assert self.classifier.is_irreversible(action)
            assert not self.classifier.is_reversible(action)
    
    def test_reversible_actions_classification(self):
        """Test that known reversible actions are classified correctly"""
        reversible_actions = [
            "search_inventory",
            "calculate_price",
            "analyze_email",
            "generate_quotation",
            "create_draft_order",
        ]
        
        for action in reversible_actions:
            result = self.classifier.classify_action(action)
            assert result == ActionType.REVERSIBLE, f"{action} should be reversible"
            assert self.classifier.is_reversible(action)
            assert not self.classifier.is_irreversible(action)
    
    def test_heuristic_classification(self):
        """Test heuristic classification for unknown actions"""
        # Actions with "send" should be irreversible
        assert self.classifier.classify_action("send_notification") == ActionType.IRREVERSIBLE
        assert self.classifier.classify_action("send_alert") == ActionType.IRREVERSIBLE
        
        # Actions with "search" should be reversible
        assert self.classifier.classify_action("search_database") == ActionType.REVERSIBLE
        assert self.classifier.classify_action("search_products") == ActionType.REVERSIBLE
        
        # Actions with "email" should be irreversible
        assert self.classifier.classify_action("email_customer") == ActionType.IRREVERSIBLE
        
        # Actions with "calculate" should be reversible
        assert self.classifier.classify_action("calculate_tax") == ActionType.REVERSIBLE
    
    def test_unknown_action_defaults_to_irreversible(self):
        """Test that unknown actions default to irreversible for safety"""
        unknown_action = "unknown_mysterious_action"
        result = self.classifier.classify_action(unknown_action)
        assert result == ActionType.IRREVERSIBLE, "Unknown actions should default to irreversible"
    
    def test_classification_caching(self):
        """Test that classifications are cached"""
        action = "test_action"
        
        # First classification
        result1 = self.classifier.classify_action(action)
        
        # Second classification should use cache
        result2 = self.classifier.classify_action(action)
        
        assert result1 == result2
        assert action in self.classifier.classification_cache
    
    def test_action_requirements(self):
        """Test getting action requirements"""
        # Irreversible action
        requirements = self.classifier.get_action_requirements("send_email_response")
        assert requirements["requires_approval"] == True
        assert requirements["can_auto_execute"] == False
        assert requirements["can_rollback"] == False
        assert requirements["risk_level"] == "high"
        
        # Reversible action
        requirements = self.classifier.get_action_requirements("search_inventory")
        assert requirements["requires_approval"] == False
        assert requirements["can_auto_execute"] == True
        assert requirements["can_rollback"] == True
        assert requirements["risk_level"] == "low"
    
    def test_bulk_classification(self):
        """Test classifying multiple actions at once"""
        actions = [
            "send_email_response",
            "search_inventory",
            "process_payment",
            "calculate_price",
        ]
        
        results = self.classifier.bulk_classify(actions)
        
        assert results["send_email_response"] == ActionType.IRREVERSIBLE
        assert results["search_inventory"] == ActionType.REVERSIBLE
        assert results["process_payment"] == ActionType.IRREVERSIBLE
        assert results["calculate_price"] == ActionType.REVERSIBLE
    
    def test_statistics(self):
        """Test getting classification statistics"""
        # Classify some actions
        self.classifier.classify_action("send_email_response")
        self.classifier.classify_action("search_inventory")
        
        stats = self.classifier.get_statistics()
        
        assert stats["total_irreversible"] > 0
        assert stats["total_reversible"] > 0
        assert stats["total_classified"] >= 2


class TestToolFactory:
    """Test tool factory classification integration"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.factory = ToolFactory(mode="execute")
    
    def test_tool_classification(self):
        """Test that tools are classified correctly"""
        # Test irreversible tool
        classification = self.factory.classify_tool("send_email_response")
        assert classification == ActionType.IRREVERSIBLE
        assert self.factory.is_tool_irreversible("send_email_response")
        
        # Test reversible tool
        classification = self.factory.classify_tool("search_inventory")
        assert classification == ActionType.REVERSIBLE
        assert self.factory.is_tool_reversible("search_inventory")
    
    def test_tool_requirements(self):
        """Test getting tool requirements"""
        requirements = self.factory.get_tool_requirements("send_email_response")
        assert requirements["requires_approval"] == True
        
        requirements = self.factory.get_tool_requirements("search_inventory")
        assert requirements["requires_approval"] == False
    
    def test_tool_classifications_summary(self):
        """Test getting summary of tool classifications"""
        summary = self.factory.get_tool_classifications_summary()
        
        assert "reversible" in summary
        assert "irreversible" in summary
        assert summary["total_reversible"] > 0
        assert summary["total_irreversible"] > 0
        
        # Check specific tools are in correct categories
        assert "search_inventory" in summary["reversible"]
        assert "send_email_response" in summary["irreversible"]
        assert "process_payment" in summary["irreversible"]
        assert "calculate_price" not in summary["irreversible"]
    
    def test_tool_wrapping(self):
        """Test wrapping tools with classification metadata"""
        # Create a mock tool
        class MockTool:
            def __call__(self):
                pass
        
        tool = MockTool()
        tool_name = "send_email_response"
        
        wrapped = self.factory.wrap_tool_with_classification(tool, tool_name)
        
        assert hasattr(wrapped, "action_type")
        assert wrapped.action_type == ActionType.IRREVERSIBLE
        assert hasattr(wrapped, "requires_approval")
        assert wrapped.requires_approval == True
        assert hasattr(wrapped, "can_auto_execute")
        assert wrapped.can_auto_execute == False


class TestActionCategories:
    """Test action category classifications"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.classifier = ActionClassifier()
    
    def test_email_category_is_irreversible(self):
        """Test that email send category is always irreversible"""
        result = self.classifier.classify_action(
            "any_action", 
            ActionCategory.EMAIL_SEND
        )
        assert result == ActionType.IRREVERSIBLE
    
    def test_inventory_reserve_is_irreversible(self):
        """Test that inventory reservation is irreversible"""
        result = self.classifier.classify_action(
            "any_action",
            ActionCategory.INVENTORY_RESERVE
        )
        assert result == ActionType.IRREVERSIBLE
    
    def test_database_read_is_reversible(self):
        """Test that database reads are reversible"""
        result = self.classifier.classify_action(
            "read_data",
            ActionCategory.DATABASE_READ
        )
        assert result == ActionType.REVERSIBLE
    
    def test_ai_analysis_is_reversible(self):
        """Test that AI analysis is reversible"""
        result = self.classifier.classify_action(
            "analyze_data",
            ActionCategory.AI_ANALYSIS
        )
        assert result == ActionType.REVERSIBLE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])