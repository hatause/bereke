import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, saveProgress } from './api'
import { initialTheme } from './theme'
afterEach(()=>vi.unstubAllGlobals())
describe('API boundary',()=>{
  it('reports backend errors instead of pretending to save',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(null,{status:503})))
    await expect(saveProgress(7,true)).rejects.toThrow('503')
  })
  it('sends explicit idempotent progress state',async()=>{
    const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({completed:true})});vi.stubGlobal('fetch',fetch)
    await saveProgress(7,true)
    expect(fetch).toHaveBeenCalledWith('/api/sections/7/progress',expect.objectContaining({method:'PUT',body:'{"completed":true}'}))
  })
  it('does not swallow a network failure',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('offline')))
    await expect(api('/lessons')).rejects.toThrow('offline')
  })
})
it('uses valid persisted theme and rejects corrupted storage',()=>{
  expect(initialTheme('dark',false)).toBe('dark')
  expect(initialTheme('invalid',false)).toBe('light')
  expect(initialTheme(null,true)).toBe('dark')
})
