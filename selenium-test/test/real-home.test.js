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

const HomePage =
    require("../pages/HomePage");


// ==============================
// 截图保存目录
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
// 知航屿真实首页自动化测试
// ==================================================

describe(
    "知航屿真实首页自动化测试",
    function () {

        this.timeout(60000);

        let driver;
        let loginPage;
        let homePage;


        // ==================================================
        // 每个测试开始前
        // 先登录真实账号
        // ==================================================

        beforeEach(
            async function () {

                const username =
                    process.env.TEST_USERNAME;


                const password =
                    process.env.TEST_PASSWORD;


                assert.ok(
                    username,
                    "未设置 TEST_USERNAME 环境变量"
                );


                assert.ok(
                    password,
                    "未设置 TEST_PASSWORD 环境变量"
                );


                // 启动 Chrome
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


                homePage =
                    new HomePage(
                        driver
                    );


                // 打开真实登录页
                await loginPage.open();


                // 登录
                await loginPage.login(
                    username,
                    password
                );


                // 等待首页加载
                await homePage
                    .waitForLoaded();

            }
        );


        // ==================================================
        // 测试失败自动截图
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
                            "\n首页测试失败，截图已保存："
                        );


                        console.log(
                            screenshotPath
                        );

                    }

                } catch (error) {

                    console.log(
                        "截图保存失败：",
                        error.message
                    );

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
        // 登录后应该进入首页
        // ==================================================

        it(
            "登录成功后应该进入首页",
            async function () {

                const currentUrl =
                    await homePage
                        .getCurrentUrl();


                assert.equal(
                    currentUrl.includes(
                        "/login"
                    ),
                    false
                );


                console.log(
                    "\n当前首页地址：",
                    currentUrl
                );

            }
        );


        // ==================================================
        // 测试 2
        // 首页主标题
        // ==================================================

        it(
            "首页应该显示职业推荐主标题",
            async function () {

                const visible =
                    await homePage
                        .isMainTitleVisible();


                assert.equal(
                    visible,
                    true
                );

            }
        );


        // ==================================================
        // 测试 3
        // 推荐标题
        // ==================================================

        it(
            "首页应该显示推荐资源标题",
            async function () {

                const visible =
                    await homePage
                        .isRecommendTitleVisible();


                assert.equal(
                    visible,
                    true
                );

            }
        );


        // ==================================================
        // 测试 4
        // 首页导航
        // ==================================================

        it(
            "顶部应该显示首页导航",
            async function () {

                const visible =
                    await homePage
                        .isHomeNavVisible();


                assert.equal(
                    visible,
                    true
                );

            }
        );


        // ==================================================
        // 测试 5
        // 收藏导航
        // ==================================================

        it(
            "顶部应该显示收藏导航",
            async function () {

                const visible =
                    await homePage
                        .isFavoriteNavVisible();


                assert.equal(
                    visible,
                    true
                );

            }
        );


        // ==================================================
        // 测试 6
        // AI助手
        // ==================================================

        it(
            "顶部应该显示AI助手入口",
            async function () {

                const visible =
                    await homePage
                        .isAINavVisible();


                assert.equal(
                    visible,
                    true
                );

            }
        );


        // ==================================================
        // 测试 7
        // 搜索框
        // ==================================================

        it(
            "首页应该显示站内搜索框",
            async function () {

                const visible =
                    await homePage
                        .isSearchInputVisible();


                assert.equal(
                    visible,
                    true
                );

            }
        );


        // ==================================================
        // 测试 8
        // 站内搜索选择器
        // ==================================================

        it(
            "首页应该显示站内搜索类型",
            async function () {

                const visible =
                    await homePage
                        .isSearchTypeVisible();


                assert.equal(
                    visible,
                    true
                );

            }
        );


        // ==================================================
        // 测试 9
        // 刷新后登录状态保持
        // ==================================================

        it(
            "刷新首页后应该保持登录状态",
            async function () {

                await homePage.refresh();


                const currentUrl =
                    await homePage
                        .getCurrentUrl();


                // 刷新后不能返回登录页
                assert.equal(
                    currentUrl.includes(
                        "/login"
                    ),
                    false
                );


                // 首页标题仍然应该存在
                const titleVisible =
                    await homePage
                        .isMainTitleVisible();


                assert.equal(
                    titleVisible,
                    true
                );

            }
        );

    }
);