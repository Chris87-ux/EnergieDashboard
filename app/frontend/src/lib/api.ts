export class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`HTTP ${status}`);
    this.name = "ApiError";
  }
}

async function request<T>(method: string, path: string, data?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: data === undefined ? undefined : { "Content-Type": "application/json" },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  if (response.status === 204) return undefined as T;
  const body = response.headers.get("content-type")?.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) throw new ApiError(response.status, body);
  return body as T;
}

export const apiGet = <T>(path: string) => request<T>("GET", path);
export const apiPost = <T>(path: string, data: unknown) => request<T>("POST", path, data);
export const apiPut = <T>(path: string, data: unknown) => request<T>("PUT", path, data);
export const apiDelete = <T>(path: string) => request<T>("DELETE", path);
