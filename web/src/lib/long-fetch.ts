/**
 * Long-running upstream proxy fetch.
 *
 * Node's built-in fetch uses undici with a 5-minute body timeout — too short
 * for the resume generate pipeline, which can run 6+ minutes through revision
 * loops. Use a dedicated undici Agent with timeouts disabled.
 */
import { Agent, fetch as undiciFetch } from "undici";

const longAgent = new Agent({
  // 0 disables the timeout
  bodyTimeout: 0,
  headersTimeout: 0,
  keepAliveTimeout: 60_000,
  keepAliveMaxTimeout: 600_000,
});

export type LongFetchInit = {
  method?: string;
  headers?: Record<string, string>;
  body?: string | Uint8Array | ArrayBuffer | FormData | ReadableStream<Uint8Array> | null;
  signal?: AbortSignal;
};

export async function longFetch(url: string, init: LongFetchInit = {}): Promise<Response> {
  const res = await undiciFetch(url, {
    method: init.method ?? "GET",
    headers: init.headers,
    // undici's BodyInit is broader than the spec; cast away the difference
    body: init.body as never,
    signal: init.signal,
    dispatcher: longAgent,
  });
  // Bridge undici Response → web Response so Next route handlers can return it.
  return new Response(res.body as ReadableStream<Uint8Array> | null, {
    status: res.status,
    headers: Object.fromEntries(res.headers.entries()),
  });
}
