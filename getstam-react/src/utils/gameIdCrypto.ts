export function encodeGameId(hexId: string): string {
  const bytes = hexId.match(/.{2}/g)!.map(h => parseInt(h, 16));
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

export function decodeGameId(encoded: string): string {
  try {
    const pad = (4 - encoded.length % 4) % 4;
    const b64 = encoded.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat(pad);
    return Array.from(atob(b64))
      .map(c => c.charCodeAt(0).toString(16).padStart(2, '0')).join('');
  } catch {
    return encoded; // fallback: treat as raw id if decode fails
  }
}
