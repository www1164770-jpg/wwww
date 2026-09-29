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

const SearchPage =
    require("../pages/SearchPage");

const FavoritePage =
    require("../pages/FavoritePage");


// ==================================================
// 截图目录
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
// 收藏功能测试
// ==================================================

describe(
    "知航屿真实收藏功能自动化测试",
    function () {

        this.timeout(
            120000
        );


        let driver;

        let loginPage;

        let searchPage;

        let favoritePage;


        // ==================================================
        // 每个测试开始前
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


                favoritePage =
                    new FavoritePage(
                        driver
                    );


                // ------------------------------------------
                // 登录
                // ------------------------------------------

                await loginPage.open();


                await loginPage.login(
                    username,
                    password
                );


                // ------------------------------------------
                // 等登录完成
                // ------------------------------------------

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

                    "登录失败，仍停留在登录页面"

                );


                // ------------------------------------------
                // 等顶部收藏导航
                // ------------------------------------------

                await driver.wait(

                    async () => {

                        const elements =
                            await driver.findElements(
                                By.css(
                                    'a[href="/favorites"], a[href$="/favorites"]'
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

                    "登录成功后没有看到收藏导航"

                );


                await driver.sleep(
                    500
                );

            }
        );


        // ==================================================
        // 每个测试结束后
        // ==================================================

        afterEach(
            async function () {

                try {

                    if (
                        driver &&
                        this.currentTest &&
                        this.currentTest.state ===
                        "failed"
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
                            "\n收藏测试失败，截图已保存："
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
        // 测试 1
        // ==================================================

        it(
            "应该能够正常进入收藏页面",
            async function () {

                await favoritePage.open();


                const url =
                    await favoritePage
                        .getCurrentUrl();


                assert.ok(
                    url.includes(
                        "/favorites"
                    ),
                    `收藏页 URL 不正确：${url}`
                );


                const loaded =
                    await favoritePage
                        .isPageLoaded();


                assert.equal(
                    loaded,
                    true,
                    "收藏页面没有正常加载"
                );


                const empty =
                    await favoritePage
                        .isEmptyStateVisible();


                if (empty) {

                    console.log(
                        "\n收藏页面验证成功：当前收藏夹为空"
                    );

                } else {

                    console.log(
                        "\n收藏页面验证成功：当前存在收藏内容"
                    );

                }

            }
        );


        // ==================================================
        // 测试 2
        // ==================================================

        it(
            "应该能够收藏并取消收藏Python文档",
            async function () {

                const resourceName =
                    "Python 文档";


                // ==========================================
                // STEP 1
                // 进入收藏页
                // ==========================================

                await favoritePage.open();


                // ==========================================
                // STEP 2
                // 清理测试开始前的旧收藏
                // ==========================================

                const alreadyFavorite =
                    await favoritePage
                        .isResourceVisible(
                            resourceName
                        );


                if (alreadyFavorite) {

                    console.log(
                        "\n测试开始前 Python 文档已收藏，先清理旧状态..."
                    );


                    const cleaned =
                        await favoritePage
                            .cancelFavoriteFromFavoritesPage(
                                resourceName
                            );


                    assert.equal(
                        cleaned,
                        true,
                        "测试开始前的旧收藏状态清理失败"
                    );


                    console.log(
                        "旧收藏状态清理完成"
                    );

                } else {

                    console.log(
                        "\n测试开始前收藏夹为空或没有 Python 文档"
                    );

                }


                // ==========================================
                // STEP 3
                // 返回首页
                // ==========================================

                await driver.get(
                    "http://127.0.0.1:5173/"
                );


                // ==========================================
                // STEP 4
                // 等搜索框
                // ==========================================

                await driver.wait(

                    async () => {

                        const inputs =
                            await driver.findElements(
                                By.css(
                                    'input[placeholder*="搜索工具"]'
                                )
                            );


                        for (const input of inputs) {

                            try {

                                if (
                                    await input.isDisplayed()
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

                    "首页搜索框没有显示"

                );


                // ==========================================
                // STEP 5
                // 搜索 Python
                // ==========================================

                await searchPage.search(
                    "Python"
                );


                await searchPage
                    .waitForResults();


                // ==========================================
                // STEP 6
                // 验证 Python 文档出现
                // ==========================================

                const resultVisible =
                    await searchPage
                        .isResourceVisible(
                            resourceName
                        );


                assert.equal(
                    resultVisible,
                    true,
                    "搜索结果中没有找到 Python 文档"
                );


                // ==========================================
                // STEP 7
                // 点击收藏
                // ==========================================

                await favoritePage
                    .clickFavoriteToggleForResource(
                        resourceName
                    );


                // ==========================================
                // 捕获“已收藏”
                // ==========================================

                try {

                    await favoritePage
                        .waitForMessage(
                            "已收藏",
                            3000
                        );


                    console.log(
                        "\n已捕获“已收藏”提示"
                    );

                } catch (error) {

                    console.log(
                        "\n没有捕获 Toast，继续验证收藏页真实数据"
                    );

                }


                // ==========================================
                // STEP 8
                // 打开收藏页
                // ==========================================

                await favoritePage.open();


                // ==========================================
                // STEP 9
                // 验证 Python 文档存在
                // ==========================================

                await favoritePage
                    .waitForResourceState(
                        resourceName,
                        true,
                        15000
                    );


                assert.equal(
                    await favoritePage
                        .isResourceVisible(
                            resourceName
                        ),
                    true,
                    "收藏后 Python 文档没有出现在收藏页"
                );


                console.log(
                    "\nPython 文档收藏成功"
                );


                // ==========================================
                // STEP 10
                // 专门执行收藏页取消收藏
                // ==========================================

                const cancelSuccess =
                    await favoritePage
                        .cancelFavoriteFromFavoritesPage(
                            resourceName
                        );


                assert.equal(
                    cancelSuccess,
                    true,
                    "Python 文档取消收藏失败"
                );


                // ==========================================
                // STEP 11
                // 最终确认
                // ==========================================

                const stillVisible =
                    await favoritePage
                        .isResourceVisible(
                            resourceName
                        );


                assert.equal(
                    stillVisible,
                    false,
                    "取消收藏后 Python 文档仍然存在"
                );


                console.log(
                    "\nPython 文档取消收藏成功"
                );


                // 如果只有这一条收藏，
                // 页面应该恢复空收藏状态
                const empty =
                    await favoritePage
                        .isEmptyStateVisible();


                if (empty) {

                    console.log(
                        "收藏夹已恢复为空"
                    );

                }

            }
        );

    }
);