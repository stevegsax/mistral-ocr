"""Simplified Mistral OCR Client - single file with all core functionality."""

import base64
import json
import os
import pathlib
import sqlite3
import tempfile
from typing import Dict, List, Optional, Union

from mistralai import Mistral


class OCRDatabase:
    """Simple SQLite database for OCR jobs and results."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.expanduser("~/.mistral-ocr/database.db")
        
        self.db_path = pathlib.Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self) -> None:
        """Initialize database schema."""
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY,
                job_id TEXT UNIQUE,
                document_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );
            
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY,
                job_id TEXT,
                file_name TEXT,
                text_content TEXT,
                markdown_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            );
        """)
        self.connection.commit()
    
    def add_document(self, name: str) -> int:
        """Add a document and return its ID."""
        cursor = self.connection.execute(
            "INSERT OR REPLACE INTO documents (name) VALUES (?)", (name,)
        )
        self.connection.commit()
        return cursor.lastrowid or 0
    
    def add_job(self, job_id: str, document_id: int) -> None:
        """Add a job."""
        self.connection.execute(
            "INSERT INTO jobs (job_id, document_id) VALUES (?, ?)",
            (job_id, document_id)
        )
        self.connection.commit()
    
    def update_job_status(self, job_id: str, status: str) -> None:
        """Update job status."""
        self.connection.execute(
            "UPDATE jobs SET status = ? WHERE job_id = ?", (status, job_id)
        )
        self.connection.commit()
    
    def add_result(self, job_id: str, file_name: str, text: str, markdown: str) -> None:
        """Add OCR result."""
        self.connection.execute(
            "INSERT INTO results (job_id, file_name, text_content, markdown_content) "
            "VALUES (?, ?, ?, ?)",
            (job_id, file_name, text, markdown)
        )
        self.connection.commit()
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job details."""
        row = self.connection.execute(
            "SELECT j.*, d.name as document_name FROM jobs j "
            "JOIN documents d ON j.document_id = d.id WHERE j.job_id = ?",
            (job_id,)
        ).fetchone()
        return dict(row) if row else None
    
    def get_results(self, job_id: str) -> List[Dict]:
        """Get results for a job."""
        rows = self.connection.execute(
            "SELECT * FROM results WHERE job_id = ? ORDER BY file_name",
            (job_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    
    def search_content(self, query: str) -> List[Dict]:
        """Search OCR content."""
        rows = self.connection.execute(
            """SELECT r.*, j.job_id, d.name as document_name 
               FROM results r 
               JOIN jobs j ON r.job_id = j.job_id 
               JOIN documents d ON j.document_id = d.id 
               WHERE r.text_content LIKE ? OR r.markdown_content LIKE ?
               ORDER BY r.created_at DESC LIMIT 50""",
            (f"%{query}%", f"%{query}%")
        ).fetchall()
        return [dict(row) for row in rows]
    
    def list_jobs(self) -> List[Dict]:
        """List all jobs."""
        rows = self.connection.execute(
            """SELECT j.*, d.name as document_name 
               FROM jobs j 
               JOIN documents d ON j.document_id = d.id 
               ORDER BY j.created_at DESC""",
        ).fetchall()
        return [dict(row) for row in rows]
    
    def close(self) -> None:
        """Close database connection."""
        self.connection.close()


class SimpleMistralOCRClient:
    """Simplified Mistral OCR Client - single class for all operations."""
    
    def __init__(self, api_key: Optional[str] = None, db_path: Optional[str] = None):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set MISTRAL_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = Mistral(api_key=self.api_key)
        self.db = OCRDatabase(db_path)
        
    def submit(self, files: List[Union[str, pathlib.Path]], document_name: str) -> str:
        """Submit files for OCR processing."""
        print(f"Submitting {len(files)} files for OCR processing...")
        
        # Convert to Path objects
        file_paths = [pathlib.Path(f) for f in files]
        
        # Validate files exist
        for file_path in file_paths:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
        
        # Add document to database
        doc_id = self.db.add_document(document_name)
        
        # Create batch file for Mistral API
        batch_file = self._create_batch_file(file_paths)
        
        try:
            # Upload batch file
            print("Uploading batch file...")
            upload_response = self.client.files.upload(
                file={"file_name": "batch.jsonl", "content": open(batch_file, "rb")},
                purpose="batch"
            )
            
            # Create batch job
            print("Creating batch job...")
            batch_job = self.client.batch.jobs.create(
                input_files=[upload_response.id],
                endpoint="/v1/chat/completions",
                model="mistral-large-latest"
            )
            
            job_id = batch_job.id
            
            # Store in database
            self.db.add_job(job_id, doc_id)
            
            print(f"✅ Job submitted successfully: {job_id}")
            return str(job_id)
            
        finally:
            # Cleanup temp file
            pathlib.Path(batch_file).unlink(missing_ok=True)
    
    def status(self, job_id: str) -> str:
        """Check job status."""
        try:
            # Get status from Mistral API
            batch_job = self.client.batch.jobs.get(job_id=job_id)
            status = batch_job.status
            
            # Update database
            self.db.update_job_status(job_id, status)
            
            return str(status)
        except Exception as e:
            print(f"Error checking status: {e}")
            # Fall back to database status
            job = self.db.get_job(job_id)
            return job["status"] if job else "unknown"
    
    def results(self, job_id: str) -> List[Dict]:
        """Get results for a completed job."""
        # Check if we already have results in database
        existing_results = self.db.get_results(job_id)
        if existing_results:
            return existing_results
        
        # Get fresh results from API
        try:
            batch_job = self.client.batch.jobs.get(job_id=job_id)
            
            if batch_job.status != "completed":
                print(f"Job not completed yet. Status: {batch_job.status}")
                return []
            
            if not batch_job.output_file:
                print("No output file available")
                return []
            
            # Download results
            print("Downloading results...")
            output_response = self.client.files.download(file_id=batch_job.output_file)
            output_content = output_response.read().decode("utf-8")
            
            # Parse results and store in database
            results = []
            for line in output_content.strip().split("\n"):
                if not line:
                    continue
                    
                data = json.loads(line)
                custom_id = data.get("custom_id", "unknown")
                
                # Extract text from response
                response_body = data.get("response", {}).get("body", {})
                choices = response_body.get("choices", [])
                
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    
                    # Simple parsing - assume content is OCR text
                    text_content = content
                    markdown_content = f"# OCR Result for {custom_id}\n\n{content}"
                    
                    # Store in database
                    self.db.add_result(job_id, custom_id, text_content, markdown_content)
                    
                    results.append({
                        "file_name": custom_id,
                        "text_content": text_content,
                        "markdown_content": markdown_content
                    })
            
            print(f"✅ Downloaded {len(results)} results")
            return results
            
        except Exception as e:
            print(f"Error downloading results: {e}")
            return []
    
    def search(self, query: str) -> List[Dict]:
        """Search OCR content."""
        return self.db.search_content(query)
    
    def list_jobs(self) -> List[Dict]:
        """List all jobs."""
        return self.db.list_jobs()
    
    def _create_batch_file(self, file_paths: List[pathlib.Path]) -> str:
        """Create JSONL batch file for Mistral API."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
        
        for file_path in file_paths:
            # Read and encode file
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
            # Create data URL for image
            file_ext = file_path.suffix.lower()
            if file_ext in ['.png', '.jpg', '.jpeg']:
                mime_type = f"image/{'jpeg' if file_ext in ['.jpg', '.jpeg'] else 'png'}"
                data_url = f"data:{mime_type};base64,{base64.b64encode(file_content).decode()}"
            else:
                # For PDFs or other files, also encode as base64
                data_url = f"data:application/pdf;base64,{base64.b64encode(file_content).decode()}"
            
            # Create batch entry
            entry = {
                "custom_id": file_path.name,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "mistral-large-latest",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Extract all text from this image using OCR. "
                                        "Return only the extracted text without "
                                        "any additional commentary."
                                    )
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": data_url}
                                }
                            ]
                        }
                    ]
                }
            }
            
            temp_file.write(json.dumps(entry) + "\n")
        
        temp_file.close()
        return temp_file.name
    
    def __del__(self) -> None:
        """Cleanup database connection."""
        if hasattr(self, 'db'):
            self.db.close()


# Alias for backward compatibility
MistralOCRClient = SimpleMistralOCRClient