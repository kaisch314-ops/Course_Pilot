from playwright.sync_api import sync_playwright, expect
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge')
    page=browser.new_page()
    page.goto('http://127.0.0.1:8765/')
    panel=page.locator('#assistant')
    panel.get_by_label('新档案名称').fill('A')
    panel.get_by_role('button',name='创建独立档案').click()
    panel.get_by_role('button',name='喜欢这个方向',exact=True).click()
    expect(panel.get_by_text('当前有 1 条反馈。',exact=False)).to_be_visible()
    with page.expect_response('**/api/solve') as response:
        panel.get_by_role('button',name='确认画像并推荐课表').click()
    payload=response.value.request.post_data_json
    assert payload['affinity'] and all(v>0 for v in payload['affinity'].values())
    assert response.value.json()['schedules']
    page.reload()
    panel.get_by_label('选择个人档案').select_option(label='A')
    expect(panel.get_by_text('当前有 1 条反馈。',exact=False)).to_be_visible()
    panel.get_by_label('新档案名称').fill('B')
    panel.get_by_role('button',name='创建独立档案').click()
    expect(panel.get_by_text('当前有 0 条反馈。',exact=False)).to_be_visible()
    panel.get_by_label('选择个人档案').select_option(label='A')
    expect(panel.get_by_text('当前有 1 条反馈。',exact=False)).to_be_visible()
    panel.get_by_text('反馈记录与撤回',exact=True).click()
    panel.get_by_role('button',name='撤回此反馈').click()
    with page.expect_response('**/api/solve') as response:
        panel.get_by_role('button',name='确认画像并推荐课表').click()
    assert response.value.request.post_data_json['affinity']=={}
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    browser.close()
print('PASS: feedback persistence, student isolation, solver payload, withdrawal, mobile')
