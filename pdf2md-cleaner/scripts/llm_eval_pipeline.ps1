# llm_eval_pipeline.ps1 - Evaluate PDF2MD pipeline design using DeepSeek via NVIDIA API
$ApiKey = "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"
$Model = "deepseek-ai/deepseek-v4-flash"

$SystemPrompt = "You are an expert in document processing pipelines and embedded systems documentation. Respond only in valid JSON."

$UserPrompt = @"
You are evaluating a PDF-to-Markdown tool pipeline design for embedded/MCU programming manuals. The pipeline uses 4 backends: (1) PyMuPDF4LLM lightweight no GPU, (2) Docling IBM TableFormer CPU-friendly, (3) Marker VikParuchuri 21k stars GPU, (4) MinerU OpenDataLab 30k stars GPU. Post-processing removes vendor names, page numbers, headers/footers, fixes table separators, formats hex addresses and register names as inline code, removes TOC and revision history. LLM evaluation scores each output on table quality, structure, cleanliness, register data, readability (0-50 total). Evaluate this design. Respond in JSON with fields: design_score (0-10), strengths (array), weaknesses (array), recommendations (array), backend_ranking (array), additional_cleanup_patterns (array).
"@

$Body = @{
    model = $Model
    messages = @(
        @{ role = "system"; content = $SystemPrompt }
        @{ role = "user"; content = $UserPrompt }
    )
    temperature = 0.1
    max_tokens = 2000
} | ConvertTo-Json -Depth 5

$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer $ApiKey"
}

Write-Host "Calling NVIDIA API ($Model)..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "https://integrate.api.nvidia.com/v1/chat/completions" -Method Post -Headers $headers -Body $Body -TimeoutSec 120
    $content = $response.choices[0].message.content
    Write-Host $content -ForegroundColor Green
    $content | Out-File -FilePath "C:\Users\WJ\.qclaw\workspace-agent-f93ed705\pdf2md-cleaner\pipeline_evaluation.json" -Encoding utf8
    Write-Host "`nSaved to pipeline_evaluation.json" -ForegroundColor Yellow
} catch {
    Write-Host "API call failed: $_" -ForegroundColor Red
}
