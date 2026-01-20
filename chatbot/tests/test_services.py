# Services Tests

"""
Tests for service layer components.
"""

import pytest


class TestPromptsImport:
    """Tests for prompts module."""
    
    def test_prompts_import(self):
        """Test prompts can be imported."""
        from prompts import prompts, patient_note_templates
        
        assert isinstance(prompts, dict)
        assert isinstance(patient_note_templates, dict)
    
    def test_prompts_has_indexes(self):
        """Test prompts contains expected indexes."""
        from prompts import prompts
        
        expected_indexes = [
            "tiamd_prod_processed_notes",
            "tiamd_prod_clinical_notes",
            "tiamd_clinical_notes",
        ]
        
        for index in expected_indexes:
            assert index in prompts, f"Missing index: {index}"
    
    def test_templates_has_formats(self):
        """Test templates contains expected formats."""
        from prompts import patient_note_templates
        
        expected_templates = [
            "neurology_consult",
            "neurology_progress",
            "soap_note",
        ]
        
        for template in expected_templates:
            assert template in patient_note_templates, f"Missing template: {template}"
    
    def test_template_has_required_keys(self):
        """Test each template has required keys."""
        from prompts import patient_note_templates
        
        required_keys = ["name", "description", "format_instructions"]
        
        for template_key, template in patient_note_templates.items():
            for key in required_keys:
                assert key in template, f"Template {template_key} missing key: {key}"


class TestHelperFunctions:
    """Tests for prompts helper functions."""
    
    def test_get_template_options_text(self):
        """Test get_template_options_text returns formatted string."""
        from prompts import get_template_options_text
        
        result = get_template_options_text()
        
        assert isinstance(result, str)
        assert "Neurology Consult" in result
        assert "SOAP Note" in result
    
    def test_should_show_note_templates_with_note_keyword(self):
        """Test detection of note-related queries."""
        from prompts import should_show_note_templates
        
        # Should trigger for "notes" keyword
        should_show, options = should_show_note_templates("Show me patient notes")
        assert should_show is True
        assert options is not None
        
    def test_should_show_note_templates_without_keyword(self):
        """Test non-note queries don't trigger template options."""
        from prompts import should_show_note_templates
        
        # Should NOT trigger for generic query
        should_show, options = should_show_note_templates("What is the total count?")
        assert should_show is False
        assert options is None
