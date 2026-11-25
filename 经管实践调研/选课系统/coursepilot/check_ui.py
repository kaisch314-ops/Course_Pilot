from pathlib import Path
from tempfile import gettempdir
from playwright.sync_api import sync_playwright, expect

proof = Path(gettempdir()) / "CoursePilot-review"
proof.mkdir(exist_ok=True)
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge")
    page = browser.new_page(viewport={"width":1440,"height":960})
    page.goto("http://127.0.0.1:8765/")
    page.get_by_role("button",name="解析偏好").click()
    expect(page.get_by_text("条件已修改，等待重新排课")).to_be_visible()
    page.get_by_role("button", name="应用条件并生成课表").click()
    expect(page.locator(".blocked-slot")).to_be_visible()
    bank = page.locator("article").filter(has=page.get_by_role("heading",name="货币银行学",exact=False))
    bank.get_by_role("button",name="已选上，锁定此班").click()
    source = page.locator("article").filter(has=page.get_by_role("heading",name="公司金融",exact=False))
    old = source.locator("code").inner_text()
    source.get_by_text("标记满员").click()
    expect(page.get_by_role("button",name="采用备选")).to_be_visible()
    assert source.locator("code").inner_text()==old
    page.locator(".review").scroll_into_view_if_needed()
    page.screenshot(path=str(proof/"desktop-preview.png"))
    page.get_by_text("采用备选",exact=True).click()
    assert source.locator("code").inner_text()!=old
    expect(bank.get_by_text("已锁定",exact=False)).to_be_visible()
    source.get_by_text("标记满员").click()
    expect(page.get_by_text("未找到可用备选")).to_be_visible()
    page.get_by_text("撤销本次满员标记").click()
    expect(page.get_by_text("撤销 "+old+" 满员记录")).to_be_visible()
    with page.expect_download() as event:
        page.get_by_text("下载离线清单",exact=False).click()
    assert old not in Path(event.value.path()).read_text(encoding="utf-8-sig")
    page.route("**/api/solve",lambda route:route.abort())
    page.get_by_role("button",name="应用条件并生成课表").click()
    expect(page.get_by_text("请求失败",exact=False)).to_be_visible()
    expect(source).to_be_visible()
    mobile=browser.new_page(viewport={"width":390,"height":844})
    mobile.goto("http://127.0.0.1:8765/")
    expect(mobile.locator(".daily-list")).to_be_visible()
    mobile.locator(".mobile-day select").select_option("3")
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
    mobile.screenshot(path=str(proof/"mobile.png"))
    browser.close()
print("PASS: desktop, mobile, preview, adoption, undo, request failure and offline export")
