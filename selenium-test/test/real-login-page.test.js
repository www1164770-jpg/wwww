const {
    Builder,
    Browser
} = require("selenium-webdriver");

const assert =
    require("node:assert/strict");

const RealLoginPage =
    require("../pages/RealLoginPage");


describe(
    "知航屿真实登录页面自动化测试",
    function () {

        this.timeout(60000);

        let driver;
        let loginPage;


        // ==============================
        // 每个测试之前启动 Chrome
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
                    new RealLoginPage(
                        driver
                    );


                await loginPage.open();
            }
        );


        // ==============================
        // 测试结束后关闭 Chrome
        // ==============================

        afterEach(
            async function () {

                if (driver) {

                    await driver.quit();

                    driver = null;
                }
            }
        );


        // ==============================
        // 测试 1
        // ==============================

        it(
            "应该能够正常打开知航屿登录页面",
            async function () {

                const currentUrl =
                    await driver
                        .getCurrentUrl();

                assert.ok(
                    currentUrl.includes(
                        "/login"
                    )
                );
            }
        );


        // ==============================
        // 测试 2
        // ==============================

        it(
            "应该显示邮箱或用户名输入框",
            async function () {

                const visible =
                    await loginPage
                        .isUsernameVisible();

                assert.equal(
                    visible,
                    true
                );
            }
        );


        // ==============================
        // 测试 3
        // ==============================

        it(
            "应该显示密码输入框",
            async function () {

                const visible =
                    await loginPage
                        .isPasswordVisible();

                assert.equal(
                    visible,
                    true
                );
            }
        );


        // ==============================
        // 测试 4
        // ==============================

        it(
            "应该显示登录按钮",
            async function () {

                const visible =
                    await loginPage
                        .isLoginButtonVisible();

                assert.equal(
                    visible,
                    true
                );
            }
        );

    }
);