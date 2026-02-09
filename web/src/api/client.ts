const BASE_URL = '/api'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

type RequestOptions = {
  params?: Record<string, string | number | boolean | undefined>
}

export async function fetchApi<T>(path: string, options?: RequestOptions): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`, window.location.origin)

  if (options?.params) {
    for (const [key, value] of Object.entries(options.params)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value))
      }
    }
  }

  const response = await fetch(url.toString())

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new ApiError(response.status, body.detail ?? 'Unknown error')
  }

  return response.json() as Promise<T>
}
