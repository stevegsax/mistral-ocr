import argparse
import pathlib
import sys
from typing import TYPE_CHECKING, Optional

from mistral_ocr._version import __version__
from mistral_ocr.constants import (
    TEXT_PREVIEW_LENGTH, TABLE_SEPARATOR_LENGTH, JOB_ID_COLUMN_WIDTH,
    STATUS_COLUMN_WIDTH, SUBMITTED_COLUMN_WIDTH, API_REFRESH_COLUMN_WIDTH
)
from mistral_ocr.exceptions import MistralOCRError

if TYPE_CHECKING:
    from mistral_ocr.client import MistralOCRClient
    from mistral_ocr.settings import Settings


# Helper functions
def format_timestamp(timestamp: Optional[str]) -> str:
    """Format timestamp for display, showing 'Never' if None.
    
    Args:
        timestamp: ISO timestamp string or None
        
    Returns:
        Formatted timestamp or 'Never'
    """
    if not timestamp:
        return "Never"
    
    # Extract just the date and time part (remove microseconds and timezone)
    try:
        # Handle formats like '2024-01-01 12:34:56' or '2024-01-01T12:34:56.123Z'
        if 'T' in timestamp:
            date_time = timestamp.split('T')
            date_part = date_time[0]
            time_part = date_time[1].split('.')[0]  # Remove microseconds
            return f"{date_part} {time_part}"
        else:
            # Already in 'YYYY-MM-DD HH:MM:SS' format
            return timestamp.split('.')[0]  # Remove microseconds if present
    except (IndexError, ValueError):
        return timestamp  # Return as-is if parsing fails


# Command handler functions
def handle_submit_command(
    args: argparse.Namespace, 
    client: 'MistralOCRClient', 
    settings: 'Settings'
) -> None:
    """Handle document submission command."""
    file_path = pathlib.Path(args.submit)
    model = args.model or settings.get_default_model()

    job_id = client.submit_documents(
        [file_path],
        recursive=args.recursive,
        document_name=args.document_name,
        document_uuid=args.document_uuid,
        model=model,
    )

    if isinstance(job_id, list):
        print(f"Submitted {len(job_id)} batch jobs:")
        for jid in job_id:
            print(f"  {jid}")
    else:
        print(f"Submitted job: {job_id}")


def handle_job_status_command(
    args: argparse.Namespace, 
    client: 'MistralOCRClient'
) -> None:
    """Handle job status check command."""
    status = client.check_job_status(args.check_job)
    print(f"Job {args.check_job} status: {status}")


def handle_document_query_command(
    args: argparse.Namespace, 
    client: 'MistralOCRClient'
) -> None:
    """Handle document status query command."""
    statuses = client.query_document_status(args.query_document)
    print(f"Document '{args.query_document}' job statuses:")
    for i, status in enumerate(statuses, 1):
        print(f"  Job {i}: {status}")


def handle_cancel_job_command(
    args: argparse.Namespace, 
    client: 'MistralOCRClient'
) -> None:
    """Handle job cancellation command."""
    success = client.cancel_job(args.cancel_job)
    if success:
        print(f"Successfully cancelled job {args.cancel_job}")
    else:
        print(f"Failed to cancel job {args.cancel_job}")


def handle_list_jobs_command(
    args: argparse.Namespace, 
    client: 'MistralOCRClient'
) -> None:
    """Handle jobs listing command."""
    jobs = client.list_all_jobs()
    if not jobs:
        print("No jobs found")
    else:
        # Format column headers
        header = (
            f"{'Job ID':<{JOB_ID_COLUMN_WIDTH}} "
            f"{'Status':<{STATUS_COLUMN_WIDTH}} "
            f"{'Submitted':<{SUBMITTED_COLUMN_WIDTH}} "
            f"{'Last API Refresh':<{API_REFRESH_COLUMN_WIDTH}}"
        )
        print(header)
        print("-" * TABLE_SEPARATOR_LENGTH)
        
        for job in jobs:
            api_refresh = format_timestamp(job.get('last_api_refresh'))
            submitted = format_timestamp(job.get('submitted'))
            
            row = (
                f"{job['id']:<{JOB_ID_COLUMN_WIDTH}} "
                f"{job['status']:<{STATUS_COLUMN_WIDTH}} "
                f"{submitted:<{SUBMITTED_COLUMN_WIDTH}} "
                f"{api_refresh:<{API_REFRESH_COLUMN_WIDTH}}"
            )
            print(row)


