<?php
// Configure how the PHP proxy connects to your real backend
// Example: FastAPI running at http://localhost:8000/api


return [
'BACKEND_BASE' => getenv('BACKEND_BASE') ?: 'http://localhost:8000/api',
// Optional fixed token you can set on the server (overridden by client-sent token if present)
'BEARER_TOKEN' => getenv('BEARER_TOKEN') ?: ''
];