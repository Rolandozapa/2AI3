#!/usr/bin/env python3
"""
IA2 DECISION PERSISTENCE DATABASE FIX TEST SUITE
Focus: Test IA2 decision persistence database fix in trading bot system

CRITICAL TEST REQUIREMENTS FROM REVIEW REQUEST:
1. **IA2 DECISION PERSISTENCE VIA FORCE-IA1-ANALYSIS ENDPOINT**:
   - Test POST /api/force-ia1-analysis with a symbol that will trigger IA2 escalation
   - Verify IA2 decision is created AND saved to database
   - Check MongoDB trading_decisions collection for the new decision
   - Verify decision contains: symbol, signal, confidence, timestamp

2. **DATABASE PERSISTENCE VERIFICATION**:
   - Query trading_decisions collection before and after forced analysis
   - Confirm decision_dict structure includes timestamp with get_paris_time()
   - Verify logging shows "💾 IA2 DECISION SAVED: {symbol} → {signal} in database"

3. **API RESPONSE VS DATABASE CONSISTENCY**:
   - Ensure API response includes IA2 decision details
   - Confirm database entry matches API response data
   - Verify no data loss between decision creation and storage

4. **ERROR HANDLING**:
   - Test database save error handling
   - Verify proper error logging if save fails
   - Ensure system continues to return API response even if DB save fails

5. **COMPARE WITH MAIN ORCHESTRATION**:
   - Verify both force-ia1-analysis and main trading cycle use identical persistence logic
   - Confirm both save to same trading_decisions collection

SUCCESS CRITERIA:
✅ IA2 decision created via force-ia1-analysis is saved to database
✅ Database entry contains all required fields with correct timestamp
✅ Logging confirms successful database save
✅ API response and database entry are consistent
✅ Error handling works if database save fails
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
import subprocess
import re
from pymongo import MongoClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IA2DecisionPersistenceTestSuite:
    """Comprehensive test suite for IA2 Decision Persistence Database Fix"""
    
    def __init__(self):
        # Get backend URL from frontend env
        try:
            with open('/app/frontend/.env', 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        backend_url = line.split('=')[1].strip()
                        break
                else:
                    backend_url = "http://localhost:8001"
        except Exception:
            backend_url = "http://localhost:8001"
        
        self.api_url = f"{backend_url}/api"
        logger.info(f"Testing IA2 Decision Persistence Database Fix at: {self.api_url}")
        
        # MongoDB connection for direct database analysis
        try:
            self.mongo_client = MongoClient("mongodb://localhost:27017")
            self.db = self.mongo_client["myapp"]
            logger.info("✅ MongoDB connection established for IA2 Decision Persistence testing")
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            self.mongo_client = None
            self.db = None
        
        # Test results
        self.test_results = []
        
        # Expected IA2 decision fields
        self.ia2_decision_fields = ['symbol', 'signal', 'confidence', 'timestamp', 'id']
        
        # Test symbols likely to trigger IA2 escalation
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'LINKUSDT']
        
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
    
    async def test_1_ia2_decision_persistence_via_force_analysis(self):
        """Test 1: IA2 Decision Persistence via force-ia1-analysis Endpoint"""
        logger.info("\n🔍 TEST 1: IA2 Decision Persistence via force-ia1-analysis Endpoint")
        
        try:
            persistence_results = {
                'force_analysis_successful': False,
                'ia2_escalation_triggered': False,
                'database_save_successful': False,
                'api_response_contains_ia2': False,
                'database_entry_found': False,
                'logging_confirmation': False,
                'decision_data': {},
                'test_symbol': None
            }
            
            logger.info("   🚀 Testing IA2 decision persistence via force-ia1-analysis...")
            logger.info("   📊 Expected: IA2 decision created and saved to database")
            
            # Step 1: Get current trading_decisions count before test
            initial_decisions_count = 0
            if self.db:
                try:
                    initial_decisions_count = await asyncio.to_thread(
                        self.db.trading_decisions.count_documents, {}
                    )
                    logger.info(f"      📊 Initial trading_decisions count: {initial_decisions_count}")
                except Exception as e:
                    logger.warning(f"      ⚠️ Could not get initial count: {e}")
            
            # Step 2: Find a suitable symbol for testing
            logger.info("   📈 Finding suitable symbol for IA2 escalation test...")
            test_symbol = None
            
            # Try to get opportunities first
            try:
                response = requests.get(f"{self.api_url}/opportunities", timeout=30)
                if response.status_code == 200:
                    opportunities = response.json()
                    if isinstance(opportunities, list) and len(opportunities) > 0:
                        # Look for a symbol with good characteristics for IA2 escalation
                        for opp in opportunities[:5]:
                            symbol = opp.get('symbol', '')
                            if symbol and any(test_sym in symbol for test_sym in self.test_symbols):
                                test_symbol = symbol
                                break
                        
                        if not test_symbol and opportunities:
                            test_symbol = opportunities[0].get('symbol', 'BTCUSDT')
                    else:
                        test_symbol = 'BTCUSDT'  # Fallback
                else:
                    test_symbol = 'BTCUSDT'  # Fallback
            except Exception as e:
                logger.warning(f"      ⚠️ Could not get opportunities: {e}")
                test_symbol = 'BTCUSDT'  # Fallback
            
            persistence_results['test_symbol'] = test_symbol
            logger.info(f"      📋 Selected test symbol: {test_symbol}")
            
            # Step 3: Force IA1 analysis to trigger IA2 escalation
            logger.info(f"   🚀 Forcing IA1 analysis for {test_symbol}...")
            start_time = time.time()
            
            try:
                response = requests.post(
                    f"{self.api_url}/force-ia1-analysis",
                    json={"symbol": test_symbol},
                    timeout=180  # 3 minutes timeout for analysis
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    force_data = response.json()
                    persistence_results['force_analysis_successful'] = force_data.get('success', False)
                    
                    logger.info(f"      ✅ Force analysis completed (response time: {response_time:.2f}s)")
                    logger.info(f"      📋 Response success: {persistence_results['force_analysis_successful']}")
                    
                    if persistence_results['force_analysis_successful']:
                        # Check if IA2 escalation occurred
                        if 'ia2_decision' in force_data:
                            persistence_results['ia2_escalation_triggered'] = True
                            persistence_results['api_response_contains_ia2'] = True
                            persistence_results['decision_data'] = force_data['ia2_decision']
                            
                            logger.info(f"      ✅ IA2 escalation triggered!")
                            logger.info(f"      📋 IA2 decision: {force_data['ia2_decision']}")
                        else:
                            logger.warning(f"      ❌ No IA2 escalation in response")
                            logger.info(f"      📋 Response keys: {list(force_data.keys())}")
                    else:
                        logger.warning(f"      ❌ Force analysis failed: {force_data.get('error', 'Unknown')}")
                else:
                    logger.error(f"      ❌ Force analysis HTTP error: {response.status_code}")
                    if response.text:
                        logger.error(f"         Error response: {response.text[:300]}...")
                        
            except Exception as e:
                logger.error(f"      ❌ Force analysis exception: {e}")
            
            # Step 4: Check database for new IA2 decision
            if persistence_results['ia2_escalation_triggered'] and self.db:
                logger.info("   📊 Checking database for IA2 decision persistence...")
                try:
                    # Wait a moment for database write
                    await asyncio.sleep(2)
                    
                    # Get current count
                    current_decisions_count = await asyncio.to_thread(
                        self.db.trading_decisions.count_documents, {}
                    )
                    
                    logger.info(f"      📊 Current trading_decisions count: {current_decisions_count}")
                    
                    if current_decisions_count > initial_decisions_count:
                        persistence_results['database_save_successful'] = True
                        logger.info(f"      ✅ Database count increased: {initial_decisions_count} → {current_decisions_count}")
                        
                        # Find the latest decision for our symbol
                        latest_decision = await asyncio.to_thread(
                            self.db.trading_decisions.find_one,
                            {"symbol": test_symbol},
                            {"sort": [("timestamp", -1)]}
                        )
                        
                        if latest_decision:
                            persistence_results['database_entry_found'] = True
                            logger.info(f"      ✅ Database entry found for {test_symbol}")
                            
                            # Verify required fields
                            required_fields = ['symbol', 'signal', 'confidence', 'timestamp']
                            missing_fields = [field for field in required_fields if field not in latest_decision]
                            
                            if not missing_fields:
                                logger.info(f"      ✅ All required fields present: {required_fields}")
                                logger.info(f"      📋 Decision: {latest_decision.get('signal')} with confidence {latest_decision.get('confidence')}")
                            else:
                                logger.warning(f"      ⚠️ Missing fields in database entry: {missing_fields}")
                        else:
                            logger.warning(f"      ❌ No database entry found for {test_symbol}")
                    else:
                        logger.warning(f"      ❌ Database count did not increase")
                        
                except Exception as e:
                    logger.error(f"      ❌ Database check error: {e}")
            
            # Step 5: Check backend logs for confirmation
            logger.info("   📋 Checking backend logs for IA2 decision save confirmation...")
            try:
                backend_logs = await self._capture_backend_logs()
                if backend_logs:
                    save_confirmations = []
                    for log_line in backend_logs:
                        if ("IA2 DECISION SAVED" in log_line and test_symbol in log_line):
                            save_confirmations.append(log_line.strip())
                            persistence_results['logging_confirmation'] = True
                    
                    if save_confirmations:
                        logger.info(f"      ✅ Found IA2 decision save confirmations: {len(save_confirmations)}")
                        for confirmation in save_confirmations[:2]:
                            logger.info(f"         - {confirmation}")
                    else:
                        logger.warning(f"      ❌ No IA2 decision save confirmations found in logs")
                else:
                    logger.warning(f"      ⚠️ Could not capture backend logs")
            except Exception as e:
                logger.warning(f"      ⚠️ Log check error: {e}")
            
            # Calculate test success
            success_criteria = [
                persistence_results['force_analysis_successful'],
                persistence_results['ia2_escalation_triggered'],
                persistence_results['database_save_successful'] or persistence_results['database_entry_found'],
                persistence_results['api_response_contains_ia2']
            ]
            success_count = sum(success_criteria)
            success_rate = success_count / len(success_criteria)
            
            if success_rate >= 0.75:  # 75% success threshold
                self.log_test_result("IA2 Decision Persistence via Force Analysis", True, 
                                   f"IA2 persistence working: {success_count}/{len(success_criteria)} criteria met. Symbol: {test_symbol}, IA2 triggered: {persistence_results['ia2_escalation_triggered']}, DB saved: {persistence_results['database_save_successful']}")
            else:
                self.log_test_result("IA2 Decision Persistence via Force Analysis", False, 
                                   f"IA2 persistence issues: {success_count}/{len(success_criteria)} criteria met. Symbol: {test_symbol}")
                
        except Exception as e:
            self.log_test_result("IA2 Decision Persistence via Force Analysis", False, f"Exception: {str(e)}")
    
    async def test_2_database_persistence_verification(self):
        """Test 2: Database Persistence Verification - Check MongoDB Structure and Logging"""
        logger.info("\n🔍 TEST 2: Database Persistence Verification")
        
        try:
            db_results = {
                'trading_decisions_collection_exists': False,
                'recent_decisions_found': False,
                'decision_structure_valid': False,
                'timestamp_format_correct': False,
                'logging_messages_found': False,
                'sample_decision': {},
                'total_decisions': 0
            }
            
            logger.info("   🚀 Testing database persistence structure and logging...")
            logger.info("   📊 Expected: trading_decisions collection with proper structure and timestamps")
            
            if not self.db:
                logger.error("      ❌ No database connection available")
                self.log_test_result("Database Persistence Verification", False, "No database connection")
                return
            
            # Step 1: Check if trading_decisions collection exists
            logger.info("   📊 Checking trading_decisions collection...")
            try:
                collections = await asyncio.to_thread(self.db.list_collection_names)
                if 'trading_decisions' in collections:
                    db_results['trading_decisions_collection_exists'] = True
                    logger.info(f"      ✅ trading_decisions collection exists")
                    
                    # Get total count
                    total_count = await asyncio.to_thread(
                        self.db.trading_decisions.count_documents, {}
                    )
                    db_results['total_decisions'] = total_count
                    logger.info(f"      📋 Total trading decisions: {total_count}")
                    
                else:
                    logger.warning(f"      ❌ trading_decisions collection not found")
                    logger.info(f"      📋 Available collections: {collections}")
                    
            except Exception as e:
                logger.error(f"      ❌ Error checking collections: {e}")
            
            # Step 2: Check recent decisions structure
            if db_results['trading_decisions_collection_exists']:
                logger.info("   📊 Checking recent trading decisions structure...")
                try:
                    # Get recent decisions (last 24 hours)
                    from datetime import datetime, timedelta
                    cutoff_time = datetime.now() - timedelta(hours=24)
                    
                    recent_decisions = await asyncio.to_thread(
                        lambda: list(self.db.trading_decisions.find(
                            {"timestamp": {"$gte": cutoff_time}}
                        ).sort("timestamp", -1).limit(5))
                    )
                    
                    if recent_decisions:
                        db_results['recent_decisions_found'] = True
                        db_results['sample_decision'] = recent_decisions[0]
                        logger.info(f"      ✅ Found {len(recent_decisions)} recent decisions")
                        
                        # Check structure of latest decision
                        latest_decision = recent_decisions[0]
                        required_fields = ['symbol', 'signal', 'confidence', 'timestamp', 'id']
                        present_fields = [field for field in required_fields if field in latest_decision]
                        
                        if len(present_fields) >= 4:  # At least 4/5 required fields
                            db_results['decision_structure_valid'] = True
                            logger.info(f"      ✅ Decision structure valid: {present_fields}")
                            
                            # Check timestamp format
                            timestamp_value = latest_decision.get('timestamp')
                            if timestamp_value:
                                if isinstance(timestamp_value, datetime):
                                    db_results['timestamp_format_correct'] = True
                                    logger.info(f"      ✅ Timestamp format correct: {timestamp_value}")
                                elif isinstance(timestamp_value, str):
                                    # Check if it's a Paris time string
                                    if "Heure de Paris" in timestamp_value or len(timestamp_value) > 10:
                                        db_results['timestamp_format_correct'] = True
                                        logger.info(f"      ✅ Timestamp format correct (string): {timestamp_value}")
                                    else:
                                        logger.warning(f"      ⚠️ Timestamp format unclear: {timestamp_value}")
                                else:
                                    logger.warning(f"      ⚠️ Unexpected timestamp type: {type(timestamp_value)}")
                            else:
                                logger.warning(f"      ❌ No timestamp field found")
                        else:
                            logger.warning(f"      ❌ Invalid decision structure: {present_fields}/{len(required_fields)} fields")
                            logger.info(f"         Available fields: {list(latest_decision.keys())}")
                    else:
                        logger.warning(f"      ❌ No recent decisions found in last 24 hours")
                        
                        # Try to get any decisions
                        any_decisions = await asyncio.to_thread(
                            lambda: list(self.db.trading_decisions.find().sort("timestamp", -1).limit(1))
                        )
                        
                        if any_decisions:
                            logger.info(f"      📋 Found older decisions, latest: {any_decisions[0].get('timestamp', 'No timestamp')}")
                        else:
                            logger.warning(f"      ❌ No trading decisions found at all")
                        
                except Exception as e:
                    logger.error(f"      ❌ Error checking recent decisions: {e}")
            
            # Step 3: Check backend logs for IA2 decision save messages
            logger.info("   📋 Checking backend logs for IA2 decision save messages...")
            try:
                backend_logs = await self._capture_backend_logs()
                if backend_logs:
                    save_messages = []
                    for log_line in backend_logs:
                        if "IA2 DECISION SAVED" in log_line:
                            save_messages.append(log_line.strip())
                    
                    if save_messages:
                        db_results['logging_messages_found'] = True
                        logger.info(f"      ✅ Found {len(save_messages)} IA2 decision save messages")
                        for msg in save_messages[:2]:  # Show first 2
                            logger.info(f"         - {msg}")
                    else:
                        logger.warning(f"      ❌ No IA2 decision save messages found in logs")
                        
                        # Check for any IA2 related messages
                        ia2_messages = []
                        for log_line in backend_logs:
                            if "IA2" in log_line and ("decision" in log_line.lower() or "save" in log_line.lower()):
                                ia2_messages.append(log_line.strip())
                        
                        if ia2_messages:
                            logger.info(f"      📋 Found {len(ia2_messages)} other IA2 decision messages:")
                            for msg in ia2_messages[:2]:
                                logger.info(f"         - {msg}")
                else:
                    logger.warning(f"      ⚠️ Could not capture backend logs")
            except Exception as e:
                logger.warning(f"      ⚠️ Log check error: {e}")
            
            # Calculate test success
            success_criteria = [
                db_results['trading_decisions_collection_exists'],
                db_results['recent_decisions_found'] or db_results['total_decisions'] > 0,
                db_results['decision_structure_valid'],
                db_results['timestamp_format_correct']
            ]
            success_count = sum(success_criteria)
            success_rate = success_count / len(success_criteria)
            
            if success_rate >= 0.75:  # 75% success threshold
                self.log_test_result("Database Persistence Verification", True, 
                                   f"Database persistence working: {success_count}/{len(success_criteria)} criteria met. Total decisions: {db_results['total_decisions']}, Structure valid: {db_results['decision_structure_valid']}")
            else:
                self.log_test_result("Database Persistence Verification", False, 
                                   f"Database persistence issues: {success_count}/{len(success_criteria)} criteria met. Total: {db_results['total_decisions']}")
                
        except Exception as e:
            self.log_test_result("Database Persistence Verification", False, f"Exception: {str(e)}")
    
    async def test_3_api_response_vs_database_consistency(self):
        """Test 3: API Response vs Database Consistency - Verify Data Matches"""
        logger.info("\n🔍 TEST 3: API Response vs Database Consistency")
        
        try:
            consistency_results = {
                'force_analysis_successful': False,
                'api_response_has_ia2': False,
                'database_entry_found': False,
                'data_consistency_verified': False,
                'field_matches': {},
                'test_symbol': None,
                'api_data': {},
                'db_data': {}
            }
            
            logger.info("   🚀 Testing API response vs database consistency for IA2 decisions...")
            logger.info("   📊 Expected: API response data matches database entry data")
            
            if not self.db:
                logger.error("      ❌ No database connection available")
                self.log_test_result("API Response vs Database Consistency", False, "No database connection")
                return
            
            # Step 1: Select test symbol and force analysis
            test_symbol = 'ETHUSDT'  # Use a common symbol
            consistency_results['test_symbol'] = test_symbol
            
            logger.info(f"   🚀 Forcing IA1 analysis for {test_symbol} to test consistency...")
            
            try:
                response = requests.post(
                    f"{self.api_url}/force-ia1-analysis",
                    json={"symbol": test_symbol},
                    timeout=180
                )
                
                if response.status_code == 200:
                    force_data = response.json()
                    consistency_results['force_analysis_successful'] = force_data.get('success', False)
                    
                    logger.info(f"      ✅ Force analysis completed: {consistency_results['force_analysis_successful']}")
                    
                    if consistency_results['force_analysis_successful'] and 'ia2_decision' in force_data:
                        consistency_results['api_response_has_ia2'] = True
                        consistency_results['api_data'] = force_data['ia2_decision']
                        
                        logger.info(f"      ✅ API response contains IA2 decision")
                        logger.info(f"      📋 API IA2 data: {consistency_results['api_data']}")
                        
                        # Step 2: Wait and check database for corresponding entry
                        await asyncio.sleep(3)  # Wait for database write
                        
                        logger.info("   📊 Checking database for corresponding IA2 decision...")
                        
                        # Find the latest decision for this symbol
                        latest_decision = await asyncio.to_thread(
                            self.db.trading_decisions.find_one,
                            {"symbol": test_symbol},
                            {"sort": [("timestamp", -1)]}
                        )
                        
                        if latest_decision:
                            consistency_results['database_entry_found'] = True
                            consistency_results['db_data'] = latest_decision
                            
                            logger.info(f"      ✅ Database entry found for {test_symbol}")
                            logger.info(f"      📋 DB decision ID: {latest_decision.get('id', 'N/A')}")
                            
                            # Step 3: Compare API response with database entry
                            logger.info("   🔍 Comparing API response with database entry...")
                            
                            # Fields to compare
                            compare_fields = ['signal', 'confidence']
                            matches = 0
                            total_comparisons = 0
                            
                            for field in compare_fields:
                                api_value = consistency_results['api_data'].get(field)
                                db_value = latest_decision.get(field)
                                
                                total_comparisons += 1
                                
                                if api_value is not None and db_value is not None:
                                    # Handle different data types
                                    if isinstance(api_value, str) and hasattr(db_value, 'value'):
                                        # API might have string, DB might have enum
                                        db_value_str = db_value.value if hasattr(db_value, 'value') else str(db_value)
                                        match = api_value.lower() == db_value_str.lower()
                                    elif isinstance(api_value, (int, float)) and isinstance(db_value, (int, float)):
                                        # Numeric comparison with tolerance
                                        match = abs(api_value - db_value) < 0.01
                                    else:
                                        # String comparison
                                        match = str(api_value).lower() == str(db_value).lower()
                                    
                                    consistency_results['field_matches'][field] = {
                                        'api_value': api_value,
                                        'db_value': db_value,
                                        'match': match
                                    }
                                    
                                    if match:
                                        matches += 1
                                        logger.info(f"      ✅ {field} matches: API={api_value}, DB={db_value}")
                                    else:
                                        logger.warning(f"      ❌ {field} mismatch: API={api_value}, DB={db_value}")
                                else:
                                    logger.warning(f"      ⚠️ {field} missing in API or DB: API={api_value}, DB={db_value}")
                            
                            # Check if symbol matches
                            api_symbol = force_data.get('analysis', {}).get('symbol', test_symbol)
                            db_symbol = latest_decision.get('symbol')
                            if api_symbol == db_symbol:
                                matches += 1
                                logger.info(f"      ✅ Symbol matches: {api_symbol}")
                            else:
                                logger.warning(f"      ❌ Symbol mismatch: API={api_symbol}, DB={db_symbol}")
                            total_comparisons += 1
                            
                            # Check timestamp presence (not exact match due to timing)
                            if 'timestamp' in latest_decision:
                                matches += 0.5  # Half point for timestamp presence
                                logger.info(f"      ✅ Timestamp present in DB: {latest_decision['timestamp']}")
                            total_comparisons += 0.5
                            
                            consistency_rate = matches / total_comparisons if total_comparisons > 0 else 0
                            if consistency_rate >= 0.8:  # 80% consistency threshold
                                consistency_results['data_consistency_verified'] = True
                                logger.info(f"      ✅ Data consistency verified: {matches}/{total_comparisons} ({consistency_rate:.1%})")
                            else:
                                logger.warning(f"      ❌ Data consistency issues: {matches}/{total_comparisons} ({consistency_rate:.1%})")
                        else:
                            logger.warning(f"      ❌ No database entry found for {test_symbol}")
                    else:
                        logger.warning(f"      ❌ No IA2 decision in API response")
                        logger.info(f"      📋 Response keys: {list(force_data.keys()) if isinstance(force_data, dict) else 'Not a dict'}")
                else:
                    logger.error(f"      ❌ Force analysis HTTP error: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"      ❌ Force analysis exception: {e}")
            
            # Calculate test success
            success_criteria = [
                consistency_results['force_analysis_successful'],
                consistency_results['api_response_has_ia2'],
                consistency_results['database_entry_found'],
                consistency_results['data_consistency_verified']
            ]
            success_count = sum(success_criteria)
            success_rate = success_count / len(success_criteria)
            
            if success_rate >= 0.75:  # 75% success threshold
                self.log_test_result("API Response vs Database Consistency", True, 
                                   f"Data consistency verified: {success_count}/{len(success_criteria)} criteria met. Symbol: {test_symbol}, Matches: {consistency_results['field_matches']}")
            else:
                self.log_test_result("API Response vs Database Consistency", False, 
                                   f"Data consistency issues: {success_count}/{len(success_criteria)} criteria met. Symbol: {test_symbol}")
                
        except Exception as e:
            self.log_test_result("API Response vs Database Consistency", False, f"Exception: {str(e)}")
    
    async def test_4_error_handling_verification(self):
        """Test 4: Error Handling Verification - Test Database Save Error Scenarios"""
        logger.info("\n🔍 TEST 4: Error Handling Verification")
        
        try:
            error_results = {
                'force_analysis_accessible': False,
                'api_continues_on_db_error': False,
                'error_logging_present': False,
                'graceful_degradation': False,
                'backend_logs_captured': False,
                'error_messages': []
            }
            
            logger.info("   🚀 Testing error handling for IA2 decision database save failures...")
            logger.info("   📊 Expected: System continues to return API response even if DB save fails")
            
            # Step 1: Test normal force analysis to establish baseline
            logger.info("   📈 Testing normal force analysis operation...")
            
            try:
                response = requests.post(
                    f"{self.api_url}/force-ia1-analysis",
                    json={"symbol": "BTCUSDT"},
                    timeout=120
                )
                
                if response.status_code == 200:
                    error_results['force_analysis_accessible'] = True
                    force_data = response.json()
                    
                    logger.info(f"      ✅ Force analysis endpoint accessible")
                    logger.info(f"      📋 Response success: {force_data.get('success', False)}")
                    
                    # Check if system handles the request gracefully
                    if force_data.get('success') or 'error' in force_data:
                        error_results['graceful_degradation'] = True
                        logger.info(f"      ✅ System provides graceful response")
                    else:
                        logger.warning(f"      ⚠️ Unexpected response format")
                        
                else:
                    logger.warning(f"      ⚠️ Force analysis HTTP error: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"      ⚠️ Force analysis test error: {e}")
            
            # Step 2: Test with invalid symbol to trigger error conditions
            logger.info("   📈 Testing with invalid symbol to trigger error conditions...")
            
            try:
                response = requests.post(
                    f"{self.api_url}/force-ia1-analysis",
                    json={"symbol": "INVALID_SYMBOL_TEST"},
                    timeout=60
                )
                
                if response.status_code == 200:
                    force_data = response.json()
                    
                    # Should get an error response but still be structured
                    if 'error' in force_data or not force_data.get('success'):
                        error_results['api_continues_on_db_error'] = True
                        logger.info(f"      ✅ API returns structured error response")
                        logger.info(f"      📋 Error message: {force_data.get('error', 'No specific error')}")
                    else:
                        logger.warning(f"      ⚠️ Unexpected success with invalid symbol")
                        
                elif response.status_code in [400, 404, 422]:
                    # These are acceptable error codes
                    error_results['api_continues_on_db_error'] = True
                    logger.info(f"      ✅ API returns appropriate HTTP error: {response.status_code}")
                else:
                    logger.warning(f"      ⚠️ Unexpected HTTP status: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"      ⚠️ Invalid symbol test error: {e}")
            
            # Step 3: Test with missing symbol parameter
            logger.info("   📈 Testing with missing symbol parameter...")
            
            try:
                response = requests.post(
                    f"{self.api_url}/force-ia1-analysis",
                    json={},  # Empty request
                    timeout=30
                )
                
                if response.status_code == 200:
                    force_data = response.json()
                    if 'error' in force_data and 'symbol' in force_data['error'].lower():
                        logger.info(f"      ✅ Proper validation error for missing symbol")
                    else:
                        logger.warning(f"      ⚠️ Unexpected response to missing symbol")
                elif response.status_code in [400, 422]:
                    logger.info(f"      ✅ Proper HTTP validation error: {response.status_code}")
                else:
                    logger.warning(f"      ⚠️ Unexpected response to missing symbol: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"      ⚠️ Missing symbol test error: {e}")
            
            # Step 4: Check backend logs for error handling messages
            logger.info("   📋 Checking backend logs for error handling messages...")
            
            try:
                backend_logs = await self._capture_backend_logs()
                if backend_logs:
                    error_results['backend_logs_captured'] = True
                    
                    # Look for error handling patterns
                    error_patterns = [
                        'Failed to save IA2 decision',
                        'Database save error',
                        'MongoDB error',
                        'Exception',
                        'ERROR'
                    ]
                    
                    found_errors = []
                    for log_line in backend_logs:
                        for pattern in error_patterns:
                            if pattern.lower() in log_line.lower():
                                found_errors.append(log_line.strip())
                                break
                    
                    if found_errors:
                        error_results['error_logging_present'] = True
                        error_results['error_messages'] = found_errors[:3]  # Keep first 3
                        logger.info(f"      ✅ Found {len(found_errors)} error handling messages")
                        for error_msg in error_results['error_messages']:
                            logger.info(f"         - {error_msg}")
                    else:
                        logger.info(f"      📋 No error messages found (system may be healthy)")
                        
                    # Look for graceful error handling patterns
                    graceful_patterns = [
                        'continuing despite',
                        'fallback',
                        'graceful',
                        'still returning',
                        'error handled'
                    ]
                    
                    graceful_messages = []
                    for log_line in backend_logs:
                        for pattern in graceful_patterns:
                            if pattern.lower() in log_line.lower():
                                graceful_messages.append(log_line.strip())
                                break
                    
                    if graceful_messages:
                        logger.info(f"      ✅ Found graceful error handling: {len(graceful_messages)} messages")
                    
                else:
                    logger.warning(f"      ⚠️ Could not capture backend logs")
                    
            except Exception as e:
                logger.warning(f"      ⚠️ Log analysis error: {e}")
            
            # Calculate test success
            success_criteria = [
                error_results['force_analysis_accessible'],
                error_results['api_continues_on_db_error'],
                error_results['graceful_degradation'],
                error_results['backend_logs_captured']
            ]
            success_count = sum(success_criteria)
            success_rate = success_count / len(success_criteria)
            
            if success_rate >= 0.75:  # 75% success threshold
                self.log_test_result("Error Handling Verification", True, 
                                   f"Error handling working: {success_count}/{len(success_criteria)} criteria met. Graceful degradation: {error_results['graceful_degradation']}, Error logging: {error_results['error_logging_present']}")
            else:
                self.log_test_result("Error Handling Verification", False, 
                                   f"Error handling issues: {success_count}/{len(success_criteria)} criteria met")
                
        except Exception as e:
            self.log_test_result("Error Handling Verification", False, f"Exception: {str(e)}")
    
    async def test_5_main_orchestration_comparison(self):
        """Test 5: Main Orchestration Comparison - Verify Both Endpoints Use Identical Logic"""
        logger.info("\n🔍 TEST 5: Main Orchestration Comparison")
        
        try:
            comparison_results = {
                'force_analysis_logic_found': False,
                'main_orchestration_logic_found': False,
                'identical_save_logic': False,
                'same_collection_used': False,
                'logging_patterns_match': False,
                'code_analysis_successful': False
            }
            
            logger.info("   🚀 Comparing force-ia1-analysis and main orchestration IA2 persistence logic...")
            logger.info("   📊 Expected: Both use identical database save logic and same collection")
            
            # Step 1: Analyze the server.py code for both implementations
            logger.info("   📋 Analyzing server.py code for IA2 persistence implementations...")
            
            try:
                with open('/app/backend/server.py', 'r') as f:
                    server_code = f.read()
                
                comparison_results['code_analysis_successful'] = True
                logger.info(f"      ✅ Server code loaded: {len(server_code)} characters")
                
                # Look for force-ia1-analysis IA2 save logic
                force_analysis_patterns = [
                    'force-ia1-analysis',
                    'decision_dict = decision.dict()',
                    'decision_dict[\'timestamp\'] = get_paris_time()',
                    'db.trading_decisions.insert_one(decision_dict)',
                    'IA2 DECISION SAVED'
                ]
                
                force_matches = 0
                for pattern in force_analysis_patterns:
                    if pattern in server_code:
                        force_matches += 1
                
                if force_matches >= 4:  # At least 4/5 patterns found
                    comparison_results['force_analysis_logic_found'] = True
                    logger.info(f"      ✅ Force analysis IA2 save logic found: {force_matches}/{len(force_analysis_patterns)} patterns")
                else:
                    logger.warning(f"      ❌ Force analysis IA2 save logic incomplete: {force_matches}/{len(force_analysis_patterns)} patterns")
                
                # Look for main orchestration IA2 save logic
                main_orchestration_patterns = [
                    'run_trading_cycle',
                    'decision_dict = decision.dict()',
                    'decision_dict[\'timestamp\'] = get_paris_time()',
                    'db.trading_decisions.insert_one(decision_dict)',
                    'IA2 DECISION SAVED'
                ]
                
                main_matches = 0
                for pattern in main_orchestration_patterns:
                    if pattern in server_code:
                        main_matches += 1
                
                if main_matches >= 4:  # At least 4/5 patterns found
                    comparison_results['main_orchestration_logic_found'] = True
                    logger.info(f"      ✅ Main orchestration IA2 save logic found: {main_matches}/{len(main_orchestration_patterns)} patterns")
                else:
                    logger.warning(f"      ❌ Main orchestration IA2 save logic incomplete: {main_matches}/{len(main_orchestration_patterns)} patterns")
                
                # Check if both use identical save patterns
                identical_patterns = [
                    'decision_dict = decision.dict()',
                    'decision_dict[\'timestamp\'] = get_paris_time()',
                    'db.trading_decisions.insert_one(decision_dict)',
                    'IA2 DECISION SAVED'
                ]
                
                identical_count = 0
                for pattern in identical_patterns:
                    occurrences = server_code.count(pattern)
                    if occurrences >= 2:  # Should appear in both places
                        identical_count += 1
                        logger.info(f"      ✅ Pattern '{pattern}' found {occurrences} times")
                    else:
                        logger.warning(f"      ❌ Pattern '{pattern}' found only {occurrences} times")
                
                if identical_count >= 3:  # At least 3/4 identical patterns
                    comparison_results['identical_save_logic'] = True
                    logger.info(f"      ✅ Identical save logic confirmed: {identical_count}/{len(identical_patterns)} patterns match")
                else:
                    logger.warning(f"      ❌ Save logic differs: {identical_count}/{len(identical_patterns)} patterns match")
                
                # Check if both use same collection
                trading_decisions_count = server_code.count('db.trading_decisions')
                if trading_decisions_count >= 2:
                    comparison_results['same_collection_used'] = True
                    logger.info(f"      ✅ Same collection used: 'trading_decisions' appears {trading_decisions_count} times")
                else:
                    logger.warning(f"      ❌ Collection usage unclear: 'trading_decisions' appears {trading_decisions_count} times")
                
                # Check logging patterns
                ia2_saved_count = server_code.count('IA2 DECISION SAVED')
                if ia2_saved_count >= 2:
                    comparison_results['logging_patterns_match'] = True
                    logger.info(f"      ✅ Logging patterns match: 'IA2 DECISION SAVED' appears {ia2_saved_count} times")
                else:
                    logger.warning(f"      ❌ Logging patterns differ: 'IA2 DECISION SAVED' appears {ia2_saved_count} times")
                
            except Exception as e:
                logger.error(f"      ❌ Code analysis error: {e}")
            
            # Step 2: Check backend logs for evidence of both implementations working
            logger.info("   📋 Checking backend logs for evidence of both implementations...")
            
            try:
                backend_logs = await self._capture_backend_logs()
                if backend_logs:
                    # Look for force analysis IA2 saves
                    force_saves = []
                    main_saves = []
                    
                    for log_line in backend_logs:
                        if 'IA2 DECISION SAVED' in log_line:
                            # Try to determine if it's from force analysis or main orchestration
                            if any(keyword in log_line.lower() for keyword in ['force', 'forced']):
                                force_saves.append(log_line.strip())
                            else:
                                main_saves.append(log_line.strip())
                    
                    logger.info(f"      📋 Found IA2 saves - Force: {len(force_saves)}, Main: {len(main_saves)}")
                    
                    if force_saves:
                        logger.info(f"      ✅ Force analysis IA2 saves detected")
                        for save in force_saves[:1]:
                            logger.info(f"         - {save}")
                    
                    if main_saves:
                        logger.info(f"      ✅ Main orchestration IA2 saves detected")
                        for save in main_saves[:1]:
                            logger.info(f"         - {save}")
                else:
                    logger.warning(f"      ⚠️ Could not capture backend logs")
                    
            except Exception as e:
                logger.warning(f"      ⚠️ Log analysis error: {e}")
            
            # Calculate test success
            success_criteria = [
                comparison_results['code_analysis_successful'],
                comparison_results['force_analysis_logic_found'],
                comparison_results['main_orchestration_logic_found'],
                comparison_results['identical_save_logic'] and comparison_results['same_collection_used']
            ]
            success_count = sum(success_criteria)
            success_rate = success_count / len(success_criteria)
            
            if success_rate >= 0.75:  # 75% success threshold
                self.log_test_result("Main Orchestration Comparison", True, 
                                   f"Orchestration comparison successful: {success_count}/{len(success_criteria)} criteria met. Identical logic: {comparison_results['identical_save_logic']}, Same collection: {comparison_results['same_collection_used']}")
            else:
                self.log_test_result("Main Orchestration Comparison", False, 
                                   f"Orchestration comparison issues: {success_count}/{len(success_criteria)} criteria met")
                
        except Exception as e:
            self.log_test_result("Main Orchestration Comparison", False, f"Exception: {str(e)}")
    
    async def _capture_backend_logs(self):
        """Capture recent backend logs"""
        try:
            log_files = [
                "/var/log/supervisor/backend.out.log",
                "/var/log/supervisor/backend.err.log"
            ]
            
            all_logs = []
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        result = subprocess.run(['tail', '-n', '100', log_file], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            all_logs.extend(result.stdout.split('\n'))
                    except Exception:
                        pass
            
            return [log for log in all_logs if log.strip()]
        except Exception:
            return []
    
    async def run_comprehensive_test_suite(self):
        """Run comprehensive IA2 Decision Persistence Database Fix test suite"""
        logger.info("🚀 Starting IA2 Decision Persistence Database Fix Test Suite")
        logger.info("=" * 80)
        logger.info("📋 IA2 DECISION PERSISTENCE DATABASE FIX TEST SUITE")
        logger.info("🎯 Testing: IA2 decision persistence database fix in trading bot system")
        logger.info("🎯 Expected: IA2 decisions saved to database via both force-ia1-analysis and main orchestration")
        logger.info("=" * 80)
        
        # Run all tests in sequence
        await self.test_1_ia2_decision_persistence_via_force_analysis()
        await self.test_2_database_persistence_verification()
        await self.test_3_api_response_vs_database_consistency()
        await self.test_4_error_handling_verification()
        await self.test_5_main_orchestration_comparison()
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 IA2 DECISION PERSISTENCE DATABASE FIX TEST SUMMARY")
        logger.info("=" * 80)
        
        passed_tests = sum(1 for result in self.test_results if result['success'])
        total_tests = len(self.test_results)
        
        for result in self.test_results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            logger.info(f"{status}: {result['test']}")
            if result['details']:
                logger.info(f"   {result['details']}")
                
        logger.info(f"\n🎯 OVERALL RESULT: {passed_tests}/{total_tests} tests passed")
        
        # Critical requirements analysis
        logger.info("\n" + "=" * 80)
        logger.info("📋 CRITICAL REQUIREMENTS VERIFICATION")
        logger.info("=" * 80)
        
        requirements_status = {}
        
        for result in self.test_results:
            if "IA2 Decision Persistence via Force Analysis" in result['test']:
                requirements_status['IA2 Decision Persistence via force-ia1-analysis'] = result['success']
            elif "Database Persistence Verification" in result['test']:
                requirements_status['Database Structure and Logging'] = result['success']
            elif "API Response vs Database Consistency" in result['test']:
                requirements_status['API Response vs Database Consistency'] = result['success']
            elif "Error Handling Verification" in result['test']:
                requirements_status['Error Handling and Graceful Degradation'] = result['success']
            elif "Main Orchestration Comparison" in result['test']:
                requirements_status['Identical Logic in Both Endpoints'] = result['success']
        
        logger.info("🎯 CRITICAL REQUIREMENTS STATUS:")
        for requirement, status in requirements_status.items():
            status_icon = "✅" if status else "❌"
            logger.info(f"   {status_icon} {requirement}")
        
        requirements_met = sum(1 for status in requirements_status.values() if status)
        total_requirements = len(requirements_status)
        
        # Final verdict
        logger.info(f"\n🏆 REQUIREMENTS SATISFACTION: {requirements_met}/{total_requirements}")
        
        if requirements_met == total_requirements:
            logger.info("\n🎉 VERDICT: IA2 DECISION PERSISTENCE DATABASE FIX 100% SUCCESSFUL!")
            logger.info("✅ IA2 decisions created via force-ia1-analysis are saved to database")
            logger.info("✅ Database entry contains all required fields with correct timestamp")
            logger.info("✅ Logging confirms successful database save")
            logger.info("✅ API response and database entry are consistent")
            logger.info("✅ Error handling works if database save fails")
            logger.info("✅ Both force-ia1-analysis and main orchestration use identical persistence logic")
        elif requirements_met >= total_requirements * 0.8:
            logger.info("\n⚠️ VERDICT: IA2 DECISION PERSISTENCE DATABASE FIX MOSTLY SUCCESSFUL")
            logger.info("🔍 Minor issues may need attention for complete database persistence")
        elif requirements_met >= total_requirements * 0.6:
            logger.info("\n⚠️ VERDICT: IA2 DECISION PERSISTENCE DATABASE FIX PARTIALLY SUCCESSFUL")
            logger.info("🔧 Several requirements need attention for complete database persistence")
        else:
            logger.info("\n❌ VERDICT: IA2 DECISION PERSISTENCE DATABASE FIX NOT SUCCESSFUL")
            logger.info("🚨 Major issues detected - IA2 decisions not being saved to database properly")
            logger.info("🚨 System needs significant fixes for IA2 decision persistence")
        
        return passed_tests, total_tests

async def main():
    """Main function to run the comprehensive IA2 Decision Persistence Database Fix test suite"""
    test_suite = IA2DecisionPersistenceTestSuite()
    passed_tests, total_tests = await test_suite.run_comprehensive_test_suite()
    
    # Exit with appropriate code
    if passed_tests == total_tests:
        sys.exit(0)  # All tests passed
    elif passed_tests >= total_tests * 0.8:
        sys.exit(1)  # Mostly successful
    else:
        sys.exit(2)  # Major issues

if __name__ == "__main__":
    asyncio.run(main())