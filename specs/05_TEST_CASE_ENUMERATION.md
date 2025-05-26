# Test Case Enumeration

> This document lists the test cases for `mistral-ocr` in order of increasing complexity. These cases are derived from the requirements, architecture, pseudocode, and test design.

## Basic File Submission
1. **Submit single PNG file** – valid path returns a batch/job ID.
2. **Submit single JPEG file** – valid path returns a batch/job ID.
3. **Submit single PDF file** – valid path returns a batch/job ID.
4. **Unsupported file type** – submission of a non‑image/PDF file raises a validation error.
5. **File not found** – submission of a non‑existent path raises a `FileNotFoundError`.

## Directory Submission
6. **Submit directory (non‑recursive)** – only top‑level files are processed, hidden files ignored.
7. **Submit directory recursively** – subdirectories are traversed when the recursive option is enabled.
8. **Automatic batch partitioning** – more than 100 files triggers creation of multiple batch jobs.

## Document Naming and Association
9. **Create new document by name** – pages submitted with a new document name generate a new document record with UUID.
10. **Append pages to recent document by name** – subsequent submission with same name appends to the most recent document.
11. **Append pages to document by UUID** – specifying the UUID appends pages to that document regardless of name.

## Job Management
12. **Check job status by job ID** – returns one of `pending`, `processing`, `completed`, or `failed`.
13. **Query status by document name** – lists all batches associated with that document name with their statuses.
14. **Cancel job** – issuing a cancel command for a job ID returns immediate confirmation.
15. **Invalid job ID** – checking or cancelling with an unknown ID returns a meaningful error.

## Result Retrieval
16. **Retrieve results for completed job** – returns a list of `OCRResult` objects containing text, markdown, file name, and job ID.
17. **Attempt retrieval before completion** – raises an error or message that the job is not yet completed.
18. **Automatic download of results** – results are saved under `$XDG_DATA_HOME/<document-name>` with name normalization.
19. **Unknown document storage** – pages without a document name are stored under an `unknown` directory.
20. **Re‑download results** – repeated retrieval attempts succeed after a transient failure.

## Advanced Options and CLI
21. **Specify custom OCR model** – submitting files with a model parameter uses that model.
22. **Command line submission** – `--submit` invokes file submission and prints job ID.
23. **Command line status check** – `--check-job` prints the current job status.
24. **Command line result retrieval** – `--get-results` outputs or downloads OCR results.
25. **Logging of errors** – errors during submission or retrieval are written to a log file.
26. **Batch processing for cost management** – verify that no batch contains more than 100 files and API calls are grouped accordingly.
