import argparse
import pathlib
import sys

from mistral_ocr._version import __version__
from mistral_ocr.exceptions import MistralOCRError


# Command handler functions
def handle_submit_command(args, client, config):
    """Handle document submission command."""
    file_path = pathlib.Path(args.submit)
    model = args.model or config.get_default_model()

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


def handle_job_status_command(args, client):
    """Handle job status check command."""
    status = client.check_job_status(args.check_job)
    print(f"Job {args.check_job} status: {status}")


def handle_document_query_command(args, client):
    """Handle document status query command."""
    statuses = client.query_document_status(args.query_document)
    print(f"Document '{args.query_document}' job statuses:")
    for i, status in enumerate(statuses, 1):
        print(f"  Job {i}: {status}")


def handle_cancel_job_command(args, client):
    """Handle job cancellation command."""
    success = client.cancel_job(args.cancel_job)
    if success:
        print(f"Successfully cancelled job {args.cancel_job}")
    else:
        print(f"Failed to cancel job {args.cancel_job}")


def handle_list_jobs_command(args, client):
    """Handle jobs listing command."""
    jobs = client.list_all_jobs()
    if not jobs:
        print("No jobs found")
    else:
        print(f"{'Job ID':<36} {'Status':<12} {'Submitted':<20}")
        print("-" * 70)
        for job in jobs:
            print(f"{job['id']:<36} {job['status']:<12} {job['submitted']:<20}")


def handle_job_details_command(args, client):
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


def handle_get_results_command(args, client):
    """Handle results retrieval command."""
    results = client.get_results(args.get_results)
    print(f"Results for job {args.get_results}: {len(results)} items")
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ({result.file_name}) ---")
        print(result.text[:200] + "..." if len(result.text) > 200 else result.text)


def handle_download_results_command(args, client):
    """Handle results download command."""
    destination = None
    if args.download_to:
        destination = pathlib.Path(args.download_to)

    client.download_results(args.download_results, destination)
    print(f"Downloaded results for job {args.download_results}")


def handle_download_document_command(args, client):
    """Handle document download command."""
    destination = None
    if args.download_to:
        destination = pathlib.Path(args.download_to)

    client.download_document_results(args.download_document, destination)
    print(f"Downloaded all results for document {args.download_document}")


def main() -> None:
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
    from mistral_ocr.config import ConfigurationManager

    # Initialize configuration
    config = ConfigurationManager()

    # Get API key
    api_key = config.get_api_key()
    if not api_key:
        print("Error: No API key found. Set MISTRAL_API_KEY environment variable or use config.")
        sys.exit(1)

    try:
        client = MistralOCRClient(api_key=api_key)
    except Exception as e:
        print(f"Error initializing client: {e}")
        sys.exit(1)

    try:
        # Route to appropriate command handler
        if args.submit:
            handle_submit_command(args, client, config)
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