def handle_job_details_command(
    args: argparse.Namespace, 
    client: 'MistralOCRClient'
) -> None:
    """Handle detailed job status command."""
    try:
        job_details = client.get_job_details(args.job_status)
        print(f"Job ID: {job_details['id']}")
        print(f"Status: {job_details['status']}")
        print(f"Document Name: {job_details.get('document_name', 'N/A')}")
        print(f"File Count: {job_details.get('file_count', 'N/A')}")
        print(f"Submitted: {job_details.get('submitted', 'N/A')}")
        if job_details.get("completed"):
            print(f"Completed: {job_details['completed']}")
        if job_details.get("last_api_refresh"):
            print(f"Last API Refresh: {job_details['last_api_refresh']}")
        if job_details.get("error"):
            print(f"Error: {job_details['error']}")
            
        # Show API response details if available (for debugging)
        if job_details.get("api_response_json") and args.job_status:
            import json
            try:
                api_data = json.loads(job_details["api_response_json"])
                print("\nAPI Response Details:")
                print(f"  Refresh Time: {api_data.get('refresh_timestamp', 'N/A')}")
                if api_data.get('created_at'):
                    print(f"  Created: {api_data['created_at']}")
                if api_data.get('completed_at'):
                    print(f"  Completed: {api_data['completed_at']}")
                if api_data.get('output_file'):
                    print(f"  Output File: {api_data['output_file']}")
                if api_data.get('errors'):
                    print(f"  Errors: {api_data['errors']}")
            except json.JSONDecodeError:
                pass  # Skip if JSON is invalid
                
    except MistralOCRError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_get_results_command(
    args: argparse.Namespace, 
    client: 'MistralOCRClient'
) -> None:
    """Handle results retrieval command."""
    results = client.get_results(args.get_results)
    print(f"Results for job {args.get_results}: {len(results)} items")
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ({result.file_name}) ---")
        print(result.text[:TEXT_PREVIEW_LENGTH] + "..." if len(result.text) > TEXT_PREVIEW_LENGTH else result.text)


def handle_download_results_command(
    args: argparse.Namespace, 
    client: 'MistralOCRClient'
) -> None:
    """Handle results download command."""
    destination = None
    if args.download_to:
        destination = pathlib.Path(args.download_to)

    client.download_results(args.download_results, destination)
    print(f"Downloaded results for job {args.download_results}")


def handle_download_document_command(
    args: argparse.Namespace, 
    client: 'MistralOCRClient'
) -> None:
    """Handle document download command."""
    destination = None
    if args.download_to:
        destination = pathlib.Path(args.download_to)

    client.download_document_results(args.download_document, destination)
    print(f"Downloaded all results for document {args.download_document}")


def main() -> None:
    """Main entry point for the Mistral OCR command-line interface.
    
    Parses command-line arguments and routes to appropriate command handlers for:
    - Document submission and batch processing
    - Job status checking and management
    - Result retrieval and downloading
    - Document querying and listing
    
    The CLI supports both individual file processing and batch operations,
    with automatic file validation, job tracking, and result management.
    
    Environment Variables:
        MISTRAL_API_KEY: Required API key for Mistral service authentication
        XDG_DATA_HOME: Optional data directory override
        XDG_STATE_HOME: Optional state directory override
        
    Raises:
        SystemExit: On error conditions or missing configuration
    """
    parser = argparse.ArgumentParser(
        prog="mistral-ocr", description="Submit OCR batches to the Mistral API"
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("--submit", type=str, help="Submit a file or directory for OCR processing")
    parser.add_argument("--recursive", action="store_true", help="Process directories recursively")
    parser.add_argument("--document-name", type=str, help="Associate files with a document name")
    parser.add_argument("--document-uuid", type=str, help="Associate files with a document UUID")
    parser.add_argument("--model", type=str, help="Specify the OCR model to use")

    parser.add_argument("--check-job", type=str, help="Check the status of a job by ID")
    parser.add_argument("--query-document", type=str, help="Query job statuses by document name")
    parser.add_argument("--cancel-job", type=str, help="Cancel a job by ID")

    parser.add_argument("--list-jobs", action="store_true", help="List all jobs with their status")
    parser.add_argument("--job-status", type=str, help="Show detailed status for a specific job")

    parser.add_argument(
        "--get-results", type=str, help="Retrieve results for a completed job by ID"
    )
    parser.add_argument(
        "--download-results", type=str, help="Download results for a completed job by ID"
    )
    parser.add_argument(
        "--download-document", type=str, help="Download all results for a document by name or UUID"
    )
    parser.add_argument("--download-to", type=str, help="Specify download destination directory")

    args = parser.parse_args()

    # Import here to avoid circular imports
    from mistral_ocr.client import MistralOCRClient
    from mistral_ocr.settings import get_settings

    # Initialize settings
    settings = get_settings()

    # Get API key
    api_key = settings.get_api_key_optional()
    if not api_key:
        print("Error: No API key found. Set MISTRAL_API_KEY environment variable or use config.")
        sys.exit(1)

    try:
        client = MistralOCRClient(api_key=api_key, settings=settings)
    except Exception as e:
        print(f"Error initializing client: {e}")
        sys.exit(1)

    try:
        # Route to appropriate command handler
        if args.submit:
            handle_submit_command(args, client, settings)
        elif args.check_job:
            handle_job_status_command(args, client)
        elif args.query_document:
            handle_document_query_command(args, client)
        elif args.cancel_job:
            handle_cancel_job_command(args, client)
        elif args.list_jobs:
            handle_list_jobs_command(args, client)
        elif args.job_status:
            handle_job_details_command(args, client)
        elif args.get_results:
            handle_get_results_command(args, client)
        elif args.download_results:
            handle_download_results_command(args, client)
        elif args.download_document:
            handle_download_document_command(args, client)
        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
