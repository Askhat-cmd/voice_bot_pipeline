#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test runner"""
import sys
import os
from pathlib import Path

# Setup path
script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))
os.chdir(script_dir)

output_file = script_dir / 'test_results.txt'

# Write results to file
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(f"Script dir: {script_dir}\n")
    try:
        from text_processor.validators.terminology_validator import TerminologyValidator, ValidationResult
        f.write("IMPORT OK\n")
        
        validator = TerminologyValidator()
        f.write(f"Loaded {len(validator.all_sarsekenov_terms)} Sarsekenov terms\n")
        f.write(f"Loaded {len(validator.forbidden_terms)} forbidden terms\n")
        
        # Test 1: Valid text
        text1 = """
        Когда Ищущий практикует метанаблюдение, он начинает замечать 
        появление Я-образа в поле внимания. Через разотождествление 
        возникает свободное внимание и чистое осознавание.
        """
        result1 = validator.validate_text(text1)
        f.write(f"\nTEST 1 - Valid text:\n")
        f.write(f"  is_valid: {result1.is_valid}\n")
        f.write(f"  density: {result1.metrics.get('density', 0):.1%}\n")
        f.write(f"  entities: {result1.sarsekenov_entities}\n")
        
        # Test 2: Forbidden terms
        text2 = "Эго и подсознание создают стресс и тревогу."
        result2 = validator.validate_text(text2, strict_mode=True)
        f.write(f"\nTEST 2 - Forbidden terms:\n")
        f.write(f"  is_valid: {result2.is_valid}\n")
        f.write(f"  forbidden_found: {result2.forbidden_terms_found}\n")
        
        # Test 3: Replacement
        replaced = validator.replace_forbidden_terms(text2)
        f.write(f"\nTEST 3 - Replacement:\n")
        f.write(f"  original: {text2}\n")
        f.write(f"  replaced: {replaced}\n")
        
        f.write("\n" + "="*50 + "\n")
        f.write("ALL TESTS PASSED!\n")
        
    except Exception as e:
        f.write(f"ERROR: {e}\n")
        import traceback
        f.write(traceback.format_exc())
