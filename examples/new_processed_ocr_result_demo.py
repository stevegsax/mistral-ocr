#!/usr/bin/env python3
"""
Demonstration of the new ProcessedOCRResult structure.

This script shows how the refactored ProcessedOCRResult supports:
1. Multiple file types (text, markdown, images)
2. Base64 encoded images
3. Backward compatibility with existing text/markdown fields
4. Helper methods for accessing different content types
"""

import base64
from pathlib import Path

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mistral_ocr.data_types import (
    ProcessedOCRResult,
    ProcessedOCRFile,
    ProcessedOCRFileType,
)


def create_sample_image_base64() -> str:
    """Create a simple base64-encoded image for demonstration."""
    # This is a minimal 1x1 PNG image in base64
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAGAWWWIIwAAAABJRU5ErkJggg=="


def demonstrate_new_structure():
    """Demonstrate the new ProcessedOCRResult structure."""
    
    print("🔍 ProcessedOCRResult Refactoring Demonstration")
    print("=" * 50)
    
    # Create sample content
    text_content = "This is the extracted text from the document."
    markdown_content = "# Document Title\n\nThis is the **extracted text** from the document."
    image_base64 = create_sample_image_base64()
    
    # Create individual file objects
    text_file = ProcessedOCRFile(
        file_type=ProcessedOCRFileType.TEXT,
        content=text_content,
        file_extension=".txt",
        metadata={"extraction_confidence": 0.95}
    )
    
    markdown_file = ProcessedOCRFile(
        file_type=ProcessedOCRFileType.MARKDOWN,
        content=markdown_content,
        file_extension=".md",
        metadata={"contains_formatting": True}
    )
    
    image_file = ProcessedOCRFile(
        file_type=ProcessedOCRFileType.IMAGE,
        content=image_base64,
        file_extension=".png",
        metadata={"image_type": "diagram", "width": 1, "height": 1}
    )
    
    # Create the new ProcessedOCRResult
    result = ProcessedOCRResult(
        file_name="sample_document",
        job_id="job_12345",
        custom_id="sample_001",
        files=[text_file, markdown_file, image_file],
        # Backward compatibility fields
        text=text_content,
        markdown=markdown_content,
        metadata={"processing_time": 2.5, "page_count": 1}
    )
    
    print("✅ Created ProcessedOCRResult with multiple file types:")
    print(f"   - File name: {result.file_name}")
    print(f"   - Job ID: {result.job_id}")
    print(f"   - Number of files: {len(result.files)}")
    print()
    
    # Demonstrate file type access
    print("📄 File Types Breakdown:")
    for i, file_obj in enumerate(result.files):
        print(f"   {i+1}. Type: {file_obj.file_type.value}")
        print(f"      Extension: {file_obj.file_extension}")
        print(f"      Content length: {len(file_obj.content)} characters")
        if file_obj.metadata:
            print(f"      Metadata: {file_obj.metadata}")
        print()
    
    # Demonstrate helper methods
    print("🔧 Helper Method Demonstrations:")
    
    # Get text content
    text = result.get_text_content()
    print(f"   📝 Text content: {text[:50]}...")
    
    # Get markdown content
    markdown = result.get_markdown_content()
    print(f"   📋 Markdown content: {markdown[:50]}...")
    
    # Get image files
    images = result.get_image_files()
    print(f"   🖼️  Image files: {len(images)} found")
    if images:
        print(f"      First image base64 length: {len(images[0].content)} characters")
    
    # Get files by type
    text_files = result.get_files_by_type(ProcessedOCRFileType.TEXT)
    markdown_files = result.get_files_by_type(ProcessedOCRFileType.MARKDOWN)
    image_files = result.get_files_by_type(ProcessedOCRFileType.IMAGE)
    
    print(f"   📊 Files by type:")
    print(f"      Text files: {len(text_files)}")
    print(f"      Markdown files: {len(markdown_files)}")
    print(f"      Image files: {len(image_files)}")
    print()
    
    # Demonstrate backward compatibility
    print("🔄 Backward Compatibility:")
    print(f"   📝 Direct text access: {result.text[:30]}...")
    print(f"   📋 Direct markdown access: {result.markdown[:30]}...")
    print()
    
    # Demonstrate image decoding (simulated)
    print("🖼️  Image Processing Example:")
    for image_file in result.get_image_files():
        try:
            # Decode base64 to bytes (would be saved to file in real usage)
            image_bytes = base64.b64decode(image_file.content)
            print(f"   ✅ Successfully decoded {image_file.file_extension} image")
            print(f"      Size: {len(image_bytes)} bytes")
            print(f"      Metadata: {image_file.metadata}")
        except Exception as e:
            print(f"   ❌ Failed to decode image: {e}")
    
    print()
    print("🎉 Refactoring Complete!")
    print("   The new structure supports:")
    print("   ✅ Multiple file types in a single result")
    print("   ✅ Base64 encoded images")
    print("   ✅ Backward compatibility with existing code")
    print("   ✅ Rich metadata for each file")
    print("   ✅ Helper methods for easy content access")


if __name__ == "__main__":
    demonstrate_new_structure()