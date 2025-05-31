#!/usr/bin/env python3
"""Ultra-simple CLI for Mistral OCR."""

import argparse
import pathlib
import sys
from typing import Any

from .simple_client import SimpleMistralOCRClient


def submit_command(args: Any) -> int:
    """Submit files for OCR processing."""
    client = SimpleMistralOCRClient()
    
    # Collect all files
    files = []
    for file_arg in args.files:
        path = pathlib.Path(file_arg)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            # Find image/PDF files in directory
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.pdf']:
                files.extend(path.glob(ext))
                if args.recursive:
                    files.extend(path.rglob(ext))
    
    if not files:
        print("No files found to process")
        return 1
    
    try:
        job_id = client.submit(list(files), args.name or "OCR Job")
        print(f"Job ID: {job_id}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def status_command(args: Any) -> int:
    """Check job status with comprehensive details."""
    client = SimpleMistralOCRClient()
    
    try:
        # Update status from API and get comprehensive job info
        status = client.status(args.job_id)
        job = client.db.get_job(args.job_id)
        
        if not job:
            print(f"Job {args.job_id} not found")
            return 1
        
        # Status emoji
        status_emoji = {
            'SUCCESS': '✅',
            'FAILED': '❌', 
            'RUNNING': '🔄',
            'PENDING': '⏳',
            'CANCELLED': '🚫'
        }.get(job.get('status', ''), '❓')
        
        print(f"{status_emoji} Job Status: {job['status']}")
        print(f"📋 Job ID: {job['job_id']}")
        print(f"📄 Document: {job['document_name']}")
        
        # Progress information
        if job.get('total_requests'):
            completed = job.get('completed_requests', 0)
            succeeded = job.get('succeeded_requests', 0)
            failed = job.get('failed_requests', 0)
            total = job['total_requests']
            
            progress_percent = (completed / total * 100) if total > 0 else 0
            print(f"📊 Progress: {completed}/{total} ({progress_percent:.1f}%)")
            print(f"   ✅ Succeeded: {succeeded}")
            print(f"   ❌ Failed: {failed}")
        
        # Model and endpoint information
        if job.get('model'):
            print(f"🤖 Model: {job['model']}")
        if job.get('endpoint'):
            print(f"🔗 Endpoint: {job['endpoint']}")
        if job.get('object_type'):
            print(f"📦 Object Type: {job['object_type']}")
        
        # Timing information
        if job.get('api_created_at'):
            print(f"⏰ Created: {job['api_created_at']}")
        if job.get('started_at'):
            print(f"🚀 Started: {job['started_at']}")
        if job.get('completed_at'):
            print(f"🏁 Completed: {job['completed_at']}")
        
        # File information
        if job.get('input_files'):
            try:
                import json
                input_files = json.loads(job['input_files']) if isinstance(job['input_files'], str) else job['input_files']
                if input_files:
                    print(f"📁 Input Files: {len(input_files)} file(s)")
                    if len(input_files) <= 3:
                        for file_id in input_files:
                            print(f"   • {file_id}")
                    else:
                        for file_id in input_files[:3]:
                            print(f"   • {file_id}")
                        print(f"   ... and {len(input_files) - 3} more")
            except:
                pass
        
        # Output files
        if job.get('output_file'):
            print(f"📤 Output File: {job['output_file']}")
        if job.get('error_file'):
            print(f"📋 Error File: {job['error_file']}")
            
            # Show error file content if available
            error_content = client.db.get_error_file(job['job_id'], job['error_file'])
            if error_content:
                print(f"📄 Error File Content:")
                # Truncate very long error content
                if len(error_content) > 1000:
                    print(f"   {error_content[:1000]}...")
                    print(f"   (truncated - showing first 1000 characters)")
                else:
                    # Indent each line for better formatting
                    for line in error_content.strip().split('\n'):
                        print(f"   {line}")
        
        # Error information
        if job.get('errors'):
            try:
                import json
                errors = json.loads(job['errors']) if isinstance(job['errors'], str) else job['errors']
                if errors:
                    print(f"⚠️ Errors: {len(errors)} error(s)")
                    for error in errors:
                        if isinstance(error, dict) and 'message' in error:
                            count = error.get('count', 1)
                            print(f"   • {error['message']} (x{count})")
            except:
                pass
        
        # Metadata
        if job.get('metadata'):
            try:
                import json
                metadata = json.loads(job['metadata']) if isinstance(job['metadata'], str) else job['metadata']
                if metadata and metadata != {}:
                    print(f"🏷️ Metadata:")
                    for key, value in metadata.items():
                        print(f"   • {key}: {value}")
            except:
                pass
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def results_command(args: Any) -> int:
    """Get job results."""
    client = SimpleMistralOCRClient()
    
    try:
        results = client.results(args.job_id)
        
        if not results:
            print("No results available yet")
            return 1
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n--- Result {i}: {result['file_name']} ---")
            if args.format == 'text':
                print(result['text_content'])
            elif args.format == 'markdown':
                print(result['markdown_content'])
            else:
                print(f"Text length: {len(result['text_content'])} characters")
                print(f"Preview: {result['text_content'][:200]}...")
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def search_command(args: Any) -> int:
    """Search OCR content."""
    client = SimpleMistralOCRClient()
    
    try:
        results = client.search(args.query)
        
        if not results:
            print("No results found")
            return 0
        
        print(f"Found {len(results)} matching results:")
        for result in results:
            print(f"\n📄 {result['file_name']} (Job: {result['job_id']})")
            print(f"Document: {result['document_name']}")
            
            # Show context around the match
            text = result['text_content'] or ""
            query_lower = args.query.lower()
            text_lower = text.lower()
            
            if query_lower in text_lower:
                idx = text_lower.find(query_lower)
                start = max(0, idx - 50)
                end = min(len(text), idx + len(args.query) + 50)
                context = text[start:end]
                print(f"Context: ...{context}...")
            
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def list_command(args: Any) -> int:
    """List all jobs with rich information."""
    client = SimpleMistralOCRClient()
    
    try:
        jobs = client.list_jobs()
        
        if not jobs:
            print("No jobs found")
            return 0
        
        print(f"Found {len(jobs)} jobs:\n")
        
        for job in jobs:
            # Basic info
            status_emoji = {
                'SUCCESS': '✅',
                'FAILED': '❌', 
                'RUNNING': '🔄',
                'PENDING': '⏳',
                'CANCELLED': '🚫'
            }.get(job.get('status', ''), '❓')
            
            print(f"{status_emoji} {job['job_id']} - {job['status']}")
            print(f"   📄 Document: {job['document_name']}")
            
            # Progress information
            if job.get('total_requests'):
                completed = job.get('completed_requests', 0)
                succeeded = job.get('succeeded_requests', 0)
                failed = job.get('failed_requests', 0)
                total = job['total_requests']
                
                progress_percent = (completed / total * 100) if total > 0 else 0
                print(f"   📊 Progress: {completed}/{total} ({progress_percent:.1f}%) | ✅ {succeeded} | ❌ {failed}")
            
            # Model and endpoint
            if job.get('model'):
                print(f"   🤖 Model: {job['model']}")
            if job.get('endpoint'):
                print(f"   🔗 Endpoint: {job['endpoint']}")
            
            # Timing information
            if job.get('api_created_at'):
                print(f"   ⏰ Created: {job['api_created_at']}")
            if job.get('started_at'):
                print(f"   🚀 Started: {job['started_at']}")
            if job.get('completed_at'):
                print(f"   🏁 Completed: {job['completed_at']}")
            
            # Error information
            if job.get('errors'):
                try:
                    import json
                    errors = json.loads(job['errors']) if isinstance(job['errors'], str) else job['errors']
                    if errors:
                        print(f"   ⚠️ Errors: {len(errors)} error(s)")
                        for error in errors[:2]:  # Show first 2 errors
                            if isinstance(error, dict) and 'message' in error:
                                count = error.get('count', 1)
                                print(f"      • {error['message']} (x{count})")
                except:
                    pass
            
            # Error file indicator
            if job.get('error_file'):
                error_content = client.db.get_error_file(job['job_id'], job['error_file'])
                if error_content:
                    print(f"   📋 Error file downloaded ({len(error_content)} chars)")
                else:
                    print(f"   📋 Error file: {job['error_file']} (not downloaded)")
            
            print()  # Empty line between jobs
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Simple Mistral OCR CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mistral-ocr submit document.pdf --name "Invoice 2024"
  mistral-ocr submit *.jpg --name "Receipt Batch"  
  mistral-ocr submit /path/to/images/ --recursive --name "All Documents"
  mistral-ocr status job_abc123
  mistral-ocr results job_abc123 --format text
  mistral-ocr search "invoice total"
  mistral-ocr list
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Submit command
    submit_parser = subparsers.add_parser('submit', help='Submit files for OCR')
    submit_parser.add_argument('files', nargs='+', help='Files or directories to process')
    submit_parser.add_argument('--name', help='Document name')
    submit_parser.add_argument(
        '--recursive', '-r', action='store_true', help='Process directories recursively'
    )
    submit_parser.set_defaults(func=submit_command)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check job status')
    status_parser.add_argument('job_id', help='Job ID to check')
    status_parser.set_defaults(func=status_command)
    
    # Results command
    results_parser = subparsers.add_parser('results', help='Get job results')
    results_parser.add_argument('job_id', help='Job ID to get results for')
    results_parser.add_argument('--format', choices=['text', 'markdown', 'summary'], 
                               default='summary', help='Output format')
    results_parser.set_defaults(func=results_command)
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search OCR content')
    search_parser.add_argument('query', help='Text to search for')
    search_parser.set_defaults(func=search_command)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all jobs')
    list_parser.set_defaults(func=list_command)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())