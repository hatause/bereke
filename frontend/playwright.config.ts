import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
const python=fileURLToPath(new URL(process.platform==='win32'?'../.venv/Scripts/python.exe':'../.venv/bin/python',import.meta.url))
export default defineConfig({
  testDir:'./e2e',workers:1,retries:0,reporter:'list',
  use:{baseURL:'http://127.0.0.1:5173',trace:'retain-on-failure'},
  webServer:[
    {command:`"${python}" ../scripts/e2e_server.py`,url:'http://127.0.0.1:8000/api/health',reuseExistingServer:false,timeout:60000},
    {command:'npm run dev',url:'http://127.0.0.1:5173',reuseExistingServer:false,timeout:60000},
  ],
})
