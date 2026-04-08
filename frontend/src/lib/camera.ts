/**
 * Safe camera access: navigator.mediaDevices is undefined in some contexts
 * (non-HTTPS non-localhost, embedded webviews, SSR, very old browsers).
 * Uses modern API when available, otherwise legacy prefixed getUserMedia.
 */

/** True if some getUserMedia implementation exists (modern or legacy). */
export function isCameraSupportedEnvironment(): boolean {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    return false;
  }
  return getGetUserMediaFn() !== null;
}

function getGetUserMediaFn():
  | ((c: MediaStreamConstraints) => Promise<MediaStream>)
  | null {
  const nav = navigator as Navigator & {
    getUserMedia?: LegacyGetUserMedia;
    webkitGetUserMedia?: LegacyGetUserMedia;
    mozGetUserMedia?: LegacyGetUserMedia;
    msGetUserMedia?: LegacyGetUserMedia;
  };

  if (nav.mediaDevices?.getUserMedia) {
    return (constraints) => nav.mediaDevices!.getUserMedia(constraints);
  }

  const legacy =
    nav.getUserMedia ||
    nav.webkitGetUserMedia ||
    nav.mozGetUserMedia ||
    nav.msGetUserMedia;

  if (!legacy) {
    return null;
  }

  return (constraints) =>
    new Promise<MediaStream>((resolve, reject) => {
      legacy.call(nav, constraints, resolve, reject);
    });
}

type LegacyGetUserMedia = (
  constraints: MediaStreamConstraints,
  success: (stream: MediaStream) => void,
  failure: (err: Error) => void,
) => void;

export function getCameraStream(
  constraints: MediaStreamConstraints = { video: { facingMode: "user" }, audio: false },
): Promise<MediaStream> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Camera is only available in the browser."));
  }

  if (!window.isSecureContext) {
    const host = window.location.hostname;
    const isLocal =
      host === "localhost" ||
      host === "127.0.0.1" ||
      host === "[::1]" ||
      host.endsWith(".localhost");
    if (!isLocal) {
      return Promise.reject(
        new Error(
          "Camera requires a secure connection (HTTPS) or localhost. Open the app via http://localhost:8080 or HTTPS.",
        ),
      );
    }
  }

  const fn = getGetUserMediaFn();
  if (!fn) {
    return Promise.reject(
      new Error(
        "This browser does not support camera access. Try Chrome, Firefox, Safari, or Edge, and use localhost or HTTPS.",
      ),
    );
  }

  return fn(constraints);
}

export function stopMediaStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => {
    track.stop();
  });
}
