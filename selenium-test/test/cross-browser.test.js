const {
    Builder,
    Browser,
    By,
    until
} = require("selenium-webdriver");

const assert = require("node:assert/strict");
const path = require("node:path");
const { pathToFileURL } = require("node:url");


// 要测试的浏览器
const browsers = [
    Browser.CHROME,
    Browser.FIREFOX
];


describe("跨浏览器自动化测试", function () {

    // Firefox 第一次运行时可能需要下载驱动
    this.timeout(120000);


    // 依次测试 Chrome 和 Firefox
    for (const browser of browsers) {

        describe(`${browser} 浏览器测试`, function () {

            let driver;


            // 每个测试开始之前启动对应浏览器
            beforeEach(async function () {

                driver = await new Builder()
                    .forBrowser(browser)
                    .build();

            });


            // 每个测试结束后关闭浏览器
            afterEach(async function () {

                if (driver) {

                    await driver.quit();

                    driver = null;
                }

            });


            it(
                `应该能够在 ${browser} 中完成登录`,
                async function () {

                    // demo.html 路径
                    const filePath = path.resolve(
                        __dirname,
                        "../demo.html"
                    );

                    const fileUrl =
                        pathToFileURL(filePath).href;


                    // 打开登录页面
                    await driver.get(fileUrl);


                    // 等待用户名输入框出现
                    const username =
                        await driver.wait(
                            until.elementLocated(
                                By.id("username")
                            ),
                            10000
                        );


                    // 输入用户名
                    await username.sendKeys(
                        "admin"
                    );


                    // 输入密码
                    await driver
                        .findElement(
                            By.id("password")
                        )
                        .sendKeys(
                            "123456"
                        );


                    // 点击登录按钮
                    await driver
                        .findElement(
                            By.id("loginBtn")
                        )
                        .click();


                    // 找到登录结果
                    const resultElement =
                        await driver.wait(
                            until.elementLocated(
                                By.id("result")
                            ),
                            10000
                        );


                    // 获取登录结果
                    const result =
                        await resultElement.getText();


                    // 判断是否登录成功
                    assert.equal(
                        result,
                        "登录成功"
                    );

                }
            );

        });

    }

});