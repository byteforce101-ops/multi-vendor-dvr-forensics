const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request(path, { accessToken, body, headers = {}, method = 'GET' } = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
    body,
  })
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail || `Request failed (${response.status})`)
  }
  return response.json()
}

export function createCase(accessToken, payload) {
  return request('/cases', {
    accessToken,
    method: 'POST',
    body: JSON.stringify(payload),
    headers: { 'Content-Type': 'application/json' },
  })
}

export function uploadEvidence(accessToken, caseId, file) {
  const form = new FormData()
  form.append('file', file)
  return request(`/cases/${caseId}/evidence/upload`, { accessToken, body: form, method: 'POST' })
}

export function parseEvidence(accessToken, evidenceId) {
  return request(`/evidence/${evidenceId}/parse`, { accessToken, method: 'POST' })
}
