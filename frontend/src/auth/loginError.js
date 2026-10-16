export function getLoginErrorMessage(error) {
  if (error.response?.status === 401) {
    return "Invalid username or password. Verify the credentials configured for this deployment.";
  }

  const detail = error.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (!error.response) {
    return "Could not reach the API. Check the backend URL, service availability, and CORS configuration.";
  }

  return `Login request failed (HTTP ${error.response.status}). Please try again.`;
}
