.mode markdown

select documents.name, jobs.job_id, jobs.status, jobs.last_api_refresh
from documents, jobs where 
documents.uuid=jobs.document_uuid
order by documents.name;

