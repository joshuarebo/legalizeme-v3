"""
Debug compliance checking locally
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def debug_compliance():
    """Debug compliance checking locally"""
    
    print("🔍 DEBUGGING COMPLIANCE CHECKING")
    print("=" * 50)
    
    try:
        # Test 1: Import and initialize
        print("1. Testing import and initialization...")
        from app.services.kenyan_law_database import kenyan_law_db
        print("   ✅ Successfully imported kenyan_law_db")
        
        # Test 2: Check if compliance rules are loaded
        print("\n2. Checking compliance rules...")
        print(f"   Compliance rules loaded: {len(kenyan_law_db.compliance_rules)}")
        
        if kenyan_law_db.compliance_rules:
            print("   ✅ Compliance rules found:")
            for rule_id, rule in list(kenyan_law_db.compliance_rules.items())[:3]:
                print(f"      - {rule_id}: {rule.requirement[:50]}...")
        else:
            print("   ❌ No compliance rules loaded - this is the problem!")
            print("   🔧 Generating compliance rules...")
            await kenyan_law_db._generate_compliance_rules()
            print(f"   ✅ Generated {len(kenyan_law_db.compliance_rules)} compliance rules")
        
        # Test 3: Test compliance checking with sample data
        print("\n3. Testing compliance checking...")
        
        sample_document_data = {
            "employer_name": "Test Corp Ltd",
            "employee_name": "Test Employee", 
            "position": "General Worker",
            "salary": 10000,  # Below minimum wage
            "start_date": "2025-08-01",
            "working_hours": "60 hours per week",  # Exceeds limit
            "annual_leave": 15  # Below minimum
        }
        
        sample_content = "This is a test employment contract with salary of 10000 KES per month."
        
        compliance_results = await kenyan_law_db.check_document_compliance(
            sample_content, "employment_contract", sample_document_data
        )
        
        print(f"   Compliance results: {compliance_results}")
        
        if compliance_results:
            print("   ✅ Compliance checking working!")
            print(f"      - Overall compliance: {compliance_results.get('overall_compliance')}")
            print(f"      - Compliance score: {compliance_results.get('compliance_score')}")
            print(f"      - Violations found: {len(compliance_results.get('violations', []))}")
            
            violations = compliance_results.get('violations', [])
            for violation in violations:
                print(f"         * {violation.get('rule_id')}: {violation.get('requirement')}")
        else:
            print("   ❌ Compliance checking returned empty results")
        
        # Test 4: Test specific minimum wage checking
        print("\n4. Testing minimum wage checking directly...")
        
        compliance_results_test = {
            'violations': [],
            'warnings': [],
            'auto_fixes_available': []
        }
        
        violation_found = await kenyan_law_db._check_minimum_wage_compliance(
            sample_document_data, compliance_results_test
        )
        
        print(f"   Minimum wage violation found: {violation_found}")
        print(f"   Violations: {compliance_results_test['violations']}")
        
        return len(compliance_results.get('violations', [])) > 0 if compliance_results else False
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_compliance())
    if success:
        print("\n✅ COMPLIANCE CHECKING IS WORKING!")
    else:
        print("\n❌ COMPLIANCE CHECKING NEEDS FIXES")
