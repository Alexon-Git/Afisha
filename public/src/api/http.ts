export class ApiUnavailableError extends Error {
  constructor() { super('Public API unavailable'); }
}

export async function readJson<T>(url: string): Promise<T> {
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      credentials: 'omit',
      cache: 'no-store',
      redirect: 'error',
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new ApiUnavailableError();
    return await response.json() as T;
  } catch {
    // Do not expose internal addresses, response bodies or transport exceptions.
    throw new ApiUnavailableError();
  }
}
