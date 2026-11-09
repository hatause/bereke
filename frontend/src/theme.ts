export type Theme = 'light'|'dark'
export function initialTheme(stored:string|null, prefersDark:boolean):Theme {
  return stored === 'light' || stored === 'dark' ? stored : prefersDark ? 'dark' : 'light'
}
