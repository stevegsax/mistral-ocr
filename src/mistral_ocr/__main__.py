import argparse
import os
import pathlib


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mistral-ocr", description="Submit OCR batches to the Mistral API"
    )

    parser.add_argument("--submit", type=str, help="Submit a file or directory for OCR processing")

    parser.add_argument("--check-job", type=str, help="Check the status of a job by ID")

    parser.add_argument(
        "--get-results", type=str, help="Retrieve results for a completed job by ID"
    )

    args = parser.parse_args()

    # Import here to avoid circular imports
    from mistral_ocr.client import MistralOCRClient

    # Get API key from environment variable
    api_key = os.environ.get("MISTRAL_API_KEY", "test")
    client = MistralOCRClient(api_key=api_key)

    if args.submit:
        # Submit the file/directory
        file_path = pathlib.Path(args.submit)
        job_id = client.submit_documents([file_path])
        print(f"Submitted job: {job_id}")
    elif getattr(args, "check_job", None):
        # Check job status
        status = client.check_job_status(args.check_job)
        print(f"Job {args.check_job} status: {status}")
    elif getattr(args, "get_results", None):
        # Get job results
        results = client.get_results(args.get_results)
        print(f"Results for job {args.get_results}: {len(results)} items")


if __name__ == "__main__":
    main()
