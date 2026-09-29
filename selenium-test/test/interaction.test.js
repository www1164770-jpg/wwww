const {
    Builder,
    Browser
} = require("selenium-webdriver");

const assert =
    require("node:assert/strict");

const fs =
    require("node:fs");

const path =
    require("node:path");

const LoginPage =
    require("../pages/LoginPage");


// ==============================
// 截图目录
// ==============================

const screenshotsDir =
    path.resolve(
        __dirname,
        "../screenshots"
    );


if (!fs.existsSync(
    screenshotsDir
)) {

    fs.mkdirSync(
        screenshotsDir,
        {
            recursive: true
        }
    );
}


// ==============================
// 登录功能自动化测试
// ==============================

describe(
    "登录功能自动化测试",
    function () {

        this.timeout(60000);

        let driver;
        let loginPage;


        // ==============================
        // 每个测试前启动 Chrome
        // ==============================

        beforeEach(
            async function () {

                driver =
                    await new Builder()
                        .forBrowser(
                            Browser.CHROME
                        )
                        .build();


                loginPage =
                    new LoginPage(
                        driver
                    );


                await loginPage.open();
            }
        );


        // ==============================
        // 每个测试结束后
        // 失败则截图
        // ==============================

        afterEach(
            async function () {

                try {

                    if (
                        driver &&
                        this.currentTest &&
                        this.currentTest.state
                            === "failed"
                    ) {

                        const image =
                            await driver
                                .takeScreenshot();


                        const testName =
                            this.currentTest
                                .title
                                .replace(
                                    /[\\/:*?"<>|]/g,
                                    "_"
                                );


                        const screenshotPath =
                            path.join(
                                screenshotsDir,
                                `${Date.now()}-${testName}.png`
                            );


                        fs.writeFileSync(
                            screenshotPath,
                            image,
                            "base64"
                        );


                        console.log(
                            "\n测试失败，截图已保存："
                        );

                        console.log(
                            screenshotPath
                        );
                    }

                } finally {

                    if (driver) {

                        await driver.quit();

                        driver = null;
                    }
                }
            }
        );


        // ==============================
        // 测试 1
        // ==============================

        it(
            "输入正确账号密码后应该登录成功",
            async function () {

                await loginPage.login(
                    "admin",
                    "123456"
                );

                const result =
                    await loginPage
                        .getResult();

                assert.equal(
                    result,
                    "登录成功"
                );
            }
        );


        // ==============================
        // 测试 2
        // ==============================

        it(
            "输入错误密码后应该登录失败",
            async function () {

                await loginPage.login(
                    "admin",
                    "000000"
                );

                const result =
                    await loginPage
                        .getResult();

                assert.equal(
                    result,
                    "用户名或密码错误"
                );
            }
        );


        // ==============================
        // 测试 3
        // ==============================

        it(
            "输入错误用户名后应该登录失败",
            async function () {

                await loginPage.login(
                    "wronguser",
                    "123456"
                );

                const result =
                    await loginPage
                        .getResult();

                assert.equal(
                    result,
                    "用户名或密码错误"
                );
            }
        );


        // ==============================
        // 测试 4
        // ==============================

        it(
            "用户名为空时应该登录失败",
            async function () {

                await loginPage.login(
                    "",
                    "123456"
                );

                const result =
                    await loginPage
                        .getResult();

                assert.equal(
                    result,
                    "用户名或密码错误"
                );
            }
        );


        // ==============================
        // 测试 5
        // ==============================

        it(
            "密码为空时应该登录失败",
            async function () {

                await loginPage.login(
                    "admin",
                    ""
                );

                const result =
                    await loginPage
                        .getResult();

                assert.equal(
                    result,
                    "用户名或密码错误"
                );
            }
        );


        // ==============================
        // 测试 6
        // ==============================

        it(
            "用户名和密码都为空时应该登录失败",
            async function () {

                await loginPage.login(
                    "",
                    ""
                );

                const result =
                    await loginPage
                        .getResult();

                assert.equal(
                    result,
                    "用户名或密码错误"
                );
            }
        );

    }
);