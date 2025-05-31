#!/usr/bin/env python3
"""
Demonstration of storing and retrieving OCR content from the database.

This example shows how OCR text content is now stored directly in the database
in addition to being saved as files, enabling powerful search and query capabilities.
"""

import pathlib
import sys
from typing import List, Dict, Any

# Add the src directory to Python path for demo purposes
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from mistral_ocr.client import MistralOCRClient


def demo_database_content_storage():
    """Demonstrate storing and retrieving OCR content from database."""
    
    print("🗄️  Database OCR Content Storage Demo")
    print("=" * 50)
    
    # Initialize client (in mock mode for demo)
    client = MistralOCRClient(api_key="test-api-key")
    
    # Ensure we're in full mock mode
    client.mock_mode = True
    client.submission_manager.mock_mode = True
    client.result_manager.mock_mode = True
    client.job_manager.mock_mode = True
    
    print("✅ Client initialized in mock mode")
    
    # Create a test file (this would normally be a real image/PDF)
    test_dir = pathlib.Path.cwd() / "demo_files"
    test_dir.mkdir(exist_ok=True)
    
    test_file = test_dir / "sample_document.png"
    test_file.write_bytes(b"Sample image content for OCR processing")
    
    print(f"📄 Created test file: {test_file}")
    
    try:
        # Submit document for processing
        print("\n🚀 Submitting document for OCR processing...")
        job_id = client.submit_documents(
            [test_file], 
            document_name="Database Storage Demo"
        )
        print(f"✅ Job submitted with ID: {job_id}")
        
        # Download results (this will store content in database)
        print("\n📥 Downloading results (storing content in database)...")
        client.download_results(job_id)
        print("✅ Results downloaded and stored in database")
        
        # Demonstrate database content retrieval
        print("\n🔍 Retrieving content from database...")
        
        # Get content for specific job
        content = client.get_download_content(job_id)
        if content:
            print(f"📝 Text content: {content['text_content'][:100] if content['text_content'] else 'None'}...")
            print(f"📋 Markdown content: {content['markdown_content'][:100] if content['markdown_content'] else 'None'}...")
            print(f"🖼️  Image data: {'Present' if content['image_data_base64'] else 'None'}")
        else:
            print("❌ No content found for this job")
        
        # Search OCR content
        print("\n🔎 Searching OCR content...")
        search_results = client.search_ocr_content("sample")  # Search for "sample"
        print(f"📊 Found {len(search_results)} results containing 'sample'")
        
        for i, result in enumerate(search_results[:3]):  # Show first 3 results
            print(f"  {i+1}. Job {result['job_id']} - Document: {result['document_name']}")
            if result['text_content']:
                print(f"     Text preview: {result['text_content'][:80]}...")
        
        # Get all content for a document
        print("\n📚 Getting all content for document...")
        doc_content = client.get_all_document_content("Database Storage Demo")
        print(f"📄 Document has {len(doc_content)} downloaded results")
        
        for i, download in enumerate(doc_content):
            print(f"  {i+1}. Order {download['document_order']} - Created: {download['created_at']}")
            print(f"     Files: {download['text_path']}")
            print(f"     Content length: {len(download['text_content']) if download['text_content'] else 0} chars")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
        if test_dir.exists() and not any(test_dir.iterdir()):
            test_dir.rmdir()
        print("\n🧹 Cleanup completed")


def show_benefits():
    """Show the benefits of storing content in database."""
    
    print("\n🎯 Benefits of Database Content Storage")
    print("=" * 40)
    
    benefits = [
        "🔍 **Full-text search**: Query OCR results directly with SQL",
        "📊 **Data analytics**: Analyze OCR results across documents", 
        "🔄 **API integration**: Serve content without file system access",
        "💾 **Backup resilience**: Content preserved even if files are lost",
        "⚡ **Performance**: Faster queries than reading files from disk",
        "🔗 **Relational queries**: Join OCR content with job/document metadata",
        "📱 **Mobile/web apps**: Easy content access for applications",
        "🔐 **Security**: Database-level access controls and encryption"
    ]
    
    for benefit in benefits:
        print(f"  {benefit}")
    
    print("\n💡 **Example Use Cases:**")
    use_cases = [
        "Search invoices for specific vendor names",
        "Find contracts mentioning certain terms", 
        "Analyze document content trends over time",
        "Build content recommendation systems",
        "Create searchable document archives"
    ]
    
    for case in use_cases:
        print(f"  • {case}")


if __name__ == "__main__":
    demo_database_content_storage()
    show_benefits()
    
    print(f"\n✨ Demo completed! The OCR content is now stored in both:")
    print(f"   📁 Files: For easy direct access")
    print(f"   🗄️  Database: For powerful search and queries")