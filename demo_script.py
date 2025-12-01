"""
DFS Demo Script - Automated Testing & Demo
Generate test files dan upload via API untuk demo Web UI
"""

import requests
import os
import tempfile
import time
import random
from datetime import datetime

class DFSDemo:
    def __init__(self, naming_service="http://localhost:5000"):
        self.naming_service = naming_service
    
    def check_system(self):
        """Check if system is running"""
        try:
            response = requests.get(f"{self.naming_service}/health", timeout=2)
            if response.status_code == 200:
                print("✅ Naming Service is running")
                return True
        except:
            pass
        
        print("❌ Naming Service is NOT running")
        print("   Please start the system first:")
        print("   python naming_service.py")
        return False
    
    def create_demo_file(self, filename, size_mb=1):
        """Create demo file with random data"""
        filepath = os.path.join(tempfile.gettempdir(), filename)
        
        with open(filepath, 'wb') as f:
            # Write random data
            size_bytes = int(size_mb * 1024 * 1024)
            data = os.urandom(size_bytes)
            f.write(data)
        
        return filepath
    
    def upload_file(self, filepath, replication_factor=2):
        """Upload file to DFS"""
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        
        print(f"\n📤 Uploading: {filename} ({file_size / (1024**2):.2f} MB)")
        
        try:
            # Request upload
            response = requests.post(
                f"{self.naming_service}/api/upload/request",
                json={
                    "filename": filename,
                    "file_size": file_size,
                    "replication_factor": replication_factor
                },
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"   ❌ Upload request failed: {response.text}")
                return False
            
            data = response.json()
            file_id = data["file_id"]
            upload_nodes = data["upload_nodes"]
            
            # Upload to all nodes
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            success_count = 0
            for node in upload_nodes:
                try:
                    files = {'file': (filename, file_data)}
                    response = requests.post(node["upload_url"], files=files, timeout=30)
                    
                    if response.status_code == 200:
                        success_count += 1
                except:
                    pass
            
            if success_count > 0:
                print(f"   ✅ Uploaded to {success_count} nodes")
                print(f"   📋 File ID: {file_id}")
                return True
            else:
                print(f"   ❌ Upload failed on all nodes")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def generate_demo_files(self):
        """Generate various demo files"""
        print("\n" + "="*60)
        print("🎬 GENERATING DEMO FILES")
        print("="*60)
        
        demo_files = [
            ("document.pdf", 0.5),
            ("presentation.pptx", 1.2),
            ("image.jpg", 0.3),
            ("video.mp4", 2.5),
            ("database.sql", 0.8),
            ("archive.zip", 1.5),
            ("spreadsheet.xlsx", 0.4),
            ("code.py", 0.1),
        ]
        
        uploaded = 0
        
        for filename, size_mb in demo_files:
            print(f"\n📝 Creating: {filename}")
            filepath = self.create_demo_file(filename, size_mb)
            
            if self.upload_file(filepath, replication_factor=2):
                uploaded += 1
            
            # Cleanup
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # Small delay between uploads
            time.sleep(0.5)
        
        print("\n" + "="*60)
        print(f"✅ Demo complete! {uploaded}/{len(demo_files)} files uploaded")
        print("="*60)
        print(f"\n🌐 Open Web UI at: {self.naming_service}")
        print("   You should see all uploaded files in the dashboard")
        print("="*60)
    
    def show_stats(self):
        """Show system statistics"""
        try:
            response = requests.get(f"{self.naming_service}/api/stats", timeout=5)
            
            if response.status_code == 200:
                stats = response.json()
                
                print("\n" + "="*60)
                print("📊 SYSTEM STATISTICS")
                print("="*60)
                print(f"Total Files:     {stats['total_files']}")
                print(f"Active Nodes:    {stats['active_nodes']}")
                print(f"Total Storage:   {stats['total_size_mb']:.2f} MB")
                print(f"Recent Uploads:  {stats['recent_uploads']}")
                print("="*60)
                
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
    
    def stress_test(self, num_files=10, size_mb=0.5):
        """Stress test with multiple uploads"""
        print("\n" + "="*60)
        print(f"🔥 STRESS TEST - {num_files} files")
        print("="*60)
        
        start_time = time.time()
        success = 0
        
        for i in range(num_files):
            filename = f"stress_test_{i:03d}.bin"
            filepath = self.create_demo_file(filename, size_mb)
            
            if self.upload_file(filepath, replication_factor=2):
                success += 1
            
            if os.path.exists(filepath):
                os.remove(filepath)
        
        elapsed = time.time() - start_time
        
        print("\n" + "="*60)
        print(f"⏱️  Completed in {elapsed:.2f} seconds")
        print(f"✅ Success: {success}/{num_files}")
        print(f"📊 Average: {elapsed/num_files:.2f} seconds per file")
        print("="*60)
    
    def run_interactive_demo(self):
        """Run interactive demo"""
        print("\n" + "="*60)
        print("🚀 DFS INTERACTIVE DEMO")
        print("="*60)
        
        if not self.check_system():
            return
        
        while True:
            print("\n📋 Available Actions:")
            print("1. Generate demo files")
            print("2. Stress test (10 files)")
            print("3. Show statistics")
            print("4. Open Web UI")
            print("5. Exit")
            
            choice = input("\n👉 Choose action (1-5): ").strip()
            
            if choice == '1':
                self.generate_demo_files()
            
            elif choice == '2':
                self.stress_test()
            
            elif choice == '3':
                self.show_stats()
            
            elif choice == '4':
                print(f"\n🌐 Opening: {self.naming_service}")
                print("   (Open this URL in your browser)")
                import webbrowser
                webbrowser.open(self.naming_service)
            
            elif choice == '5':
                print("\n👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice")

if __name__ == '__main__':
    demo = DFSDemo()
    
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'generate':
            if demo.check_system():
                demo.generate_demo_files()
        
        elif command == 'stress':
            num_files = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            if demo.check_system():
                demo.stress_test(num_files)
        
        elif command == 'stats':
            demo.show_stats()
        
        else:
            print("Usage:")
            print("  python demo_script.py generate    # Generate demo files")
            print("  python demo_script.py stress [N]  # Stress test with N files")
            print("  python demo_script.py stats       # Show statistics")
            print("  python demo_script.py             # Interactive mode")
    
    else:
        demo.run_interactive_demo()