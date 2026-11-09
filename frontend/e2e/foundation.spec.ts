import { test, expect } from '@playwright/test'

test('lesson progress survives reload, dashboard updates, theme persists',async({page,request})=>{
  await page.goto('/')
  await page.getByRole('link',{name:'Открыть урок'}).first().click()
  await expect(page.getByRole('heading',{level:1})).toHaveText('Welcome Day')
  await page.getByRole('button',{name:'Отметить прочитанным'}).first().click()
  await expect(page.getByRole('status')).toContainText('Прогресс сохранён')
  await page.reload()
  await expect(page.getByTestId('lesson-progress')).toHaveText('Прочитано 1 из 6 разделов')
  await expect(page.getByRole('button',{name:'Снять отметку о прочтении'})).toHaveCount(1)
  const state=await (await request.get('/api/lessons/1')).json()
  expect(state.completed_sections).toBe(1)
  await page.getByRole('link',{name:'Обзор',exact:true}).click()
  await expect(page.getByText('1 из 22 разделов', {exact:true})).toBeVisible()
  await page.getByRole('button',{name:'Переключить тему'}).click()
  const theme=await page.locator('html').getAttribute('data-theme')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme',theme!)
  await page.setViewportSize({width:390,height:844})
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await page.screenshot({path:'test-results/mobile.png',fullPage:true})
  await page.setViewportSize({width:1440,height:1000})
  await page.screenshot({path:'test-results/dashboard.png',fullPage:true})
})

test('private files cannot be served through Vite or API',async({request})=>{
  const project=process.cwd().replaceAll('\\','/').replace(/\/frontend$/,'')
  for(const file of ['data/reviewed_content.json','.local/academy.sqlite3','sources/private/День 2. МП и карты.pdf']) {
    const response=await request.get('/@fs/'+project+'/'+file)
    expect([403,404]).toContain(response.status())
  }
  expect((await request.get('/api/sources/private/test.pdf')).status()).toBe(404)
})

test('glossary search, conflicts and light lesson render from API',async({page})=>{
  const errors:string[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  await page.goto('/terms')
  await page.getByRole('textbox',{name:'Поиск термина'}).fill('гэсв')
  await expect(page.getByRole('heading',{level:2})).toHaveText('ГЭСВ')
  await expect(page.getByText('Годовая эффективная ставка вознаграждения.',{exact:true})).toBeVisible()
  await page.getByRole('link',{name:'Проверка фактов',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Максимальный возраст заёмщиц'})).toBeVisible()
  await expect(page.getByText('Максимум для женщин — 61 год.',{exact:true})).toBeVisible()
  await expect(page.getByText('Максимум для женщин — 60 лет.',{exact:true})).toBeVisible()
  await page.getByRole('link',{name:'Настройки',exact:true}).click()
  await page.getByRole('combobox',{name:'Тема'}).selectOption('light')
  await page.goto('/lessons/3')
  await expect(page.getByRole('heading',{name:'SWIFT в учебном материале'})).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme','light')
  await page.screenshot({path:'test-results/lesson-light.png',fullPage:true})
  expect(errors).toEqual([])
})
