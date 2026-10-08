# FormaX AI – Frontend (Member 1)

    npm install
    cp .env.example .env     # VITE_USE_MOCK=true works without the backend
    npm run dev              # http://localhost:5173

Set VITE_USE_MOCK=false once Member 2's FastAPI runs on :8000 (Vite proxies /api).

## Contract with Member 2 – POST /api/generate
Request: source_text, source_type ("file"|"text"), source_filename, output_types (array),
audience, tone, language, detail_level, objective.
Response: { "outputs": [ { output_type, title, summary, key_points[], body } ] }
Errors: non-2xx with { "detail": "message" } (shown to the user).
