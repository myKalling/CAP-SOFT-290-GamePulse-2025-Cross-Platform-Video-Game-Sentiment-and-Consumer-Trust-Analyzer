const BASE_API_URL = process.env.EXPO_PUBLIC_API_URL?.replace(/\/+$/, '') ?? '';

function apiUrl(endpoint) {
  return `${BASE_API_URL}/${endpoint.replace(/^\/+/, '')}`;
}

export async function create(endpoint, data) {
  console.log("Creating data at endpoint:", endpoint, "with data:", data);
  const response = await fetch(apiUrl(endpoint), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
  });
  console.log("Response from create:", response);
  if (!response.ok) {
    return Promise.reject(
      new Error(`Failed to create data at ${endpoint}`)
    );
  }

  return response.json();
}

export async function read(endpoint) {
  const response = await fetch(apiUrl(endpoint));

  if (!response.ok) {
    return Promise.reject(
      new Error(`Failed to fetch data from ${endpoint}`)
    );
  }

  return response.json();
}

export async function update(endpoint, data) {
  const response = await fetch(apiUrl(endpoint), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    return Promise.reject(
      new Error(`Failed to update data at ${endpoint}`)
    );
  }

  return null; //no content is returned for a successful update
}

export async function del(endpoint) {
  const response = await fetch(apiUrl(endpoint), {
    method: 'DELETE',
  });

  if (!response.ok) {
    return Promise.reject(
      new Error(`Failed to delete data from ${endpoint}`)
    );
  }

  return response;
}