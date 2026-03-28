export function humanizeDownloadFailure(reason?: string | null): string | null {
  const raw = reason?.trim();
  if (!raw) return null;

  const lower = raw.toLowerCase();

  if (lower.includes('403 forbidden')) {
    return 'La editorial o el proveedor bloquearon el acceso directo al PDF.';
  }
  if (lower.includes('422 unprocessable entity')) {
    return 'La fuente externa rechazó la solicitud del artículo.';
  }
  if (lower.includes('404 not found')) {
    return 'El enlace resuelto ya no tiene un PDF disponible.';
  }
  if (lower.includes('401 unauthorized')) {
    return 'La fuente externa requiere autenticación para entregar el PDF.';
  }
  if (lower.includes('server disconnected without sending a response')) {
    return 'La fuente externa cerró la conexión antes de entregar el PDF.';
  }
  if (lower.includes('timed out') || lower.includes('timeout')) {
    return 'La fuente externa tardó demasiado en responder.';
  }
  if (
    lower.includes('no se pudo resolver un pdf open-access')
    || lower.includes('no open access')
    || lower.includes('not oa')
    || lower.includes('no oa source')
    || lower.includes('open-access')
  ) {
    return 'No se encontró una versión Open Access descargable para este paper.';
  }
  if (lower.includes('no devolvió un pdf válido') || lower.includes('content-type=')) {
    return 'La URL resuelta no devolvió un PDF válido.';
  }

  return raw;
}

export function getTechnicalDownloadFailure(reason?: string | null): string | null {
  const raw = reason?.trim();
  if (!raw) return null;
  const humanized = humanizeDownloadFailure(raw);
  return humanized && humanized !== raw ? raw : null;
}
