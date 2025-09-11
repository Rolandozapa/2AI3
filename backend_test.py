#!/usr/bin/env python3
"""
REFACTORED SYSTEM PHASE 2 - MODULAR ARCHITECTURE TESTING SUITE
Focus: Complete testing of the refactored system with event-driven modular architecture

TESTING REQUIREMENTS FROM REVIEW REQUEST:
1. Architecture Comparison: Test GET /api/system/architecture-comparison endpoint
2. Refactored System Status: Test GET /api/system/refactored/status endpoint
3. Component Initialization: Test POST /api/system/refactored/initialize endpoint
4. Event-Driven System Startup: Test POST /api/system/refactored/start endpoint
5. Phase 1 Optimization Status: Test GET /api/system/optimization-status endpoint
6. Regression Testing: Verify existing endpoints still work (/api/system/timing-info, /api/system/performance/cache-stats)
7. Backwards Compatibility: Ensure complete compatibility with legacy system
8. Performance Validation: Confirm optimized performance is maintained

EXPECTED SYSTEM CAPABILITIES:
- Modular components: Scout, IA1, Events, Orchestrator
- Event-driven pub/sub system
- Legacy/refactored integration
- Intelligent cache from Phase 1
- Current mode: "legacy" (refactored system not yet initialized)
- Refactoring endpoints accessible
- Complete backwards compatibility

TESTING APPROACH:
- Test all new refactored system endpoints
- Validate system starts in legacy mode
- Test component initialization and startup sequence
- Verify backwards compatibility with existing endpoints
- Check performance optimization status from Phase 1
- Validate event-driven architecture functionality
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RefactoredSystemPhase2TestSuite:
    """Comprehensive test suite for Refactored System Phase 2 - Modular Architecture"""
    
    def __init__(self):
        # Get backend URL from environment or use default
        try:
            with open('/app/frontend/src/App.js', 'r') as f:
                content = f.read()
                # Extract backend URL from App.js
                import re
                match = re.search(r"process\.env\.REACT_APP_BACKEND_URL \|\| '([^']+)'", content)
                if match:
                    backend_url = match.group(1)
                else:
                    backend_url = "http://localhost:8001"
        except Exception:
            backend_url = "http://localhost:8001"
        
        self.api_url = f"{backend_url}/api"
        logger.info(f"Testing Refactored System Phase 2 at: {self.api_url}")
        
        # Test results
        self.test_results = []
        
        # Expected refactored system endpoints to test
        self.refactored_endpoints = [
            {'method': 'GET', 'path': '/system/architecture-comparison', 'name': 'Architecture Comparison'},
            {'method': 'GET', 'path': '/system/refactored/status', 'name': 'Refactored System Status'},
            {'method': 'POST', 'path': '/system/refactored/initialize', 'name': 'Component Initialization'},
            {'method': 'POST', 'path': '/system/refactored/start', 'name': 'Event-Driven System Startup'},
            {'method': 'GET', 'path': '/system/optimization-status', 'name': 'Phase 1 Optimization Status'},
        ]
        
        # Regression test endpoints
        self.regression_endpoints = [
            {'method': 'GET', 'path': '/system/timing-info', 'name': 'System Timing Info'},
            {'method': 'GET', 'path': '/system/performance/cache-stats', 'name': 'Cache Performance Stats'},
            {'method': 'GET', 'path': '/system/performance/summary', 'name': 'Performance Summary'},
        ]
        
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
        if details:
            logger.info(f"   Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    async def test_1_architecture_comparison(self):
        """Test 1: Architecture Comparison Endpoint"""
        logger.info("\n🔍 TEST 1: Architecture Comparison Test")
        
        try:
            response = requests.get(f"{self.api_url}/system/architecture-comparison", timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"   📊 Architecture comparison response: {json.dumps(data, indent=2)}")
                
                # Check for expected comparison fields
                expected_fields = ['legacy_architecture', 'refactored_architecture', 'comparison', 'benefits']
                found_fields = [field for field in expected_fields if field in data]
                
                if len(found_fields) >= 3:
                    legacy_info = data.get('legacy_architecture', {})
                    refactored_info = data.get('refactored_architecture', {})
                    
                    self.log_test_result("Architecture Comparison", True, 
                                       f"Comparison data available with {len(found_fields)} sections: {found_fields}")
                else:
                    self.log_test_result("Architecture Comparison", False, 
                                       f"Missing comparison sections: expected {expected_fields}, found {found_fields}")
            else:
                self.log_test_result("Architecture Comparison", False, 
                                   f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test_result("Architecture Comparison", False, f"Exception: {str(e)}")
    
    async def test_2_refactored_system_status(self):
        """Test 2: Refactored System Status - Should show legacy mode initially"""
        logger.info("\n🔍 TEST 2: Refactored System Status Test")
        
        try:
            response = requests.get(f"{self.api_url}/system/refactored/status", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"   📊 Refactored system status: {json.dumps(data, indent=2)}")
                
                # Check for expected status fields
                expected_fields = ['refactored_system', 'orchestrator', 'event_bus']
                found_fields = [field for field in expected_fields if field in data]
                
                if len(found_fields) >= 2:
                    refactored_system = data.get('refactored_system', {})
                    legacy_mode = refactored_system.get('legacy_mode', True)
                    initialized = refactored_system.get('initialized', False)
                    
                    # Expected: system should start in legacy mode, not initialized
                    if legacy_mode and not initialized:
                        self.log_test_result("Refactored System Status", True, 
                                           f"System correctly in legacy mode (not initialized): legacy_mode={legacy_mode}, initialized={initialized}")
                    else:
                        self.log_test_result("Refactored System Status", False, 
                                           f"Unexpected system state: legacy_mode={legacy_mode}, initialized={initialized}")
                else:
                    self.log_test_result("Refactored System Status", False, 
                                       f"Missing status fields: expected {expected_fields}, found {found_fields}")
            else:
                self.log_test_result("Refactored System Status", False, 
                                   f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test_result("Refactored System Status", False, f"Exception: {str(e)}")
    
    async def test_3_component_initialization(self):
        """Test 3: Component Initialization"""
        logger.info("\n🔍 TEST 3: Component Initialization Test")
        
        try:
            # Test component initialization
            init_config = {
                "orchestrator": {
                    "enable_event_system": True,
                    "enable_performance_monitoring": True
                }
            }
            
            response = requests.post(f"{self.api_url}/system/refactored/initialize", 
                                   json=init_config, timeout=60)
            
            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"   📊 Initialization response: {json.dumps(data, indent=2)}")
                
                # Check initialization result
                success = data.get('success', False)
                message = data.get('message', '')
                
                if success:
                    # Verify system status after initialization
                    status_response = requests.get(f"{self.api_url}/system/refactored/status", timeout=30)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        refactored_system = status_data.get('refactored_system', {})
                        initialized = refactored_system.get('initialized', False)
                        
                        if initialized:
                            self.log_test_result("Component Initialization", True, 
                                               f"Components initialized successfully: {message}")
                        else:
                            self.log_test_result("Component Initialization", False, 
                                               f"Initialization reported success but status shows not initialized")
                    else:
                        self.log_test_result("Component Initialization", False, 
                                           f"Cannot verify initialization status: HTTP {status_response.status_code}")
                else:
                    self.log_test_result("Component Initialization", False, 
                                       f"Initialization failed: {message}")
            else:
                self.log_test_result("Component Initialization", False, 
                                   f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test_result("Component Initialization", False, f"Exception: {str(e)}")
    
    async def test_4_event_driven_system_startup(self):
        """Test 4: Event-Driven System Startup"""
        logger.info("\n🔍 TEST 4: Event-Driven System Startup Test")
        
        try:
            # Test system startup
            response = requests.post(f"{self.api_url}/system/refactored/start", 
                                   json={}, timeout=60)
            
            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"   📊 Startup response: {json.dumps(data, indent=2)}")
                
                # Check startup result
                success = data.get('success', False)
                message = data.get('message', '')
                
                if success:
                    # Verify system status after startup
                    status_response = requests.get(f"{self.api_url}/system/refactored/status", timeout=30)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        refactored_system = status_data.get('refactored_system', {})
                        active = refactored_system.get('active', False)
                        legacy_mode = refactored_system.get('legacy_mode', True)
                        
                        if active and not legacy_mode:
                            self.log_test_result("Event-Driven System Startup", True, 
                                               f"System started successfully: active={active}, legacy_mode={legacy_mode}")
                        else:
                            self.log_test_result("Event-Driven System Startup", False, 
                                               f"Startup reported success but system not active: active={active}, legacy_mode={legacy_mode}")
                    else:
                        self.log_test_result("Event-Driven System Startup", False, 
                                           f"Cannot verify startup status: HTTP {status_response.status_code}")
                else:
                    self.log_test_result("Event-Driven System Startup", False, 
                                       f"System startup failed: {message}")
            else:
                self.log_test_result("Event-Driven System Startup", False, 
                                   f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test_result("Event-Driven System Startup", False, f"Exception: {str(e)}")
    
    async def test_5_phase1_optimization_status(self):
        """Test 5: Phase 1 Optimization Status"""
        logger.info("\n🔍 TEST 5: Phase 1 Optimization Status Test")
        
        try:
            response = requests.get(f"{self.api_url}/system/optimization-status", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"   📊 Optimization status: {json.dumps(data, indent=2)}")
                
                # Check for Phase 1 optimization indicators
                expected_fields = ['cache_system', 'performance_monitor', 'api_coordinator']
                optimization_indicators = []
                
                for field in expected_fields:
                    if field in data:
                        optimization_indicators.append(field)
                
                if len(optimization_indicators) >= 2:
                    cache_status = data.get('cache_system', {})
                    performance_status = data.get('performance_monitor', {})
                    
                    self.log_test_result("Phase 1 Optimization Status", True, 
                                       f"Phase 1 optimizations detected: {optimization_indicators}")
                else:
                    self.log_test_result("Phase 1 Optimization Status", False, 
                                       f"Phase 1 optimizations not found: expected {expected_fields}, found {optimization_indicators}")
            else:
                self.log_test_result("Phase 1 Optimization Status", False, 
                                   f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test_result("Phase 1 Optimization Status", False, f"Exception: {str(e)}")
    
    async def test_6_regression_compatibility(self):
        """Test 6: Regression Testing - Backwards Compatibility"""
        logger.info("\n🔍 TEST 6: Regression Testing - Backwards Compatibility")
        
        regression_results = []
        
        for endpoint in self.regression_endpoints:
            try:
                method = endpoint['method']
                path = endpoint['path']
                name = endpoint['name']
                
                logger.info(f"   Testing {method} {path} ({name})")
                
                if method == 'GET':
                    response = requests.get(f"{self.api_url}{path}", timeout=60)
                else:
                    response = requests.post(f"{self.api_url}{path}", json={}, timeout=60)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        regression_results.append({
                            'endpoint': f"{method} {path}",
                            'name': name,
                            'status': 'SUCCESS',
                            'response_size': len(str(data))
                        })
                        logger.info(f"      ✅ {name}: SUCCESS")
                    except:
                        regression_results.append({
                            'endpoint': f"{method} {path}",
                            'name': name,
                            'status': 'SUCCESS_NO_JSON',
                            'response_size': len(response.text)
                        })
                        logger.info(f"      ✅ {name}: SUCCESS (No JSON)")
                else:
                    regression_results.append({
                        'endpoint': f"{method} {path}",
                        'name': name,
                        'status': f'HTTP_{response.status_code}',
                        'response_size': len(response.text)
                    })
                    logger.info(f"      ❌ {name}: HTTP {response.status_code}")
                    
            except Exception as e:
                regression_results.append({
                    'endpoint': f"{method} {path}",
                    'name': name,
                    'status': 'ERROR',
                    'error': str(e)
                })
                logger.info(f"      ❌ {name}: Exception - {str(e)}")
        
        # Evaluate regression testing
        successful_endpoints = len([r for r in regression_results if r['status'] in ['SUCCESS', 'SUCCESS_NO_JSON']])
        total_endpoints = len(regression_results)
        
        success_rate = successful_endpoints / total_endpoints if total_endpoints > 0 else 0
        
        if success_rate >= 0.8:  # 80% success rate
            self.log_test_result("Regression Compatibility", True, 
                               f"Backwards compatibility maintained: {successful_endpoints}/{total_endpoints} ({success_rate:.1%})")
        else:
            self.log_test_result("Regression Compatibility", False, 
                               f"Backwards compatibility issues: {successful_endpoints}/{total_endpoints} ({success_rate:.1%})")
    
    async def test_7_all_refactored_endpoints(self):
        """Test 7: All Refactored System Endpoints"""
        logger.info("\n🔍 TEST 7: All Refactored System Endpoints Test")
        
        endpoint_results = []
        
        for endpoint in self.refactored_endpoints:
            try:
                method = endpoint['method']
                path = endpoint['path']
                name = endpoint['name']
                
                logger.info(f"   Testing {method} {path} ({name})")
                
                if method == 'GET':
                    response = requests.get(f"{self.api_url}{path}", timeout=30)
                elif method == 'POST':
                    # Use appropriate payload for POST endpoints
                    if 'initialize' in path:
                        payload = {"orchestrator": {"enable_event_system": True}}
                    else:
                        payload = {}
                    response = requests.post(f"{self.api_url}{path}", json=payload, timeout=30)
                
                if response.status_code in [200, 201]:
                    try:
                        data = response.json()
                        endpoint_results.append({
                            'endpoint': f"{method} {path}",
                            'name': name,
                            'status': 'SUCCESS',
                            'response_size': len(str(data))
                        })
                        logger.info(f"      ✅ {name}: SUCCESS")
                    except:
                        endpoint_results.append({
                            'endpoint': f"{method} {path}",
                            'name': name,
                            'status': 'SUCCESS_NO_JSON',
                            'response_size': len(response.text)
                        })
                        logger.info(f"      ✅ {name}: SUCCESS (No JSON)")
                else:
                    endpoint_results.append({
                        'endpoint': f"{method} {path}",
                        'name': name,
                        'status': f'HTTP_{response.status_code}',
                        'response_size': len(response.text)
                    })
                    logger.info(f"      ❌ {name}: HTTP {response.status_code}")
                    
            except Exception as e:
                endpoint_results.append({
                    'endpoint': f"{method} {path}",
                    'name': name,
                    'status': 'ERROR',
                    'error': str(e)
                })
                logger.info(f"      ❌ {name}: Exception - {str(e)}")
        
        # Evaluate endpoint testing
        successful_endpoints = len([r for r in endpoint_results if r['status'] in ['SUCCESS', 'SUCCESS_NO_JSON']])
        total_endpoints = len(endpoint_results)
        
        success_rate = successful_endpoints / total_endpoints if total_endpoints > 0 else 0
        
        if success_rate >= 0.8:  # 80% success rate
            self.log_test_result("All Refactored Endpoints", True, 
                               f"Refactored endpoints accessible: {successful_endpoints}/{total_endpoints} ({success_rate:.1%})")
        else:
            self.log_test_result("All Refactored Endpoints", False, 
                               f"Refactored endpoints issues: {successful_endpoints}/{total_endpoints} ({success_rate:.1%})")
    
    async def test_8_performance_validation(self):
        """Test 8: Performance Validation - Ensure optimizations maintained"""
        logger.info("\n🔍 TEST 8: Performance Validation Test")
        
        try:
            # Test performance summary endpoint
            response = requests.get(f"{self.api_url}/system/performance/summary", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"   📊 Performance summary: {json.dumps(data, indent=2)}")
                
                # Check for performance indicators
                performance_indicators = []
                
                if 'cache_hit_rate' in data:
                    cache_hit_rate = data.get('cache_hit_rate', 0)
                    if cache_hit_rate > 0.5:  # 50% cache hit rate
                        performance_indicators.append(f"Cache hit rate: {cache_hit_rate:.1%}")
                
                if 'average_response_time' in data:
                    avg_response_time = data.get('average_response_time', 0)
                    if avg_response_time < 2.0:  # Under 2 seconds
                        performance_indicators.append(f"Response time: {avg_response_time:.2f}s")
                
                if 'optimization_active' in data:
                    optimization_active = data.get('optimization_active', False)
                    if optimization_active:
                        performance_indicators.append("Optimizations active")
                
                if len(performance_indicators) >= 1:
                    self.log_test_result("Performance Validation", True, 
                                       f"Performance optimizations maintained: {performance_indicators}")
                else:
                    self.log_test_result("Performance Validation", False, 
                                       f"Performance optimizations not detected in summary")
            else:
                self.log_test_result("Performance Validation", False, 
                                   f"Performance summary unavailable: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Performance Validation", False, f"Exception: {str(e)}")
    
    async def run_comprehensive_tests(self):
        """Run all refactored system tests"""
        logger.info("🚀 Starting Refactored System Phase 2 Comprehensive Test Suite")
        logger.info("=" * 80)
        logger.info("📋 REFACTORED SYSTEM PHASE 2 - MODULAR ARCHITECTURE TESTING")
        logger.info("🎯 Testing: Architecture comparison, system status, initialization, startup, optimization")
        logger.info("🎯 Expected: Legacy mode initially, refactored endpoints accessible, backwards compatibility")
        logger.info("=" * 80)
        
        # Run all tests in sequence
        await self.test_1_architecture_comparison()
        await self.test_2_refactored_system_status()
        await self.test_3_component_initialization()
        await self.test_4_event_driven_system_startup()
        await self.test_5_phase1_optimization_status()
        await self.test_6_regression_compatibility()
        await self.test_7_all_refactored_endpoints()
        await self.test_8_performance_validation()
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 REFACTORED SYSTEM PHASE 2 COMPREHENSIVE TEST SUMMARY")
        logger.info("=" * 80)
        
        passed_tests = sum(1 for result in self.test_results if result['success'])
        total_tests = len(self.test_results)
        
        for result in self.test_results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            logger.info(f"{status}: {result['test']}")
            if result['details']:
                logger.info(f"   {result['details']}")
                
        logger.info(f"\n🎯 OVERALL RESULT: {passed_tests}/{total_tests} tests passed")
        
        # System analysis
        logger.info("\n" + "=" * 80)
        logger.info("📋 REFACTORED SYSTEM PHASE 2 STATUS")
        logger.info("=" * 80)
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED - Refactored System Phase 2 FULLY FUNCTIONAL!")
            logger.info("✅ Architecture comparison working")
            logger.info("✅ System starts in legacy mode as expected")
            logger.info("✅ Component initialization operational")
            logger.info("✅ Event-driven system startup working")
            logger.info("✅ Phase 1 optimizations maintained")
            logger.info("✅ Backwards compatibility preserved")
            logger.info("✅ All refactored endpoints accessible")
            logger.info("✅ Performance optimizations active")
        elif passed_tests >= total_tests * 0.8:
            logger.info("⚠️ MOSTLY FUNCTIONAL - Refactored system working with minor gaps")
            logger.info("🔍 Some components may need fine-tuning for full optimization")
        elif passed_tests >= total_tests * 0.6:
            logger.info("⚠️ PARTIALLY FUNCTIONAL - Core refactored features working")
            logger.info("🔧 Some advanced features may need implementation or debugging")
        else:
            logger.info("❌ SYSTEM NOT FUNCTIONAL - Critical issues with refactored system")
            logger.info("🚨 Major implementation gaps or system errors preventing functionality")
        
        # Specific requirements check
        logger.info("\n📝 REFACTORED SYSTEM PHASE 2 REQUIREMENTS VERIFICATION:")
        
        requirements_met = []
        requirements_failed = []
        
        # Check each requirement based on test results
        for result in self.test_results:
            if result['success']:
                if "Architecture Comparison" in result['test']:
                    requirements_met.append("✅ Architecture comparison endpoint working")
                elif "Refactored System Status" in result['test']:
                    requirements_met.append("✅ System correctly starts in legacy mode")
                elif "Component Initialization" in result['test']:
                    requirements_met.append("✅ Component initialization working")
                elif "Event-Driven System Startup" in result['test']:
                    requirements_met.append("✅ Event-driven system startup operational")
                elif "Phase 1 Optimization Status" in result['test']:
                    requirements_met.append("✅ Phase 1 optimizations maintained")
                elif "Regression Compatibility" in result['test']:
                    requirements_met.append("✅ Backwards compatibility preserved")
                elif "All Refactored Endpoints" in result['test']:
                    requirements_met.append("✅ All refactored endpoints accessible")
                elif "Performance Validation" in result['test']:
                    requirements_met.append("✅ Performance optimizations active")
            else:
                if "Architecture Comparison" in result['test']:
                    requirements_failed.append("❌ Architecture comparison endpoint failed")
                elif "Refactored System Status" in result['test']:
                    requirements_failed.append("❌ System status issues")
                elif "Component Initialization" in result['test']:
                    requirements_failed.append("❌ Component initialization failed")
                elif "Event-Driven System Startup" in result['test']:
                    requirements_failed.append("❌ Event-driven system startup failed")
                elif "Phase 1 Optimization Status" in result['test']:
                    requirements_failed.append("❌ Phase 1 optimizations not maintained")
                elif "Regression Compatibility" in result['test']:
                    requirements_failed.append("❌ Backwards compatibility issues")
                elif "All Refactored Endpoints" in result['test']:
                    requirements_failed.append("❌ Refactored endpoints not accessible")
                elif "Performance Validation" in result['test']:
                    requirements_failed.append("❌ Performance optimizations not active")
        
        for req in requirements_met:
            logger.info(f"   {req}")
        
        for req in requirements_failed:
            logger.info(f"   {req}")
        
        logger.info(f"\n🏆 FINAL RESULT: {len(requirements_met)}/{len(requirements_met) + len(requirements_failed)} requirements satisfied")
        
        # Final verdict
        if len(requirements_failed) == 0:
            logger.info("\n🎉 VERDICT: Refactored System Phase 2 is FULLY FUNCTIONAL!")
            logger.info("✅ All modular architecture features implemented and working correctly")
            logger.info("✅ Event-driven system, component initialization, and backwards compatibility operational")
            logger.info("✅ System ready for production with complete legacy integration")
        elif len(requirements_failed) <= 1:
            logger.info("\n⚠️ VERDICT: Refactored System Phase 2 is MOSTLY FUNCTIONAL")
            logger.info("🔍 Minor issues may need attention for complete functionality")
        elif len(requirements_failed) <= 3:
            logger.info("\n⚠️ VERDICT: Refactored System Phase 2 is PARTIALLY FUNCTIONAL")
            logger.info("🔧 Several components need implementation or debugging")
        else:
            logger.info("\n❌ VERDICT: Refactored System Phase 2 is NOT FUNCTIONAL")
            logger.info("🚨 Major implementation gaps preventing refactored system operation")
        
        return passed_tests, total_tests

async def main():
    """Main test execution"""
    test_suite = RefactoredSystemPhase2TestSuite()
    passed, total = await test_suite.run_comprehensive_tests()
    
    # Exit with appropriate code
    if passed == total:
        sys.exit(0)  # All tests passed
    else:
        sys.exit(1)  # Some tests failed

if __name__ == "__main__":
    asyncio.run(main())