import argparse
import pathlib
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mistral-ocr", description="Submit OCR batches to the Mistral API"
    )

    parser.add_argument("--submit", type=str, help="Submit a file or directory for OCR processing")
    parser.add_argument("--recursive", action="store_true", help="Process directories recursively")
    parser.add_argument("--document-name", type=str, help="Associate files with a document name")
    parser.add_argument("--document-uuid", type=str, help="Associate files with a document UUID")
    parser.add_argument("--model", type=str, help="Specify the OCR model to use")

    parser.add_argument("--check-job", type=str, help="Check the status of a job by ID")
    parser.add_argument("--query-document", type=str, help="Query job statuses by document name")
    parser.add_argument("--cancel-job", type=str, help="Cancel a job by ID")

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
        if args.submit:
            # Submit the file/directory
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

        elif args.check_job:
            # Check job status
            status = client.check_job_status(args.check_job)
            print(f"Job {args.check_job} status: {status}")

        elif args.query_document:
            # Query document status
            statuses = client.query_document_status(args.query_document)
            print(f"Document '{args.query_document}' job statuses:")
            for i, status in enumerate(statuses, 1):
                print(f"  Job {i}: {status}")

        elif args.cancel_job:
            # Cancel job
            success = client.cancel_job(args.cancel_job)
            if success:
                print(f"Successfully cancelled job {args.cancel_job}")
            else:
                print(f"Failed to cancel job {args.cancel_job}")

        elif args.get_results:
            # Get job results
            results = client.get_results(args.get_results)
            print(f"Results for job {args.get_results}: {len(results)} items")
            for i, result in enumerate(results, 1):
                print(f"\n--- Result {i} ({result.file_name}) ---")
                print(result.text[:200] + "..." if len(result.text) > 200 else result.text)

        elif args.download_results:
            # Download job results
            destination = None
            if args.download_to:
                destination = pathlib.Path(args.download_to)

            client.download_results(args.download_results, destination)
            print(f"Downloaded results for job {args.download_results}")

        elif args.download_document:
            # Download all results for a document
            destination = None
            if args.download_to:
                destination = pathlib.Path(args.download_to)

            client.download_document_results(args.download_document, destination)
            print(f"Downloaded all results for document {args.download_document}")

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

