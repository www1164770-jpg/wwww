const { Builder, Browser } = require("selenium-webdriver");
const assert = require("node:assert/strict");

describe("我的第一个 Selenium 自动化测试", function () {

  // 原来是 20000，现在改成 60000
  this.timeout(60000);

  let driver;

  beforeEach(async function () {
    driver = await new Builder()
      .forBrowser(Browser.CHROME)
      .build();
  });

  afterEach(async function () {
    if (driver) {
      await driver.quit();
    }
  });

  it("应该能够正确打开 Example 网站", async function () {

    await driver.get("https://example.com");

    const title = await driver.getTitle();

    assert.equal(title, "Example Domain");
  });

});