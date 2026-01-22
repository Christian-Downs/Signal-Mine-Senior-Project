<?php
header('Access-Control-Allow-Methods: POST, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}


$cfg = require __DIR__ . '/config.php';
$raw = file_get_contents('php://input');
$in = json_decode($raw, true) ?: [];
$prompt = $in['prompt'] ?? '';
$conversation_id = $in['conversation_id'] ?? null;
$backendBase = $in['base'] ?? $cfg['BACKEND_BASE'];
$token = $in['token'] ?? $cfg['BEARER_TOKEN'];


if (!$prompt) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing prompt']);
    exit;
}


$endpoint = rtrim($backendBase, '/') . '/chat';


$ch = curl_init($endpoint);
$payload = json_encode(array_filter([
    'prompt' => $prompt,
    'conversation_id' => $conversation_id
]));


$headers = ['Content-Type: application/json'];
if ($token) {
    $headers[] = 'Authorization: Bearer ' . $token;
}


curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => $headers,
    CURLOPT_POSTFIELDS => $payload,
    CURLOPT_RETURNTRANSFER => false, // we'll stream directly
    CURLOPT_HEADER => true,
    CURLOPT_WRITEFUNCTION => function ($ch, $chunk) {
        static $headerDone = false;
        static $buffer = '';


        if (!$headerDone) {
            // Split headers from body
            $pos = strpos($chunk, "\r\n\r\n");
            if ($pos !== false) {
                $headers = substr($chunk, 0, $pos);
                $body = substr($chunk, $pos + 4);
                // Detect content type of backend
                if (stripos($headers, 'Content-Type: text/event-stream') !== false) {
                    header('Content-Type: text/event-stream');
                    header('Cache-Control: no-cache');
                    header('X-Accel-Buffering: no'); // for nginx
                    @ob_end_flush();
                    @flush();
                } else {
                    // Default to JSON passthrough
                    header('Content-Type: application/json');
                }
                $headerDone = true;
                if ($body !== '') {
                    echo $body;
                    @ob_flush();
                    @flush();
                }
            }
            return strlen($chunk);
        }


        echo $chunk; // pass through stream chunks
        @ob_flush();
        @flush();
        return strlen($chunk);
    },
]);


curl_exec($ch);
if (curl_errno($ch)) {
    if (!headers_sent()) header('Content-Type: application/json');
    echo json_encode(['error' => 'Proxy error', 'detail' => curl_error($ch)]);
}
curl_close($ch);
