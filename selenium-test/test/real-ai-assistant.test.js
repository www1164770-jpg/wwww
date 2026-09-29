const {
    Builder,
    Browser,
    By
} = require("selenium-webdriver");

const assert =
    require("node:assert/strict");

const fs =
    require("node:fs");

const path =
    require("node:path");


const RealLoginPage =
    require("../pages/RealLoginPage");

const AIAssistantPage =
    require("../pages/AIAssistantPage");


// ==================================================
// 截图保存目录
// ==================================================

const screenshotsDir =
    path.resolve(
        __dirname,
        "../screenshots"
    );


if (
    !fs.existsSync(
        screenshotsDir
    )
) {

    fs.mkdirSync(
        screenshotsDir,
        {
            recursive: true
        }
    );

}


// ==================================================
// AI 助手自动化测试
// ==================================================

describe(
    "知航屿真实AI助手自动化测试",
    function () {

        this.timeout(
            120000
        );


        let driver;

        let loginPage;

        let aiPage;


        // ==================================================
        // 每条测试开始前
        // ==================================================

        beforeEach(
            async function () {

                const username =
                    process.env.TEST_USERNAME;


                const password =
                    process.env.TEST_PASSWORD;


                assert.ok(
                    username,
                    "未设置 TEST_USERNAME"
                );


                assert.ok(
                    password,
                    "未设置 TEST_PASSWORD"
                );


                driver =
                    await new Builder()
                        .forBrowser(
                            Browser.CHROME
                        )
                        .build();


                loginPage =
                    new RealLoginPage(
                        driver
                    );


                aiPage =
                    new AIAssistantPage(
                        driver
                    );


                // ======================================
                // 登录
                // ======================================

                await loginPage.open();


                await loginPage.login(
                    username,
                    password
                );


                // ======================================
                // 等登录完成
                // ======================================

                await driver.wait(

                    async () => {

                        const url =
                            await driver
                                .getCurrentUrl();


                        return !url.includes(
                            "/login"
                        );

                    },

                    20000,

                    "登录失败，仍停留在登录页"

                );


                // ======================================
                // 等 AI助手 导航出现
                // ======================================

                await driver.wait(

                    async () => {

                        const elements =
                            await driver.findElements(
                                By.xpath(
                                    '//*[normalize-space(.)="AI助手"]'
                                )
                            );


                        for (const element of elements) {

                            try {

                                if (
                                    await element.isDisplayed()
                                ) {

                                    return true;
                                }

                            } catch (error) {

                                // 继续
                            }

                        }


                        return false;

                    },

                    20000,

                    "登录后没有看到 AI助手 导航"

                );


                await driver.sleep(
                    500
                );

            }
        );


        // ==================================================
        // 每条测试结束后
        // ==================================================

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
                            "\nAI助手测试失败，截图已保存："
                        );


                        console.log(
                            screenshotPath
                        );

                    }

                } finally {

                    if (driver) {

                        try {

                            await driver.quit();

                        } catch (error) {

                            // 忽略
                        }


                        driver =
                            null;
                    }

                }

            }
        );


        // ==================================================
        // 1. AI 助手能够展开
        // ==================================================

        it(
            "应该能够正常展开AI助手",
            async function () {

                await aiPage.open();


                assert.equal(
                    await aiPage.isOpen(),
                    true,
                    "AI助手没有成功展开"
                );

            }
        );


        // ==================================================
        // 2. 三个功能页签
        // ==================================================

        it(
            "展开后应该显示对话推荐写作三个功能",
            async function () {

                await aiPage.open();


                assert.equal(
                    await aiPage
                        .isChatTabVisible(),
                    true,
                    "没有看到对话功能"
                );


                assert.equal(
                    await aiPage
                        .isRecommendTabVisible(),
                    true,
                    "没有看到推荐功能"
                );


                assert.equal(
                    await aiPage
                        .isWriteTabVisible(),
                    true,
                    "没有看到写作功能"
                );

            }
        );


        // ==================================================
        // 3. 输入框
        // ==================================================

        it(
            "AI助手应该显示需求输入框",
            async function () {

                await aiPage.open();


                assert.equal(
                    await aiPage
                        .isInputVisible(),
                    true,
                    "AI助手输入框没有显示"
                );

            }
        );


        // ==================================================
        // 4. 可以输入文字
        // 不发送给真实 AI
        // ==================================================

        it(
            "应该能够在AI助手输入框中输入内容",
            async function () {

                await aiPage.open();


                const message =
                    "帮我推荐学习 Python 的网站";


                await aiPage.typeMessage(
                    message
                );


                const value =
                    await aiPage
                        .getInputValue();


                assert.equal(
                    value,
                    message,
                    "AI助手输入框内容不正确"
                );

            }
        );


        // ==================================================
        // 5. 关闭 AI 助手
        // ==================================================

        it(
            "应该能够关闭AI助手",
            async function () {

                await aiPage.open();


                assert.equal(
                    await aiPage.isOpen(),
                    true
                );


                await aiPage.closeByX();


                assert.equal(
                    await aiPage.isOpen(),
                    false,
                    "AI助手关闭失败"
                );

            }
        );


        // ==================================================
        // 6. 可以再次打开
        // ==================================================

        it(
            "关闭AI助手后应该能够再次打开",
            async function () {

                await aiPage.open();


                await aiPage.closeByX();


                assert.equal(
                    await aiPage.isOpen(),
                    false
                );


                await aiPage.open();


                assert.equal(
                    await aiPage.isOpen(),
                    true,
                    "AI助手第二次打开失败"
                );

            }
        );

    }
);