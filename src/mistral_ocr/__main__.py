import argparse
import pathlib
import sys
import time
from typing import TYPE_CHECKING, Optional

from mistral_ocr._version import __version__
from mistral_ocr.audit import AuditEventType, get_audit_logger
from mistral_ocr.constants import (
    API_REFRESH_COLUMN_WIDTH,
    JOB_ID_COLUMN_WIDTH,
    STATUS_COLUMN_WIDTH,
    SUBMITTED_COLUMN_WIDTH,
    TABLE_SEPARATOR_LENGTH,
    TEXT_PREVIEW_LENGTH,
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
        if "T" in timestamp:
            date_time = timestamp.split("T")
            date_part = date_time[0]
            time_part = date_time[1].split(".")[0]  # Remove microseconds
            return f"{date_part} {time_part}"
        else:
            # Already in 'YYYY-MM-DD HH:MM:SS' format
            return timestamp.split(".")[0]  # Remove microseconds if present
    except (IndexError, ValueError):
        return timestamp  # Return as-is if parsing fails


# Command handler functions
def handle_submit_command(
    args: argparse.Namespace, client: "MistralOCRClient", settings: "Settings"
) -> None:
    """Handle document submission command."""
    file_path = pathlib.Path(args.path)
    model = args.model or settings.get_default_model()

    job_id = client.submit_documents(
        [file_path],
        recursive=args.recursive,
        document_name=args.name,
        document_uuid=args.uuid,
        model=model,
    )

    if isinstance(job_id, list):
        print(f"Submitted {len(job_id)} batch jobs:")
        for jid in job_id:
            print(f"  {jid}")
    else:
        print(f"Submitted job: {job_id}")


def handle_job_status_command(args: argparse.Namespace, client: "MistralOCRClient") -> None:
    """Handle job status check command."""
    status = client.check_job_status(args.job_id)
    print(f"Job {args.job_id} status: {status}")


def handle_document_query_command(args: argparse.Namespace, client: "MistralOCRClient") -> None:
    """Handle document status query command."""
    statuses = client.query_document_status(args.name_or_uuid)
    print(f"Document '{args.name_or_uuid}' job statuses:")
    for i, status in enumerate(statuses, 1):
        print(f"  Job {i}: {status}")


def handle_cancel_job_command(args: argparse.Namespace, client: "MistralOCRClient") -> None:
    """Handle job cancellation command."""
    success = client.cancel_job(args.job_id)
    if success:
        print(f"Successfully cancelled job {args.job_id}")
    else:
        print(f"Failed to cancel job {args.job_id}")


def handle_list_jobs_command(args: argparse.Namespace, client: "MistralOCRClient") -> None:
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
            api_refresh = format_timestamp(job.last_api_refresh)
            submitted = format_timestamp(job.submitted)

            row = (
                f"{job.id:<{JOB_ID_COLUMN_WIDTH}} "
                f"{job.status:<{STATUS_COLUMN_WIDTH}} "
                f"{submitted:<{SUBMITTED_COLUMN_WIDTH}} "
                f"{api_refresh:<{API_REFRESH_COLUMN_WIDTH}}"
            )
            print(row)


def handle_job_details_command(args: argparse.Namespace, client: "MistralOCRClient") -> None:
    """Handle detailed job status command."""
    try:
        job_details = client.get_job_details(args.job_id)
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
        if job_details.get("api_response_json") and args.job_id:
            import json

            try:
                api_data = json.loads(job_details["api_response_json"])
                print("\nAPI Response Details:")
                print(f"  Refresh Time: {api_data.get('refresh_timestamp', 'N/A')}")
                if api_data.get("created_at"):
                    print(f"  Created: {api_data['created_at']}")
                if api_data.get("completed_at"):
                    print(f"  Completed: {api_data['completed_at']}")
                if api_data.get("output_file"):
                    print(f"  Output File: {api_data['output_file']}")
                if api_data.get("errors"):
                    print(f"  Errors: {api_data['errors']}")
            except json.JSONDecodeError:
                pass  # Skip if JSON is invalid

    except MistralOCRError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_get_results_command(args: argparse.Namespace, client: "MistralOCRClient") -> None:
    """Handle results retrieval command."""
    results = client.get_results(args.job_id)
    print(f"Results for job {args.job_id}: {len(results)} items")
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ({result.file_name}) ---")
        print(
            result.text[:TEXT_PREVIEW_LENGTH] + "..."
            if len(result.text) > TEXT_PREVIEW_LENGTH
            else result.text
        )


def handle_download_results_command(args: argparse.Namespace, client: "MistralOCRClient") -> None:
    """Handle results download command."""
    destination = None
    if args.output:
        destination = pathlib.Path(args.output)

    client.download_results(args.job_id, destination)
    print(f"Downloaded results for job {args.job_id}")


def handle_download_document_command(args: argparse.Namespace, client: "MistralOCRClient") -> None:
    """Handle document download command."""
    destination = None
    if args.output:
        destination = pathlib.Path(args.output)

    client.download_document_results(args.name_or_uuid, destination)
    print(f"Downloaded all results for document {args.name_or_uuid}")


def handle_config_command(args: argparse.Namespace, settings: "Settings") -> None:
    """Handle configuration management commands."""
    from mistral_ocr.config import ConfigurationManager

    config = ConfigurationManager()

    if args.action == "show":
        print("Current Configuration:")
        print("=====================")

        # Show API key status (don't reveal the actual key)
        api_key = config.get_api_key()
        if api_key:
            if "api_key" in config._config:
                print("API Key: Set in config file (***hidden***)")
            else:
                print("API Key: Set via environment variable")
        else:
            print("API Key: Not set")

        # Show other configuration values
        print(f"Default Model: {config.get_default_model()}")
        print(f"Download Directory: {config.get_download_directory()}")
        print(f"API Timeout: {config.get_timeout()} seconds")
        print(f"Max Retries: {config.get_max_retries()}")
        print(f"Config File: {config.config_file}")
        print(f"Database Path: {config.database_path}")

    elif args.action == "reset":
        config.reset_to_defaults()
        print("Configuration reset to defaults")


def handle_config_set_command(args: argparse.Namespace) -> None:
    """Handle configuration set commands."""
    from mistral_ocr.config import ConfigurationManager
    from mistral_ocr.exceptions import InvalidConfigurationError

    config = ConfigurationManager()

    try:
        if args.key == "api-key":
            config.set_api_key(args.value)
            print("API key saved to configuration file")
        elif args.key == "model":
            config.set_default_model(args.value)
            print(f"Default model set to: {args.value}")
        elif args.key == "download-dir":
            download_path = pathlib.Path(args.value)
            config.set_download_directory(download_path)
            print(f"Download directory set to: {download_path}")
        else:
            print(f"Unknown configuration key: {args.key}")
            sys.exit(1)
    except InvalidConfigurationError as e:
        print(f"Error: {e}")
        sys.exit(1)




def main() -> None:
    """Main entry point for the Mistral OCR command-line interface.

    Uses subcommands to organize functionality:
    - submit: Document submission and batch processing
    - jobs: Job status checking and management  
    - results: Result retrieval and downloading
    - documents: Document querying and downloading
    - config: Configuration management

    Environment Variables:
        MISTRAL_API_KEY: Required API key for Mistral service authentication
        XDG_DATA_HOME: Optional data directory override
        XDG_STATE_HOME: Optional state directory override

    Raises:
        SystemExit: On error conditions or missing configuration
    """
    # Set up minimal file-only logging before creating audit loggers
    from mistral_ocr.settings import get_settings
    from mistral_ocr.logging import setup_logging
    
    settings = get_settings()
    setup_logging(settings.state_directory, enable_console=False)
    
    # Initialize audit logging
    audit_logger = get_audit_logger("cli")
    start_time = time.time()

    parser = argparse.ArgumentParser(
        prog="mistral-ocr", description="Submit OCR batches to the Mistral API"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Submit subcommand
    submit_parser = subparsers.add_parser("submit", help="Submit files for OCR processing")
    submit_parser.add_argument("path", help="File or directory path to submit")
    submit_parser.add_argument(
        "--recursive", action="store_true", help="Process directories recursively"
    )
    submit_parser.add_argument("--name", type=str, help="Associate files with a document name")
    submit_parser.add_argument("--uuid", type=str, help="Associate files with a document UUID")
    submit_parser.add_argument("--model", type=str, help="Specify the OCR model to use")

    # Jobs subcommand
    jobs_parser = subparsers.add_parser("jobs", help="Manage OCR jobs")
    jobs_subparsers = jobs_parser.add_subparsers(dest="jobs_action", help="Job management actions")
    
    jobs_subparsers.add_parser("list", help="List all jobs")
    
    jobs_status_parser = jobs_subparsers.add_parser("status", help="Show job status")
    jobs_status_parser.add_argument("job_id", help="Job ID to check")
    
    jobs_cancel_parser = jobs_subparsers.add_parser("cancel", help="Cancel a job")
    jobs_cancel_parser.add_argument("job_id", help="Job ID to cancel")

    # Results subcommand
    results_parser = subparsers.add_parser("results", help="Manage job results")
    results_subparsers = results_parser.add_subparsers(
        dest="results_action", help="Results management actions"
    )
    
    results_get_parser = results_subparsers.add_parser("get", help="Get job results (display)")
    results_get_parser.add_argument("job_id", help="Job ID to get results for")
    
    results_download_parser = results_subparsers.add_parser("download", help="Download job results")
    results_download_parser.add_argument("job_id", help="Job ID to download results for")
    results_download_parser.add_argument("--output", type=str, help="Output directory")

    # Documents subcommand
    documents_parser = subparsers.add_parser("documents", help="Manage documents")
    documents_subparsers = documents_parser.add_subparsers(
        dest="documents_action", help="Document management actions"
    )
    
    documents_query_parser = documents_subparsers.add_parser("query", help="Query document status")
    documents_query_parser.add_argument("name_or_uuid", help="Document name or UUID to query")
    
    documents_download_parser = documents_subparsers.add_parser(
        "download", help="Download all document results"
    )
    documents_download_parser.add_argument("name_or_uuid", help="Document name or UUID to download")
    documents_download_parser.add_argument("--output", type=str, help="Output directory")

    # Config subcommand
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_subparsers = config_parser.add_subparsers(
        dest="config_action", help="Configuration actions"
    )
    
    config_subparsers.add_parser("show", help="Show current configuration")
    config_subparsers.add_parser("reset", help="Reset configuration to defaults")
    
    config_set_parser = config_subparsers.add_parser("set", help="Set configuration values")
    config_set_parser.add_argument(
        "key", choices=["api-key", "model", "download-dir"], help="Configuration key"
    )
    config_set_parser.add_argument("value", help="Configuration value")

    args = parser.parse_args()

    # Determine command for audit logging
    if args.command == "submit":
        command = f"submit:{args.path}"
    elif args.command == "jobs":
        if args.jobs_action == "list":
            command = "jobs:list"
        elif args.jobs_action == "status":
            command = f"jobs:status:{args.job_id}"
        elif args.jobs_action == "cancel":
            command = f"jobs:cancel:{args.job_id}"
        else:
            command = "jobs:help"
    elif args.command == "results":
        if args.results_action == "get":
            command = f"results:get:{args.job_id}"
        elif args.results_action == "download":
            command = f"results:download:{args.job_id}"
        else:
            command = "results:help"
    elif args.command == "documents":
        if args.documents_action == "query":
            command = f"documents:query:{args.name_or_uuid}"
        elif args.documents_action == "download":
            command = f"documents:download:{args.name_or_uuid}"
        else:
            command = "documents:help"
    elif args.command == "config":
        if args.config_action == "show":
            command = "config:show"
        elif args.config_action == "reset":
            command = "config:reset"
        elif args.config_action == "set":
            command = f"config:set:{args.key}"
        else:
            command = "config:help"
    else:
        command = "help"

    # Log application start
    audit_logger.audit(
        AuditEventType.APPLICATION_START,
        "Started mistral-ocr CLI",
        operation=command,
        version=__version__,
        args=vars(args),
    )

    try:
        # Import here to avoid circular imports
        from mistral_ocr.client import MistralOCRClient
        from mistral_ocr.settings import get_settings

        # Initialize settings
        settings = get_settings()

        # Handle configuration commands first (these don't require API key)
        if args.command == "config":
            if args.config_action == "show":
                audit_logger.audit(
                    AuditEventType.CONFIG_CHANGE,
                    "Configuration show command",
                    operation="config_show",
                )
                # Update args to match old format for handler
                args.action = "show"
                handle_config_command(args, settings)
                return
            elif args.config_action == "reset":
                audit_logger.audit(
                    AuditEventType.CONFIG_CHANGE,
                    "Configuration reset command",
                    operation="config_reset",
                )
                # Update args to match old format for handler
                args.action = "reset"
                handle_config_command(args, settings)
                return
            elif args.config_action == "set":
                audit_logger.audit(
                    AuditEventType.CONFIG_CHANGE,
                    f"Setting configuration {args.key} to: {args.value}",
                    operation="config_set",
                    key=args.key,
                    value=args.value,
                )
                handle_config_set_command(args)
                return
            else:
                config_parser.print_help()
                return

        # Show help if no command specified
        if not args.command:
            parser.print_help()
            return

        # Get API key for non-config commands
        api_key = settings.get_api_key_optional()
        if not api_key:
            audit_logger.audit(
                AuditEventType.AUTHENTICATION,
                "No API key found",
                level="warning",
                outcome="failure",
            )
            print(
                "Error: No API key found. Set MISTRAL_API_KEY environment variable or use config."
            )
            sys.exit(1)

        try:
            client = MistralOCRClient(api_key=api_key, settings=settings)
            audit_logger.audit(
                AuditEventType.AUTHENTICATION, "Client initialized successfully", outcome="success"
            )
        except Exception as e:
            audit_logger.audit(
                AuditEventType.AUTHENTICATION,
                f"Client initialization failed: {str(e)}",
                level="error",
                outcome="failure",
                error_message=str(e),
            )
            print(f"Error initializing client: {e}")
            sys.exit(1)

        # Route to appropriate command handler
        if args.command == "submit":
            audit_logger.audit(
                AuditEventType.CLI_COMMAND,
                "Document submission requested",
                operation="submit",
                file_path=args.path,
                recursive=args.recursive,
                document_name=args.name,
                document_uuid=args.uuid,
                model=args.model,
            )
            handle_submit_command(args, client, settings)
        elif args.command == "jobs":
            if args.jobs_action == "list":
                audit_logger.audit(
                    AuditEventType.CLI_COMMAND, "Jobs listing requested", operation="list_jobs"
                )
                handle_list_jobs_command(args, client)
            elif args.jobs_action == "status":
                audit_logger.audit(
                    AuditEventType.CLI_COMMAND,
                    "Detailed job status requested",
                    operation="job_status",
                    job_id=args.job_id,
                )
                handle_job_details_command(args, client)
            elif args.jobs_action == "cancel":
                audit_logger.audit(
                    AuditEventType.CLI_COMMAND,
                    "Job cancellation requested",
                    operation="cancel_job",
                    job_id=args.job_id,
                )
                handle_cancel_job_command(args, client)
            else:
                jobs_parser.print_help()
        elif args.command == "results":
            if args.results_action == "get":
                audit_logger.audit(
                    AuditEventType.CLI_COMMAND,
                    "Results retrieval requested",
                    operation="get_results",
                    job_id=args.job_id,
                )
                handle_get_results_command(args, client)
            elif args.results_action == "download":
                audit_logger.audit(
                    AuditEventType.CLI_COMMAND,
                    "Results download requested",
                    operation="download_results",
                    job_id=args.job_id,
                    output=getattr(args, 'output', None),
                )
                handle_download_results_command(args, client)
            else:
                results_parser.print_help()
        elif args.command == "documents":
            if args.documents_action == "query":
                audit_logger.audit(
                    AuditEventType.CLI_COMMAND,
                    "Document query requested",
                    operation="query_document",
                    document_name=args.name_or_uuid,
                )
                handle_document_query_command(args, client)
            elif args.documents_action == "download":
                audit_logger.audit(
                    AuditEventType.CLI_COMMAND,
                    "Document download requested",
                    operation="download_document",
                    document_name=args.name_or_uuid,
                    output=getattr(args, 'output', None),
                )
                handle_download_document_command(args, client)
            else:
                documents_parser.print_help()

        # Log successful completion
        duration = time.time() - start_time
        audit_logger.audit(
            AuditEventType.APPLICATION_END,
            "CLI command completed successfully",
            operation=command,
            outcome="success",
            duration_seconds=round(duration, 3),
        )

    except Exception as e:
        duration = time.time() - start_time
        audit_logger.audit(
            AuditEventType.APPLICATION_END,
            f"CLI command failed: {str(e)}",
            level="error",
            operation=command,
            outcome="failure",
            duration_seconds=round(duration, 3),
            error_message=str(e),
        )
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
