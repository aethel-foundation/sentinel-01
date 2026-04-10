#!/usr/bin/env python3
"""
Sentinel-01 Backend API Testing
AETHEL Finance Lab - Comprehensive API Test Suite

Tests all backend endpoints for the ERC-8004 capital protection agent.
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class Sentinel01APITester:
    def __init__(self, base_url="https://governance-protocol.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int = 200, 
                 data: Optional[Dict] = None, params: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Non-dict response'}")
                except:
                    response_data = {}
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                print(f"   Error: {response.text[:200]}")
                response_data = {}

            self.test_results.append({
                "name": name,
                "endpoint": endpoint,
                "method": method,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "success": success,
                "response_size": len(response.text) if response.text else 0
            })

            return success, response_data

        except requests.exceptions.Timeout:
            print(f"❌ FAILED - Request timeout (30s)")
            self.test_results.append({
                "name": name,
                "endpoint": endpoint,
                "method": method,
                "status_code": 0,
                "expected_status": expected_status,
                "success": False,
                "error": "Timeout"
            })
            return False, {}
        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "endpoint": endpoint,
                "method": method,
                "status_code": 0,
                "expected_status": expected_status,
                "success": False,
                "error": str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test GET /api/ - root endpoint returns Sentinel-01 info"""
        success, response = self.run_test(
            "Root Endpoint",
            "GET",
            "",
            200
        )
        if success and response:
            required_fields = ["name", "organization", "version", "status"]
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
            else:
                print(f"   ✅ All required fields present")
                print(f"   Agent: {response.get('name')} v{response.get('version')}")
        return success

    def test_agent_status(self):
        """Test GET /api/agent/status - returns agent status with policy_hash, portfolio, metrics"""
        success, response = self.run_test(
            "Agent Status",
            "GET",
            "agent/status",
            200
        )
        if success and response:
            required_fields = ["agent_id", "version", "policy_hash", "running", "cycle_count", "portfolio", "metrics"]
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
            else:
                print(f"   ✅ All required fields present")
                print(f"   Policy Hash: {response.get('policy_hash', '')[:16]}...")
                print(f"   Cycles: {response.get('cycle_count', 0)}")
        return success

    def test_agent_cycle(self, asset="ETH"):
        """Test POST /api/agent/cycle?asset=ETH/BTC - runs cycle and returns ValidationArtifact"""
        success, response = self.run_test(
            f"Agent Cycle ({asset})",
            "POST",
            "agent/cycle",
            200,
            params={"asset": asset}
        )
        if success and response:
            required_fields = ["artifact_id", "timestamp", "regime", "action_taken", "artifact_hash"]
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
            else:
                print(f"   ✅ ValidationArtifact generated")
                print(f"   Artifact ID: {response.get('artifact_id', '')[:16]}...")
                print(f"   Action: {response.get('action_taken')}")
                print(f"   Regime: {response.get('regime')}")
        return success

    def test_market_price(self, asset="ETH"):
        """Test GET /api/market/price/ETH/BTC - returns real price from CoinGecko"""
        success, response = self.run_test(
            f"Market Price ({asset})",
            "GET",
            f"market/price/{asset}",
            200
        )
        if success and response:
            if "price" in response and response["price"] > 0:
                print(f"   ✅ Price data received: ${response['price']:,.2f}")
                if "volume_24h" in response:
                    print(f"   Volume 24h: ${response['volume_24h']:,.0f}")
            else:
                print(f"   ⚠️  Invalid price data")
        return success

    def test_artifacts_recent(self):
        """Test GET /api/artifacts/recent - returns recent ValidationArtifacts"""
        success, response = self.run_test(
            "Recent Artifacts",
            "GET",
            "artifacts/recent",
            200,
            params={"count": 10}
        )
        if success:
            if isinstance(response, list):
                print(f"   ✅ Received {len(response)} artifacts")
                if response:
                    artifact = response[0]
                    if "artifact_id" in artifact and "timestamp" in artifact:
                        print(f"   Latest: {artifact.get('artifact_id', '')[:16]}...")
            else:
                print(f"   ⚠️  Expected list, got {type(response)}")
        return success

    def test_risk_limits(self):
        """Test GET /api/risk/limits - returns risk limits"""
        success, response = self.run_test(
            "Risk Limits",
            "GET",
            "risk/limits",
            200
        )
        if success and response:
            required_fields = ["max_drawdown_pct", "max_single_trade_pct", "max_daily_loss_pct", "max_position_pct"]
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
            else:
                print(f"   ✅ Risk limits configured")
                print(f"   Max Drawdown: {response.get('max_drawdown_pct')}%")
                print(f"   Max Trade: {response.get('max_single_trade_pct')}%")
        return success

    def test_policy_summary(self):
        """Test GET /api/policy/summary - returns policy engine summary"""
        success, response = self.run_test(
            "Policy Summary",
            "GET",
            "policy/summary",
            200
        )
        if success:
            print(f"   ✅ Policy summary received")
        return success

    def test_portfolio_state(self):
        """Test GET /api/portfolio/state - returns portfolio state"""
        success, response = self.run_test(
            "Portfolio State",
            "GET",
            "portfolio/state",
            200
        )
        if success and response:
            if "total_value" in response:
                print(f"   ✅ Portfolio value: ${response.get('total_value', 0):,.2f}")
                print(f"   Cash: ${response.get('cash_balance', 0):,.2f}")
                print(f"   Drawdown: {response.get('current_drawdown', 0):.2%}")
            else:
                print(f"   ⚠️  Missing portfolio data")
        return success

    def test_governance_status(self):
        """Test GET /api/governance/status - returns governance status"""
        success, response = self.run_test(
            "Governance Status",
            "GET",
            "governance/status",
            200
        )
        if success:
            print(f"   ✅ Governance status received")
        return success

    def test_emergency_status(self):
        """Test GET /api/emergency/status - returns emergency protocol status"""
        success, response = self.run_test(
            "Emergency Status",
            "GET",
            "emergency/status",
            200
        )
        if success and response:
            if "is_trading_paused" in response:
                print(f"   ✅ Trading paused: {response.get('is_trading_paused')}")
                print(f"   Emergency active: {response.get('is_emergency_active', False)}")
            else:
                print(f"   ⚠️  Missing emergency status fields")
        return success

    def test_emergency_pause(self):
        """Test POST /api/emergency/pause - pauses trading"""
        success, response = self.run_test(
            "Emergency Pause",
            "POST",
            "emergency/pause",
            200
        )
        if success and response:
            if "status" in response and "paused" in response["status"]:
                print(f"   ✅ Trading paused successfully")
            else:
                print(f"   ⚠️  Unexpected pause response")
        return success

    def test_emergency_resume(self):
        """Test POST /api/emergency/resume - resumes trading"""
        success, response = self.run_test(
            "Emergency Resume",
            "POST",
            "emergency/resume",
            200
        )
        if success and response:
            if "status" in response and "resumed" in response["status"]:
                print(f"   ✅ Trading resumed successfully")
            else:
                print(f"   ⚠️  Unexpected resume response")
        return success

    def test_reputation_metrics(self):
        """Test GET /api/reputation/metrics - returns reputation metrics"""
        success, response = self.run_test(
            "Reputation Metrics",
            "GET",
            "reputation/metrics",
            200
        )
        if success and response:
            if "total_cycles" in response:
                print(f"   ✅ Metrics received")
                print(f"   Total cycles: {response.get('total_cycles', 0)}")
                print(f"   Success rate: {response.get('success_rate', 0)}%")
            else:
                print(f"   ⚠️  Missing metrics fields")
        return success

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("=" * 60)
        print("🛡️  SENTINEL-01 API TEST SUITE")
        print("   AETHEL Finance Lab - ERC-8004 Agent")
        print("=" * 60)
        print(f"Backend URL: {self.base_url}")
        print(f"API URL: {self.api_url}")
        
        # Core API tests
        print("\n📡 CORE API TESTS")
        self.test_root_endpoint()
        self.test_agent_status()
        
        # Market data tests
        print("\n📈 MARKET DATA TESTS")
        self.test_market_price("ETH")
        self.test_market_price("BTC")
        
        # Agent operation tests
        print("\n🤖 AGENT OPERATION TESTS")
        self.test_agent_cycle("ETH")
        self.test_agent_cycle("BTC")
        self.test_artifacts_recent()
        
        # Risk and policy tests
        print("\n🛡️  RISK & POLICY TESTS")
        self.test_risk_limits()
        self.test_policy_summary()
        self.test_portfolio_state()
        
        # Governance tests
        print("\n🏛️  GOVERNANCE TESTS")
        self.test_governance_status()
        self.test_reputation_metrics()
        
        # Emergency protocol tests
        print("\n🚨 EMERGENCY PROTOCOL TESTS")
        self.test_emergency_status()
        self.test_emergency_pause()
        self.test_emergency_resume()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        # Show failed tests
        failed_tests = [test for test in self.test_results if not test["success"]]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                error_msg = test.get('error', f'Status {test["status_code"]}')
                print(f"   • {test['name']}: {error_msg}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = Sentinel01APITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n💥 Test suite error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())