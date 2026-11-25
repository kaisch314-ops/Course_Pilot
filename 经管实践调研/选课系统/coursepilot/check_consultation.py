from playwright.sync_api import sync_playwright,expect
with sync_playwright() as p:
 b=p.chromium.launch(channel='msedge');page=b.new_page(viewport={'width':1440,'height':960});page.goto('http://127.0.0.1:8765/')
 expect(page.get_by_role('dialog')).to_have_count(0)
 page.get_by_role('button',name='打开选课咨询').click()
 d=page.get_by_role('dialog',name='选课咨询');expect(d).to_be_visible()
 assert '参数' not in d.inner_text() and '模拟器' not in d.inner_text()
 d.get_by_label('咨询内容').fill('我想学数据分析，周三下午要实习');d.get_by_role('button',name='发送消息').click()
 with page.expect_response('**/recommend') as r:d.get_by_role('button',name='按这个安排更新课表').click()
 assert r.value.json()['profile']['blocked'][0]['day']==3
 page.screenshot(path='chat-desktop.png')
 page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth');page.screenshot(path='chat-mobile.png')
 d.get_by_role('button',name='收起选课咨询').click();expect(d).to_have_count(0)
 b.close()
print('PASS: floating chat, clean UI, recommendation, mobile and collapse')

