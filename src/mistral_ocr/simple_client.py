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
                -- Extended API fields
                object_type TEXT,
                input_files TEXT,  -- JSON array as text
                metadata TEXT,     -- JSON object as text
                endpoint TEXT,
                model TEXT,
                agent_id TEXT,
                output_file TEXT,
                error_file TEXT,
                errors TEXT,       -- JSON array as text
                total_requests INTEGER,
                completed_requests INTEGER,
                succeeded_requests INTEGER,
                failed_requests INTEGER,
                started_at TEXT,   -- ISO timestamp string
                completed_at TEXT, -- ISO timestamp string
                api_created_at TEXT, -- Original API created_at timestamp
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
            
            CREATE TABLE IF NOT EXISTS error_files (
                id INTEGER PRIMARY KEY,
                job_id TEXT,
                error_file_id TEXT,
                content TEXT,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            );
        """)
        self.connection.commit()
        
        # Add columns to existing tables if they don't exist
        self._migrate_schema()
    
    def _migrate_schema(self) -> None:
        """Add new columns to existing tables if they don't exist."""
        # List of new columns to add to jobs table
        new_columns = [
            ("object_type", "TEXT"),
            ("input_files", "TEXT"),
            ("metadata", "TEXT"),
            ("endpoint", "TEXT"),
            ("model", "TEXT"),
            ("agent_id", "TEXT"),
            ("output_file", "TEXT"),
            ("error_file", "TEXT"),
            ("errors", "TEXT"),
            ("total_requests", "INTEGER"),
            ("completed_requests", "INTEGER"),
            ("succeeded_requests", "INTEGER"),
            ("failed_requests", "INTEGER"),
            ("started_at", "TEXT"),
            ("completed_at", "TEXT"),
            ("api_created_at", "TEXT"),
        ]
        
        # Check which columns exist
        cursor = self.connection.execute("PRAGMA table_info(jobs)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        # Add missing columns
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                try:
                    self.connection.execute(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_type}")
                except sqlite3.Error:
                    # Column might already exist from a previous migration
                    pass
        
        self.connection.commit()
    
    def add_document(self, name: str) -> int:
        """Add a document and return its ID, or return existing ID if document exists."""
        # First try to find existing document
        existing = self.connection.execute(
            "SELECT id FROM documents WHERE name = ?", (name,)
        ).fetchone()
        
        if existing:
            return existing[0]
        
        # Create new document if it doesn't exist
        cursor = self.connection.execute(
            "INSERT INTO documents (name) VALUES (?)", (name,)
        )
        self.connection.commit()
        return cursor.lastrowid or 0
    
    def add_job(self, job_id: str, document_id: int, **api_fields) -> None:
        """Add a job with optional API fields."""
        # Extract API fields with defaults
        object_type = api_fields.get('object', None)
        input_files = json.dumps(api_fields.get('input_files', [])) if api_fields.get('input_files') else None
        metadata = json.dumps(api_fields.get('metadata', {})) if api_fields.get('metadata') else None
        endpoint = api_fields.get('endpoint', None)
        model = api_fields.get('model', None)
        agent_id = api_fields.get('agent_id', None)
        output_file = api_fields.get('output_file', None)
        error_file = api_fields.get('error_file', None)
        errors = json.dumps(api_fields.get('errors', [])) if api_fields.get('errors') else None
        total_requests = api_fields.get('total_requests', None)
        completed_requests = api_fields.get('completed_requests', None)
        succeeded_requests = api_fields.get('succeeded_requests', None)
        failed_requests = api_fields.get('failed_requests', None)
        started_at = api_fields.get('started_at', None)
        completed_at = api_fields.get('completed_at', None)
        api_created_at = str(api_fields.get('created_at', '')) if api_fields.get('created_at') else None
        status = api_fields.get('status', 'pending')
        
        self.connection.execute("""
            INSERT INTO jobs (
                job_id, document_id, status, object_type, input_files, metadata, 
                endpoint, model, agent_id, output_file, error_file, errors,
                total_requests, completed_requests, succeeded_requests, failed_requests,
                started_at, completed_at, api_created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id, document_id, status, object_type, input_files, metadata,
            endpoint, model, agent_id, output_file, error_file, errors,
            total_requests, completed_requests, succeeded_requests, failed_requests,
            started_at, completed_at, api_created_at
        ))
        self.connection.commit()
    
    def update_job_status(self, job_id: str, status: str, **api_fields) -> None:
        """Update job status and API fields."""
        # Build dynamic update query based on provided fields
        update_fields = ["status = ?"]
        values = [status]
        
        # Add API fields if provided (excluding 'status' which is already handled)
        field_mappings = {
            'object': 'object_type',
            'input_files': 'input_files',
            'metadata': 'metadata',
            'endpoint': 'endpoint',
            'model': 'model',
            'agent_id': 'agent_id',
            'output_file': 'output_file',
            'error_file': 'error_file',
            'errors': 'errors',
            'total_requests': 'total_requests',
            'completed_requests': 'completed_requests',
            'succeeded_requests': 'succeeded_requests',
            'failed_requests': 'failed_requests',
            'started_at': 'started_at',
            'completed_at': 'completed_at',
            'created_at': 'api_created_at'
        }
        
        for api_field, db_field in field_mappings.items():
            if api_field in api_fields and api_field != 'status':  # Skip status to avoid conflict
                value = api_fields[api_field]
                if api_field in ['input_files', 'metadata', 'errors'] and value is not None:
                    value = json.dumps(value)
                elif api_field == 'created_at' and value is not None:
                    value = str(value)
                update_fields.append(f"{db_field} = ?")
                values.append(value)
        
        query = f"UPDATE jobs SET {', '.join(update_fields)} WHERE job_id = ?"
        values.append(job_id)
        
        self.connection.execute(query, values)
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
    
    def add_error_file(self, job_id: str, error_file_id: str, content: str) -> None:
        """Add error file content."""
        # Check if already exists
        existing = self.connection.execute(
            "SELECT id FROM error_files WHERE job_id = ? AND error_file_id = ?",
            (job_id, error_file_id)
        ).fetchone()
        
        if not existing:
            self.connection.execute(
                "INSERT INTO error_files (job_id, error_file_id, content) VALUES (?, ?, ?)",
                (job_id, error_file_id, content)
            )
            self.connection.commit()
    
    def get_error_file(self, job_id: str, error_file_id: str) -> Optional[str]:
        """Get error file content."""
        row = self.connection.execute(
            "SELECT content FROM error_files WHERE job_id = ? AND error_file_id = ?",
            (job_id, error_file_id)
        ).fetchone()
        return row[0] if row else None
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get a specific job by ID with document name."""
        row = self.connection.execute(
            """SELECT j.*, COALESCE(d.name, 'Unknown') as document_name 
               FROM jobs j 
               LEFT JOIN documents d ON j.document_id = d.id 
               WHERE j.job_id = ?""", (job_id,)
        ).fetchone()
        return dict(row) if row else None
    
    def list_jobs(self) -> List[Dict]:
        """List all jobs."""
        rows = self.connection.execute(
            """SELECT j.*, COALESCE(d.name, 'Unknown') as document_name 
               FROM jobs j 
               LEFT JOIN documents d ON j.document_id = d.id 
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
        """Check job status and update database with full API response."""
        try:
            # Get status from Mistral API
            batch_job = self.client.batch.jobs.get(job_id=job_id)
            status = batch_job.status
            
            # Extract all API fields (excluding status to avoid parameter conflict)
            api_fields = {
                'object': getattr(batch_job, 'object', None),
                'input_files': getattr(batch_job, 'input_files', []),
                'metadata': getattr(batch_job, 'metadata', {}),
                'endpoint': getattr(batch_job, 'endpoint', None),
                'model': getattr(batch_job, 'model', None),
                'agent_id': getattr(batch_job, 'agent_id', None),
                'output_file': getattr(batch_job, 'output_file', None),
                'error_file': getattr(batch_job, 'error_file', None),
                'errors': self._serialize_errors(getattr(batch_job, 'errors', [])),
                'total_requests': getattr(batch_job, 'total_requests', None),
                'completed_requests': getattr(batch_job, 'completed_requests', None),
                'succeeded_requests': getattr(batch_job, 'succeeded_requests', None),
                'failed_requests': getattr(batch_job, 'failed_requests', None),
                'started_at': getattr(batch_job, 'started_at', None),
                'completed_at': getattr(batch_job, 'completed_at', None),
                'created_at': getattr(batch_job, 'created_at', None)
            }
            
            # Process job data (download error files, etc.)
            self._process_job_data(api_fields, job_id)
            
            # Check if job exists in database
            existing_job = self.db.get_job(job_id)
            if existing_job:
                # Update database with all API fields
                self.db.update_job_status(job_id, status, **api_fields)
            else:
                # Create new job entry if it doesn't exist
                doc_name = "Unknown"
                if api_fields.get('metadata') and isinstance(api_fields['metadata'], dict):
                    doc_name = api_fields['metadata'].get('document_name', 'Unknown')
                
                doc_id = self.db.add_document(doc_name)
                self.db.add_job(job_id, doc_id, **api_fields)
            
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
    
    def list_jobs(self, refresh_from_api: bool = True) -> List[Dict]:
        """List all jobs, optionally refreshing from API."""
        
        if refresh_from_api:
            try:
                # Fetch all jobs from Mistral API
                api_jobs = self.client.batch.jobs.list()
                
                # Update database with API data
                for job in api_jobs.data:
                    # Convert job object to dict for easier access (excluding status to avoid conflict)
                    job_dict = {
                        'id': job.id,
                        'object': getattr(job, 'object', None),
                        'input_files': getattr(job, 'input_files', []),
                        'metadata': getattr(job, 'metadata', {}),
                        'endpoint': getattr(job, 'endpoint', None),
                        'model': getattr(job, 'model', None),
                        'agent_id': getattr(job, 'agent_id', None),
                        'output_file': getattr(job, 'output_file', None),
                        'error_file': getattr(job, 'error_file', None),
                        'errors': self._serialize_errors(getattr(job, 'errors', [])),
                        'total_requests': getattr(job, 'total_requests', None),
                        'completed_requests': getattr(job, 'completed_requests', None),
                        'succeeded_requests': getattr(job, 'succeeded_requests', None),
                        'failed_requests': getattr(job, 'failed_requests', None),
                        'started_at': getattr(job, 'started_at', None),
                        'completed_at': getattr(job, 'completed_at', None),
                        'created_at': getattr(job, 'created_at', None)
                    }
                    
                    # Process job data (download error files, etc.)
                    self._process_job_data(job_dict, job.id)
                    
                    # Check if job exists in database
                    existing_job = self.db.get_job(job.id)
                    if existing_job:
                        # Update existing job with all API fields
                        self.db.update_job_status(job.id, job.status, **job_dict)
                    else:
                        # Create new job entry if it doesn't exist
                        # Try to find or create a document for this job
                        doc_name = "Unknown"
                        if job_dict.get('metadata') and isinstance(job_dict['metadata'], dict):
                            doc_name = job_dict['metadata'].get('document_name', 'Unknown')
                        
                        try:
                            doc_id = self.db.add_document(doc_name)
                            self.db.add_job(job.id, doc_id, **job_dict)
                        except Exception as job_error:
                            # Job might have been created by another process, try to update instead
                            print(f"Warning: Could not create job {job.id}, attempting update: {job_error}")
                            try:
                                self.db.update_job_status(job.id, job.status, **job_dict)
                            except Exception as update_error:
                                print(f"Warning: Could not update job {job.id}: {update_error}")
                        
            except Exception as e:
                print(f"Warning: Could not refresh from API: {e}")
        
        return self.db.list_jobs()
    
    def _serialize_errors(self, errors) -> List[Dict]:
        """Convert error objects to serializable dictionaries."""
        if not errors:
            return []
        
        serialized_errors = []
        for error in errors:
            if hasattr(error, '__dict__'):
                # Convert object attributes to dict
                error_dict = {}
                for attr in ['message', 'count', 'code', 'type']:
                    if hasattr(error, attr):
                        error_dict[attr] = getattr(error, attr)
                serialized_errors.append(error_dict)
            elif isinstance(error, dict):
                # Already a dict, use as-is
                serialized_errors.append(error)
            else:
                # Convert to string as fallback
                serialized_errors.append({'message': str(error), 'count': 1})
        
        return serialized_errors
    
    def _download_error_file(self, error_file_id: str, job_id: str) -> None:
        """Download error file from Mistral API and store in database."""
        if not error_file_id:
            return
        
        try:
            # Check if already downloaded
            existing_content = self.db.get_error_file(job_id, error_file_id)
            if existing_content:
                return  # Already downloaded
            
            # Download from Mistral API
            error_response = self.client.files.download(file_id=error_file_id)
            
            # Extract content from response
            if hasattr(error_response, 'read'):
                # Streaming response - read the content
                error_content = error_response.read()
                if isinstance(error_content, bytes):
                    error_content = error_content.decode('utf-8')
            elif hasattr(error_response, 'content'):
                error_content = error_response.content.decode('utf-8') if isinstance(error_response.content, bytes) else str(error_response.content)
            elif hasattr(error_response, 'text'):
                error_content = error_response.text
            elif isinstance(error_response, bytes):
                error_content = error_response.decode('utf-8')
            else:
                error_content = str(error_response)
            
            # Store in database
            self.db.add_error_file(job_id, error_file_id, error_content)
            print(f"Downloaded error file for job {job_id}: {error_file_id}")
            
        except Exception as e:
            print(f"Warning: Could not download error file {error_file_id}: {e}")
    
    def _process_job_data(self, job_dict: Dict, job_id: str) -> None:
        """Process job data and download error files if present."""
        # Download error file if present
        if job_dict.get('error_file'):
            self._download_error_file(job_dict['error_file'], job_id)
    
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