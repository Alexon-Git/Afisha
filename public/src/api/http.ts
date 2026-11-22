export class ApiUnavailableError extends Error {
  constructor() { super('Public API unavailable'); }
}

export class ApiNotFoundError extends Error {}

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
    if (response.status === 404) throw new ApiNotFoundError();
    if (!response.ok) throw new ApiUnavailableError();
    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiNotFoundError) throw error;
    // Do not expose internal addresses, response bodies or transport exceptions.
    throw new ApiUnavailableError();
  }
}
