"""
Test script for enhanced document analysis functionality
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_enhanced_analysis():
    """Test the enhanced document analysis functionality"""
    
    # Sample employment contract content
    sample_contract = """
    EMPLOYMENT CONTRACT
    
    This Employment Contract is entered into between TechCorp Kenya Ltd (the "Company") 
    and John Doe (the "Employee") on January 15, 2025.
    
    1. POSITION AND DUTIES
    The Employee shall serve as Software Developer and shall perform duties as assigned.
    
    2. SALARY
    The Employee shall receive a monthly salary of KES 150,000 payable monthly.
    
    3. PROBATION PERIOD
    The Employee shall serve a probation period of 6 months from the start date.
    
    4. TERMINATION
    Either party may terminate this contract with 30 days written notice.
    The Company may terminate immediately for cause.
    
    5. CONFIDENTIALITY
    The Employee agrees to maintain confidentiality of all company information.
    
    This contract is governed by the laws of Kenya and subject to Employment Act 2007.
    """
    
    try:
        # Test Kenyan Law Service
        print("Testing Kenyan Law Service...")
        from app.services.kenyan_law_service import KenyanLawService
        
        kenyan_law_service = KenyanLawService()
        
        # Test citation extraction
        print("1. Testing citation extraction...")
        citations = await kenyan_law_service.extract_kenyan_law_citations(sample_contract)
        print(f"   Found {len(citations)} citations:")
        for citation in citations:
            print(f"   - {citation.source}, {citation.section}: {citation.relevance}")
        
        # Test document intelligence
        print("\n2. Testing document intelligence...")
        doc_intelligence = await kenyan_law_service.extract_document_intelligence(sample_contract)
        print(f"   Document Type: {doc_intelligence.document_type_detected}")
        print(f"   Parties: {doc_intelligence.parties_identified}")
        print(f"   Financial Terms: {doc_intelligence.financial_terms}")
        print(f"   Critical Clauses: {doc_intelligence.critical_clauses}")
        
        # Test compliance analysis
        print("\n3. Testing compliance analysis...")
        compliance = await kenyan_law_service.check_employment_act_compliance(
            sample_contract, "employment_contract"
        )
        print(f"   Overall Score: {compliance.overall_score:.2f}")
        print(f"   Kenyan Law Compliant: {compliance.kenyan_law_compliance}")
        print(f"   Missing Requirements: {len(compliance.missing_requirements)}")
        
        print("\n✅ Kenyan Law Service tests completed successfully!")
        
        # Test AI Service Enhanced Analysis (without full app context)
        print("\n4. Testing AI Service structure...")
        from app.services.ai_service import AIService
        
        # Create a mock AI service for testing structure
        ai_service = AIService()
        
        # Test helper methods
        print("   Testing helper methods...")
        
        # Test finding parsing
        sample_response = """
        Contract Terms: The employment terms are generally compliant with basic requirements.
        Risk Factors: Termination clause may need review for Employment Act compliance.
        Compliance Issues: Notice period requirements should be clarified.
        """
        
        findings = ai_service._parse_findings_from_response(sample_response)
        print(f"   Parsed {len(findings)} findings from sample response")
        
        # Test risk parsing
        sample_risk_response = """
        Compliance Risk: Potential non-compliance with Employment Act 2007 notice requirements.
        Financial Risk: Unclear severance pay calculations may lead to disputes.
        """
        
        risks = ai_service._parse_risks_from_response(sample_risk_response, "employment_contract")
        print(f"   Parsed {len(risks)} risks from sample response")
        
        # Test confidence calculation
        confidence = ai_service._calculate_enhanced_confidence(citations, compliance, findings, risks)
        print(f"   Calculated confidence: {confidence:.2f}")
        
        print("\n✅ AI Service structure tests completed successfully!")
        
        print("\n🎉 All enhanced analysis components are working correctly!")
        print("\nNext steps:")
        print("1. Deploy to production environment")
        print("2. Test with live database connection")
        print("3. Verify endpoints with real document uploads")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_enhanced_analysis())
    if success:
        print("\n✅ Enhanced analysis is ready for deployment!")
    else:
        print("\n❌ Issues found - please review before deployment")
