from playwright.sync_api import sync_playwright, expect
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge')
    page = browser.new_page()
    page.goto('http://127.0.0.1:8765/')
    panel = page.locator('#assistant')
    panel.get_by_label('新档案名称').fill('测试学生')
    panel.get_by_role('button',name='创建独立档案').click()
    box = panel.get_by_label('和小助手聊聊')
    box.fill('我想学数据分析，周三下午要实习')
    panel.get_by_role('button', name='发送', exact=True).click()
    assert {'计量','实证','量化'} <= set(panel.get_by_label('长期兴趣（逗号分隔）').input_value().split('、'))
    with page.expect_response('**/api/solve') as response:
        panel.get_by_role('button',name='确认画像并推荐课表').click()
    request = response.value.request.post_data_json
    assert request['blocked'][0]['day'] == 3
    assert request['blocked'][0]['start'] == 5
    assert '量化' in request['interests']
    assert response.value.json()['schedules']
    box.fill('不想学量化')
    panel.get_by_role('button',name='发送',exact=True).click()
    assert '量化' not in panel.get_by_label('长期兴趣（逗号分隔）').input_value()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    browser.close()
print('PASS: assistant extraction, confirmation, solver integration, negative interest, mobile layout')


