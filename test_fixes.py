"""
Test script to verify the fixes for rate limiting and minimum wage compliance
"""

import asyncio
import sys
import os
import aiohttp
import time

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_fixes():
    """Test both fixes: rate limiting and minimum wage compliance"""
    
    print("🔧 TESTING FIXES FOR RATE LIMITING & MINIMUM WAGE COMPLIANCE")
    print("=" * 70)
    
    base_url = "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com"
    
    try:
        async with aiohttp.ClientSession() as session:
            
            # Test 1: Minimum Wage Compliance Detection
            print("\n💰 TEST 1: Minimum Wage Compliance Detection")
            print("   Testing with salary below minimum wage (KES 10,000)...")
            
            low_wage_payload = {
                "template_id": "employment_contract",
                "document_data": {
                    "employer_name": "Test Corp Ltd",
                    "employee_name": "Test Employee",
                    "position": "General Worker",
                    "salary": 10000,  # Below minimum wage of KES 15,000
                    "start_date": "2025-08-01",
                    "probation_period": 6,
                    "notice_period": 30,
                    "working_hours": "8:00 AM to 5:00 PM, Monday to Friday",
                    "annual_leave": 21
                },
                "generation_options": {
                    "output_format": "html",
                    "kenyan_law_focus": True,
                    "include_compliance_notes": True
                }
            }
            
            start_time = time.time()
            async with session.post(
                f"{base_url}/api/v1/generate/generate",
                json=low_wage_payload
            ) as response:
                generation_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Check if minimum wage violation was detected
                    compliance_results = data.get("compliance_results", {})
                    violations = compliance_results.get("violations", [])
                    
                    wage_violation_found = any(
                        "min_wage" in violation.get("rule_id", "") 
                        for violation in violations
                    )
                    
                    if wage_violation_found:
                        print("   ✅ MINIMUM WAGE COMPLIANCE: FIXED!")
                        print("   ✅ System correctly detected salary below minimum wage")
                        
                        # Show violation details
                        for violation in violations:
                            if "min_wage" in violation.get("rule_id", ""):
                                print(f"      - Violation: {violation.get('requirement', 'N/A')}")
                                details = violation.get('violation_details', {})
                                if details:
                                    print(f"      - Current: KES {details.get('current_salary', 0):,}")
                                    print(f"      - Required: KES {details.get('minimum_required', 0):,}")
                                    print(f"      - Shortfall: KES {details.get('shortfall', 0):,}")
                    else:
                        print("   ❌ MINIMUM WAGE COMPLIANCE: STILL NOT WORKING")
                        print("   ❌ System did not detect salary below minimum wage")
                        
                        # Debug info
                        print(f"      Debug - Compliance results: {compliance_results}")
                        
                else:
                    print(f"   ❌ Request failed with status: {response.status}")
                    error_text = await response.text()
                    print(f"      Error: {error_text}")
            
            # Test 2: Rate Limiting
            print(f"\n🚦 TEST 2: Rate Limiting")
            print("   Testing rapid requests to check rate limiting...")
            
            # Make rapid requests to test rate limiting
            rapid_requests = 15  # More than typical rate limit
            successful_requests = 0
            rate_limited_requests = 0
            
            print(f"   Making {rapid_requests} rapid requests...")
            
            for i in range(rapid_requests):
                try:
                    async with session.get(f"{base_url}/health") as response:
                        if response.status == 200:
                            successful_requests += 1
                        elif response.status == 429:  # Too Many Requests
                            rate_limited_requests += 1
                        
                        # Small delay to avoid overwhelming
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    print(f"      Request {i+1} failed: {e}")
            
            print(f"   Results:")
            print(f"      - Successful requests: {successful_requests}")
            print(f"      - Rate limited requests: {rate_limited_requests}")
            
            if rate_limited_requests > 0:
                print("   ✅ RATE LIMITING: WORKING!")
                print(f"   ✅ System rate limited {rate_limited_requests} requests")
            else:
                print("   ⚠️ RATE LIMITING: NOT DETECTED")
                print("   ⚠️ No rate limiting observed (may need higher request volume)")
            
            # Test 3: Working Hours Compliance
            print(f"\n⏰ TEST 3: Working Hours Compliance")
            print("   Testing with excessive working hours...")
            
            excessive_hours_payload = {
                "template_id": "employment_contract",
                "document_data": {
                    "employer_name": "Test Corp Ltd",
                    "employee_name": "Test Employee",
                    "position": "General Worker",
                    "salary": 150000,  # Above minimum wage
                    "start_date": "2025-08-01",
                    "working_hours": "60 hours per week",  # Exceeds 52 hour limit
                    "annual_leave": 15  # Below 21 day minimum
                },
                "generation_options": {
                    "kenyan_law_focus": True,
                    "include_compliance_notes": True
                }
            }
            
            async with session.post(
                f"{base_url}/api/v1/generate/generate",
                json=excessive_hours_payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    compliance_results = data.get("compliance_results", {})
                    violations = compliance_results.get("violations", [])
                    
                    hours_violation = any("working_hours" in v.get("rule_id", "") for v in violations)
                    leave_violation = any("annual_leave" in v.get("rule_id", "") for v in violations)
                    
                    print(f"   Working Hours Violation Detected: {'✅ YES' if hours_violation else '❌ NO'}")
                    print(f"   Annual Leave Violation Detected: {'✅ YES' if leave_violation else '❌ NO'}")
                    
                    if hours_violation or leave_violation:
                        print("   ✅ ENHANCED COMPLIANCE CHECKING: WORKING!")
                    else:
                        print("   ⚠️ ENHANCED COMPLIANCE CHECKING: PARTIAL")
                else:
                    print(f"   ❌ Request failed with status: {response.status}")
            
            # Summary
            print(f"\n" + "=" * 70)
            print("📊 FIXES TEST SUMMARY")
            print("=" * 70)
            
            print(f"✅ Minimum Wage Detection: {'FIXED' if wage_violation_found else 'NEEDS WORK'}")
            print(f"⚠️ Rate Limiting: {'WORKING' if rate_limited_requests > 0 else 'NEEDS VERIFICATION'}")
            print(f"✅ Enhanced Compliance: {'WORKING' if hours_violation or leave_violation else 'PARTIAL'}")
            
            print(f"\n🎯 OVERALL STATUS:")
            if wage_violation_found:
                print("✅ CRITICAL FIXES IMPLEMENTED SUCCESSFULLY!")
                print("🚀 SYSTEM READY FOR DEPLOYMENT WITH ENHANCED COMPLIANCE!")
            else:
                print("⚠️ SOME FIXES NEED ADDITIONAL WORK")
                print("🔧 RECOMMEND DEBUGGING COMPLIANCE CHECKING")
            
            return wage_violation_found
            
    except Exception as e:
        print(f"\n❌ TESTING FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fixes())
    if success:
        print("\n✅ FIXES TESTING COMPLETED - READY FOR DEPLOYMENT!")
    else:
        print("\n❌ FIXES TESTING COMPLETED - NEEDS MORE WORK")
