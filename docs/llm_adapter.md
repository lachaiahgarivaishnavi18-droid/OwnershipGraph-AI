# Optional evidence selection adapter

The default is entirely local. To opt in, export LLM_ENABLED=true, LLM_API_KEY
and LLM_MODEL (a model available to your account that supports structured output).
Only then do reporting and assistant requests call the OpenAI Responses API.
The configured model and prompt version are recorded in results and agent logs.
Enabling the adapter sends the prepared evidence statements and user question to
the provider; configure it only for records permitted under your data policy.

The adapter uses `text.format` with a strict JSON schema, following the
[official structured output documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).
It sets store=false and a bounded HTTP timeout. This is not a claim about a
provider's retention policy; review your applicable account/data controls.

The model can select and order fact IDs only. Server-side Pydantic validation
rejects unknown IDs, prose, extra fields, empty or oversized selections. Displayed
sentences and citations always come from deterministic calculations. Missing keys,
timeouts, refusals, invalid responses and API errors fall back to the local result.
No model-generated percentage, relationship, screening match or score can enter
the application through this adapter. This intentional extractive design is more
constrained than free-form generative reasoning.

Transport and response validation are tested with stubbed responses. No real API
key or paid external request was used during local verification.
