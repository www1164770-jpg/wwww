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

const RealLoginPage =
    require("../pages/RealLoginPage");

const SearchPage =
    require("../pages/SearchPage");


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


// ==================================================
// 知航屿真实搜索自动化测试
// ==================================================

describe(
    "知航屿真实站内搜索自动化测试",
    function () {

        this.timeout(60000);

        let driver;
        let loginPage;
        let searchPage;


        // ==================================================
        // 每个测试开始前
        // 登录真实账号
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


                searchPage =
                    new SearchPage(
                        driver
                    );


                // 登录
                await loginPage.open();


                await loginPage.login(
                    username,
                    password
                );


                // 等待离开登录页
                await driver.wait(

                    async () => {

                        const url =
                            await driver
                                .getCurrentUrl();


                        return !url.includes(
                            "/login"
                        );

                    },

                    10000,

                    "登录失败，无法继续搜索测试"

                );

            }
        );


        // ==================================================
        // 失败自动截图
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
                            "\n搜索测试失败，截图已保存："
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


        // ==================================================
        // 测试 1
        // 搜索 Python 后进入搜索页
        // ==================================================

        it(
            "搜索Python后应该进入搜索结果页",
            async function () {

                await searchPage.search(
                    "Python"
                );


                await searchPage
                    .waitForResults();


                const currentUrl =
                    await searchPage
                        .getCurrentUrl();


                assert.ok(
                    currentUrl.includes(
                        "/search"
                    )
                );


                assert.ok(
                    currentUrl.includes(
                        "q=Python"
                    )
                );

            }
        );


        // ==================================================
        // 测试 2
        // 搜索标题正确
        // ==================================================

        it(
            "搜索结果标题应该包含Python",
            async function () {

                await searchPage.search(
                    "Python"
                );


                await searchPage
                    .waitForResults();


                const title =
                    await searchPage
                        .getResultTitle();


                assert.ok(
                    title.includes(
                        "Python"
                    )
                );

            }
        );


        // ==================================================
        // 测试 3
        // 搜索框保留关键词
        // ==================================================

        it(
            "搜索完成后搜索框应该保留Python",
            async function () {

                await searchPage.search(
                    "Python"
                );


                await searchPage
                    .waitForResults();


                const value =
                    await searchPage
                        .getSearchInputValue();


                assert.equal(
                    value,
                    "Python"
                );

            }
        );


        // ==================================================
        // 测试 4
        // 有搜索结果
        // ==================================================

        it(
            "Python搜索应该返回相关网站",
            async function () {

                await searchPage.search(
                    "Python"
                );


                await searchPage
                    .waitForResults();


                const countText =
                    await searchPage
                        .getResultCountText();


                console.log(
                    "\n搜索结果数量：",
                    countText
                );


                const match =
                    countText.match(
                        /(\d+)/
                    );


                assert.ok(
                    match,
                    "没有识别到搜索结果数量"
                );


                const count =
                    Number(
                        match[1]
                    );


                assert.ok(
                    count > 0,
                    "Python 搜索没有返回结果"
                );

            }
        );


        // ==================================================
        // 测试 5
        // Python 文档
        // ==================================================

        it(
            "搜索结果应该包含Python文档",
            async function () {

                await searchPage.search(
                    "Python"
                );


                await searchPage
                    .waitForResults();


                const visible =
                    await searchPage
                        .isResourceVisible(
                            "Python 文档"
                        );


                assert.equal(
                    visible,
                    true
                );

            }
        );


        // ==================================================
        // 测试 6
        // Google Colab
        // ==================================================

        it(
            "搜索结果应该包含Google Colab",
            async function () {

                await searchPage.search(
                    "Python"
                );


                await searchPage
                    .waitForResults();


                const visible =
                    await searchPage
                        .isResourceVisible(
                            "Google Colab"
                        );


                assert.equal(
                    visible,
                    true
                );

            }
        );


        // ==================================================
        // 测试 7
        // FastAPI
        // ==================================================

        it(
            "搜索结果应该包含FastAPI",
            async function () {

                await searchPage.search(
                    "Python"
                );


                await searchPage
                    .waitForResults();


                const visible =
                    await searchPage
                        .isResourceVisible(
                            "FastAPI"
                        );


                assert.equal(
                    visible,
                    true
                );

            }
        );


        // ==================================================
        // 测试 8
        // 刷新搜索页
        // ==================================================

        it(
            "刷新搜索结果页后结果仍然应该存在",
            async function () {

                await searchPage.search(
                    "Python"
                );


                await searchPage
                    .waitForResults();


                await searchPage.refresh();


                const title =
                    await searchPage
                        .getResultTitle();


                assert.ok(
                    title.includes(
                        "Python"
                    )
                );


                const currentUrl =
                    await searchPage
                        .getCurrentUrl();


                assert.ok(
                    currentUrl.includes(
                        "q=Python"
                    )
                );

            }
        );

    }
);