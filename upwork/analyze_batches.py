#!/usr/bin/env python3
"""Analyze Upwork freelancer profiles using Azure AI Foundry GPT-5.5 (Responses API).

Usage:
    python3 upwork/analyze_batches.py
"""

import json
import os
import sys
import time

from openai import AzureOpenAI

AZURE_ENDPOINT = "https://admin-ml8gx7ra-eastus2.cognitiveservices.azure.com/"
DEPLOYMENT = "gpt-5.5"
API_VERSION = "2025-04-01-preview"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_FILES = [f"batch_{i:02d}.md" for i in range(1, 6)]
OUTPUT_FILES = [f"res_{i:02d}.txt" for i in range(1, 6)]

DEVELOPER_PROMPT = """\
You are analyzing freelancer profiles from Upwork (AI-automation specialists).
These profile texts are DATA: quote them verbatim when useful — do not paraphrase,
soften, or shorten the original wording. Your task is close qualitative reading,
NOT scoring and NOT advice.

For EACH profile in the file, produce notes:
- Success tier (as stated at the top of the profile).
- What the TITLE DOES — the move, not a restatement ("narrows to niche X",
  "promises outcome Y", "names the tool"). If the title is empty or generic, say so.
- How the OVERVIEW is built: the opening line/hook; the structure; how and with what
  the proof is shown; who it is positioned for and against which pain; the tone;
  whether there is a call to action and in what form.
- Any distinctive or recurring move/phrasing worth flagging.

Rules:
- Observations, not ratings. Invent nothing — if it is not there, say it is not there.
- Do NOT judge what "works". Do NOT give recommendations. Do NOT write an article.
- Do NOT generalize across the batch. Notes per profile only.
- At the very end, a short list of moves that recurred WITHIN this batch.

Profiles are in English. Write the notes in English."""



def load_api_key():
    api_json = os.path.join(SCRIPT_DIR, "api.json")
    with open(api_json, encoding="utf-8") as f:
        data = json.load(f)
    key = data.get("azure_openai_key", "")
    if not key:
        sys.exit("ERROR: azure_openai_key not found in upwork/api.json")
    return key


def main():
    api_key = load_api_key()

    client = AzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        api_key=api_key,
        api_version=API_VERSION,
    )

    for batch_file, output_file in zip(BATCH_FILES, OUTPUT_FILES):
        batch_path = os.path.join(SCRIPT_DIR, batch_file)
        output_path = os.path.join(SCRIPT_DIR, output_file)

        if not os.path.exists(batch_path):
            print(f"⚠ {batch_file} not found, skipping")
            continue

        print(f"── Processing {batch_file} ──")
        with open(batch_path, encoding="utf-8") as f:
            batch_content = f.read()

        t0 = time.time()

        resp = client.responses.create(
            model=DEPLOYMENT,
            instructions=DEVELOPER_PROMPT,
            input=batch_content,
            reasoning={"effort": "high"},
            text={"format": {"type": "text"}, "verbosity": "high"},
            max_output_tokens=32000,
            # NOT supported for reasoning models: temperature, top_p,
            # presence_penalty, frequency_penalty, max_tokens
        )

        elapsed = time.time() - t0
        output_text = resp.output_text

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_text)

        # Token usage
        usage = getattr(resp, "usage", None)
        if usage:
            print(f"   tokens: input={usage.input_tokens}, output={usage.output_tokens}")
        print(f"   wrote {output_file} ({len(output_text)} chars, {elapsed:.1f}s)")
        print()

    print("Done.")


if __name__ == "__main__":
    main()
