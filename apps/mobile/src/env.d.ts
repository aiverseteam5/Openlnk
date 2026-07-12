/**
 * Expo public env var types.
 * Expo injects EXPO_PUBLIC_* at build time via babel transform.
 */
declare namespace NodeJS {
  interface ProcessEnv {
    EXPO_PUBLIC_API_URL?: string;
  }
}
