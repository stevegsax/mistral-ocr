# cURL Commands to Work With Mistral API Batch Jobs  

Based on the OpenAPI specification, here's the `curl` command to list batch jobs from the Mistral API:

```bash
curl -X GET "https://api.mistral.ai/v1/batch/jobs" \
  -H "Authorization: Bearer $MISTRAL_API_KEY" \
  -H "Content-Type: application/json"
```

## With Optional Query Parameters

You can add query parameters to filter the results:

```bash
curl -X GET "https://api.mistral.ai/v1/batch/jobs?page=0&page_size=100&created_by_me=true" \
  -H "Authorization: Bearer $MISTRAL_API_KEY" \
  -H "Content-Type: application/json"
```

## Available Query Parameters

- `page` - Page number (default: 0)
- `page_size` - Number of jobs per page (default: 100)
- `model` - Filter by model name
- `status` - Filter by job status (QUEUED, RUNNING, SUCCESS, FAILED, etc.)
- `created_after` - Filter by creation date (ISO datetime format)
- `created_by_me` - Show only jobs created by you (true/false, default: false)
- `metadata` - Filter by metadata object

## Example with Status Filter

```bash
curl -X GET "https://api.mistral.ai/v1/batch/jobs?status=RUNNING&status=SUCCESS" \
  -H "Authorization: Bearer $MISTRAL_API_KEY" \
  -H "Content-Type: application/json"
```

## Response Format

The response will be a `BatchJobsOut` object containing:
```json
{
  "data": [
    {
      "id": "job-uuid",
      "status": "SUCCESS",
      "model": "model-name",
      "endpoint": "/v1/chat/completions",
      "created_at": 1234567890,
      "total_requests": 100,
      "completed_requests": 100,
      "succeeded_requests": 95,
      "failed_requests": 5,
      ...
    }
  ],
  "object": "list",
  "total": 1
}
```

Make sure you have your `MISTRAL_API_KEY` environment variable set before running the command.

