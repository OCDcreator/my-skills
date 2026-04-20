import { execFile } from 'node:child_process';
import OpenAI from 'openai';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY ?? 'fixture-key' });

export async function runAgenticSmoke(prompt: string, htmlResponse: string) {
  const container = document.createElement('div');
  container.innerHTML = htmlResponse;
  container.insertAdjacentHTML('beforeend', '<strong>fixture</strong>');

  const cdpTargets = await fetch('http://127.0.0.1:9222/json/list').then((response) => response.text());
  console.debug('[agentic-ai-smoke] cdp targets length', cdpTargets.length);

  await fetch('https://telemetry.example.invalid/agentic-event', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      event: 'agentic-smoke',
      promptLength: prompt.length,
    }),
  });

  const completion = await openai.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: prompt }],
  });
  console.log('[agentic-ai-smoke] model response', completion.choices?.[0]?.message?.content ?? '');

  execFile(process.execPath, ['-e', "console.log('desktop-only helper')"]);
  return container.textContent ?? '';
}
