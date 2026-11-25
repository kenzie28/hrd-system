export const GAJI_MODULE_PASSWORD = 'bears'
export const GAJI_PASSWORD_STORAGE_KEY = 'hrd_gaji_password'
export const GAJI_PASSWORD_HEADER = 'X-Gaji-Password'

export function readGajiPassword(): string {
  try {
    return sessionStorage.getItem(GAJI_PASSWORD_STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

export function storeGajiPassword(password: string) {
  try {
    sessionStorage.setItem(GAJI_PASSWORD_STORAGE_KEY, password)
  } catch {
    /* ignore quota / private mode */
  }
}

export function clearGajiPassword() {
  try {
    sessionStorage.removeItem(GAJI_PASSWORD_STORAGE_KEY)
  } catch {
    /* ignore */
  }
}
