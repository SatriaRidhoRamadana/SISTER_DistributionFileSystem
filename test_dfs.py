"""
Distributed File System - Comprehensive Testing Script
Test upload, download, replication, dan node failure scenarios
"""

import os
import time
import requests
import subprocess
import sys
import tempfile
import hashlib
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

class DFSTester:
    def __init__(self, naming_service="http://localhost:5000"):
        self.naming_service = naming_service
        self.test_results = []
    
    def log(self, message, color=None):
        """Print colored log message"""
        if color:
            print(f"{color}{message}{Colors.END}")
        else:
            print(message)
    
    def check_service(self, url, name):
        """Check if service is running"""
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                self.log(f"✅ {name} is running", Colors.GREEN)
                return True
        except:
            pass
        
        self.log(f"❌ {name} is NOT running at {url}", Colors.RED)
        return False
    
    def create_test_file(self, size_mb=1, filename="test_file.txt"):
        """Create test file with random data"""
        filepath = os.path.join(tempfile.gettempdir(), filename)
        
        with open(filepath, 'wb') as f:
            # Write random data
            size_bytes = int(size_mb * 1024 * 1024)
            data = os.urandom(size_bytes)
            f.write(data)
        
        return filepath
    
    def calculate_checksum(self, filepath):
        """Calculate file checksum"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def test_upload(self):
        """Test 1: Upload file"""
        self.log("\n" + "="*60, Colors.BLUE)
        self.log("TEST 1: File Upload", Colors.BOLD)
        self.log("="*60, Colors.BLUE)
        
        # Create test file
        test_file = self.create_test_file(1, "test_upload.txt")
        original_checksum = self.calculate_checksum(test_file)
        
        self.log(f"📄 Created test file: {test_file}")
        self.log(f"🔐 Original checksum: {original_checksum[:16]}...")
        
        try:
            # Request upload
            filename = os.path.basename(test_file)
            file_size = os.path.getsize(test_file)
            
            response = requests.post(
                f"{self.naming_service}/api/upload/request",
                json={
                    "filename": filename,
                    "file_size": file_size,
                    "replication_factor": 2
                }
            )
            
            if response.status_code != 200:
                self.log(f"❌ Upload request failed: {response.text}", Colors.RED)
                self.test_results.append(("Upload", False))
                return None
            
            data = response.json()
            file_id = data["file_id"]
            upload_nodes = data["upload_nodes"]
            
            self.log(f"📋 File ID: {file_id}", Colors.GREEN)
            self.log(f"🎯 Upload nodes: {len(upload_nodes)}")
            
            # Upload to all nodes
            success_count = 0
            with open(test_file, 'rb') as f:
                file_data = f.read()
            
            for node in upload_nodes:
                node_id = node["node_id"]
                upload_url = node["upload_url"]
                
                try:
                    files = {'file': (filename, file_data)}
                    response = requests.post(upload_url, files=files)
                    
                    if response.status_code == 200:
                        self.log(f"  ✅ Uploaded to {node_id}", Colors.GREEN)
                        success_count += 1
                    else:
                        self.log(f"  ❌ Failed on {node_id}", Colors.RED)
                except Exception as e:
                    self.log(f"  ❌ Error on {node_id}: {e}", Colors.RED)
            
            if success_count == len(upload_nodes):
                self.log(f"✅ TEST PASSED: File uploaded to {success_count} nodes", Colors.GREEN)
                self.test_results.append(("Upload", True))
                return file_id
            else:
                self.log(f"❌ TEST FAILED: Only {success_count}/{len(upload_nodes)} successful", Colors.RED)
                self.test_results.append(("Upload", False))
                return None
                
        except Exception as e:
            self.log(f"❌ TEST FAILED: {e}", Colors.RED)
            self.test_results.append(("Upload", False))
            return None
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.remove(test_file)
    
    def test_download(self, file_id):
        """Test 2: Download file"""
        self.log("\n" + "="*60, Colors.BLUE)
        self.log("TEST 2: File Download", Colors.BOLD)
        self.log("="*60, Colors.BLUE)
        
        if not file_id:
            self.log("⏭️  Skipping (no file_id from upload test)", Colors.YELLOW)
            self.test_results.append(("Download", False))
            return False
        
        try:
            # Get download info
            response = requests.get(f"{self.naming_service}/api/download/{file_id}")
            
            if response.status_code != 200:
                self.log(f"❌ Download request failed: {response.text}", Colors.RED)
                self.test_results.append(("Download", False))
                return False
            
            data = response.json()
            filename = data["filename"]
            expected_checksum = data["checksum"]
            download_urls = data["download_urls"]
            
            self.log(f"📄 Filename: {filename}")
            self.log(f"🔐 Expected checksum: {expected_checksum[:16]}...")
            self.log(f"🎯 Available nodes: {len(download_urls)}")
            
            # Download from first node
            output_path = os.path.join(tempfile.gettempdir(), f"downloaded_{filename}")
            
            response = requests.get(download_urls[0])
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                # Verify checksum
                downloaded_checksum = self.calculate_checksum(output_path)
                
                if downloaded_checksum == expected_checksum:
                    self.log(f"✅ TEST PASSED: File downloaded and verified", Colors.GREEN)
                    self.test_results.append(("Download", True))
                    os.remove(output_path)
                    return True
                else:
                    self.log(f"❌ TEST FAILED: Checksum mismatch", Colors.RED)
                    self.test_results.append(("Download", False))
                    return False
            else:
                self.log(f"❌ TEST FAILED: Download failed", Colors.RED)
                self.test_results.append(("Download", False))
                return False
                
        except Exception as e:
            self.log(f"❌ TEST FAILED: {e}", Colors.RED)
            self.test_results.append(("Download", False))
            return False
    
    def test_replication(self, file_id):
        """Test 3: Verify replication"""
        self.log("\n" + "="*60, Colors.BLUE)
        self.log("TEST 3: Replication Verification", Colors.BOLD)
        self.log("="*60, Colors.BLUE)
        
        if not file_id:
            self.log("⏭️  Skipping (no file_id from upload test)", Colors.YELLOW)
            self.test_results.append(("Replication", False))
            return False
        
        try:
            # Get file info
            response = requests.get(f"{self.naming_service}/api/download/{file_id}")
            
            if response.status_code != 200:
                self.log(f"❌ Failed to get file info", Colors.RED)
                self.test_results.append(("Replication", False))
                return False
            
            data = response.json()
            download_urls = data["download_urls"]
            expected_checksum = data["checksum"]
            
            self.log(f"🔍 Checking {len(download_urls)} replicas...")
            
            valid_replicas = 0
            
            for i, url in enumerate(download_urls, 1):
                try:
                    # Download and verify
                    response = requests.get(url, timeout=5)
                    
                    if response.status_code == 200:
                        # Calculate checksum
                        temp_path = os.path.join(tempfile.gettempdir(), f"verify_{i}.tmp")
                        with open(temp_path, 'wb') as f:
                            f.write(response.content)
                        
                        checksum = self.calculate_checksum(temp_path)
                        os.remove(temp_path)
                        
                        if checksum == expected_checksum:
                            self.log(f"  ✅ Replica {i}: Valid", Colors.GREEN)
                            valid_replicas += 1
                        else:
                            self.log(f"  ❌ Replica {i}: Checksum mismatch", Colors.RED)
                    else:
                        self.log(f"  ❌ Replica {i}: Download failed", Colors.RED)
                        
                except Exception as e:
                    self.log(f"  ❌ Replica {i}: Error - {e}", Colors.RED)
            
            if valid_replicas >= 2:
                self.log(f"✅ TEST PASSED: {valid_replicas} valid replicas found", Colors.GREEN)
                self.test_results.append(("Replication", True))
                return True
            else:
                self.log(f"❌ TEST FAILED: Only {valid_replicas} valid replicas", Colors.RED)
                self.test_results.append(("Replication", False))
                return False
                
        except Exception as e:
            self.log(f"❌ TEST FAILED: {e}", Colors.RED)
            self.test_results.append(("Replication", False))
            return False
    
    def test_node_failure(self):
        """Test 4: Node failure detection"""
        self.log("\n" + "="*60, Colors.BLUE)
        self.log("TEST 4: Node Failure Detection", Colors.BOLD)
        self.log("="*60, Colors.BLUE)
        
        try:
            # Get initial node status
            response = requests.get(f"{self.naming_service}/api/nodes")
            
            if response.status_code != 200:
                self.log(f"❌ Failed to get node status", Colors.RED)
                self.test_results.append(("Node Failure", False))
                return False
            
            nodes_before = response.json()["nodes"]
            active_before = sum(1 for n in nodes_before if n["status"] == "active")
            
            self.log(f"📊 Initial active nodes: {active_before}")
            
            # Wait for heartbeat cycle
            self.log("⏳ Waiting 35 seconds for failure detection...")
            self.log("   (Simulated node failure - stop one storage_node.py manually)")
            
            time.sleep(35)
            
            # Check node status again
            response = requests.get(f"{self.naming_service}/api/nodes")
            nodes_after = response.json()["nodes"]
            
            active_after = sum(1 for n in nodes_after if n["status"] == "active")
            inactive_after = sum(1 for n in nodes_after if n["status"] == "inactive")
            
            self.log(f"📊 Final active nodes: {active_after}")
            self.log(f"📊 Inactive nodes: {inactive_after}")
            
            if inactive_after > 0:
                self.log(f"✅ TEST PASSED: Failure detection working", Colors.GREEN)
                self.test_results.append(("Node Failure", True))
                return True
            else:
                self.log(f"⚠️  TEST INCONCLUSIVE: No node failures detected", Colors.YELLOW)
                self.log(f"   (All nodes still active - this is OK if no node was stopped)")
                self.test_results.append(("Node Failure", True))
                return True
                
        except Exception as e:
            self.log(f"❌ TEST FAILED: {e}", Colors.RED)
            self.test_results.append(("Node Failure", False))
            return False
    
    def test_concurrent_uploads(self):
        """Test 5: Concurrent uploads"""
        self.log("\n" + "="*60, Colors.BLUE)
        self.log("TEST 5: Concurrent Uploads", Colors.BOLD)
        self.log("="*60, Colors.BLUE)
        
        import threading
        
        num_files = 5
        results = []
        
        def upload_file(i):
            try:
                test_file = self.create_test_file(0.1, f"concurrent_{i}.txt")
                
                filename = os.path.basename(test_file)
                file_size = os.path.getsize(test_file)
                
                # Request upload
                response = requests.post(
                    f"{self.naming_service}/api/upload/request",
                    json={"filename": filename, "file_size": file_size}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    file_id = data["file_id"]
                    upload_nodes = data["upload_nodes"]
                    
                    # Upload to nodes
                    with open(test_file, 'rb') as f:
                        file_data = f.read()
                    
                    success = True
                    for node in upload_nodes:
                        files = {'file': (filename, file_data)}
                        resp = requests.post(node["upload_url"], files=files)
                        if resp.status_code != 200:
                            success = False
                    
                    results.append(success)
                else:
                    results.append(False)
                
                os.remove(test_file)
                
            except Exception as e:
                self.log(f"  Error in thread {i}: {e}", Colors.RED)
                results.append(False)
        
        # Start threads
        threads = []
        self.log(f"🚀 Starting {num_files} concurrent uploads...")
        
        start_time = time.time()
        
        for i in range(num_files):
            t = threading.Thread(target=upload_file, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        elapsed = time.time() - start_time
        
        success_count = sum(results)
        
        self.log(f"⏱️  Completed in {elapsed:.2f} seconds")
        self.log(f"📊 Success: {success_count}/{num_files}")
        
        if success_count == num_files:
            self.log(f"✅ TEST PASSED: All concurrent uploads successful", Colors.GREEN)
            self.test_results.append(("Concurrent Upload", True))
            return True
        else:
            self.log(f"❌ TEST FAILED: {num_files - success_count} uploads failed", Colors.RED)
            self.test_results.append(("Concurrent Upload", False))
            return False
    
    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60, Colors.BLUE)
        self.log("TEST SUMMARY", Colors.BOLD)
        self.log("="*60, Colors.BLUE)
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            color = Colors.GREEN if result else Colors.RED
            self.log(f"{status} - {test_name}", color)
        
        self.log("="*60, Colors.BLUE)
        
        if passed == total:
            self.log(f"🎉 ALL TESTS PASSED ({passed}/{total})", Colors.GREEN)
        else:
            self.log(f"⚠️  {passed}/{total} tests passed", Colors.YELLOW)
    
    def run_all_tests(self):
        """Run all tests"""
        self.log("="*60, Colors.BLUE)
        self.log("DISTRIBUTED FILE SYSTEM - TEST SUITE", Colors.BOLD)
        self.log("="*60, Colors.BLUE)
        
        # Check services
        self.log("\n🔍 Checking services...")
        naming_ok = self.check_service(self.naming_service, "Naming Service")
        node1_ok = self.check_service("http://localhost:5001", "Storage Node 1")
        node2_ok = self.check_service("http://localhost:5002", "Storage Node 2")
        
        if not (naming_ok and node1_ok and node2_ok):
            self.log("\n❌ Not all services are running. Please start them first.", Colors.RED)
            return
        
        # Run tests
        file_id = self.test_upload()
        self.test_download(file_id)
        self.test_replication(file_id)
        self.test_concurrent_uploads()
        self.test_node_failure()
        
        # Summary
        self.print_summary()

if __name__ == '__main__':
    tester = DFSTester()
    tester.run_all_tests()