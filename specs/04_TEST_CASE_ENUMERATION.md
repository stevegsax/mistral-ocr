# Test Case Enumeration

> This document lists the test cases for `mistral-ocr` in order of increasing complexity. These cases are derived from the requirements, architecture, pseudocode, and test design.


## Basic Integrity Checks
1. **Display help message** – running `uv run mistral-ocr --help` shows usage information without errors.
2. **Configuration availability** – required configuration variables exist and the configuration file can be loaded.
3. **Log file creation** – starting the program generates a log file in the expected location.
4. **Database connectivity** – the SQLite database can be created and a simple query executed.

## Basic File Submission
5. **Submit single PNG file** – valid path returns a batch/job ID.
6. **Submit single JPEG file** – valid path returns a batch/job ID.
7. **Submit single PDF file** – valid path returns a batch/job ID.
8. **Unsupported file type** – submission of a non‑image/PDF file raises a validation error.
9. **File not found** – submission of a non‑existent path raises a `FileNotFoundError`.

## Directory Submission
10. **Submit directory (non‑recursive)** – only top‑level files are processed, hidden files ignored.
11. **Submit directory recursively** – subdirectories are traversed when the recursive option is enabled.
12. **Automatic batch partitioning** – more than 100 files triggers creation of multiple batch jobs.

## Document Naming and Association
13. **Create new document by name** – pages submitted with a new document name generate a new document record with UUID.
14. **Append pages to recent document by name** – subsequent submission with same name appends to the most recent document.
15. **Append pages to document by UUID** – specifying the UUID appends pages to that document regardless of name.

## Job Management
16. **Check job status by job ID** – returns one of `pending`, `processing`, `completed`, or `failed`.
17. **Query status by document name** – lists all batches associated with that document name with their statuses.
18. **Cancel job** – issuing a cancel command for a job ID returns immediate confirmation.
19. **Invalid job ID** – checking or cancelling with an unknown ID returns a meaningful error.

## Result Retrieval
20. **Retrieve results for completed job** – returns a list of `OCRResult` objects containing text, markdown, file name, and job ID.
21. **Attempt retrieval before completion** – raises an error or message that the job is not yet completed.
22. **Automatic download of results** – results are saved under `$XDG_DATA_HOME/<document-name>` with name normalization.
23. **Unknown document storage** – pages without a document name are stored under an `unknown` directory.
24. **Re‑download results** – repeated retrieval attempts succeed after a transient failure.

## Advanced Options and CLI
25. **Specify custom OCR model** – submitting files with a model parameter uses that model.
26. **Command line submission** – `--submit` invokes file submission and prints job ID.
27. **Command line status check** – `--check-job` prints the current job status.
28. **Command line result retrieval** – `--get-results` outputs or downloads OCR results.
29. **Logging of errors** – errors during submission or retrieval are written to a log file.
30. **Batch processing for cost management** – verify that no batch contains more than 100 files and API calls are grouped accordingly.
