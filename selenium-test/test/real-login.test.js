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


// ==================================================
// 截图保存目录
// ==================================================

const screenshotsDir =
    path.resolve(
        __dirname,
        "../screenshots"
    );


if (!fs.existsSync(screenshotsDir)) {

    fs.mkdirSync(
        screenshotsDir,
        {
            recursive: true
        }
    );
}


// ==================================================
// 知航屿真实登录功能自动化测试
// ==================================================

describe(
    "知航屿真实登录功能测试",
    function () {

        // Selenium 启动和真实接口请求可能需要时间
        this.timeout(60000);

        let driver;
        let loginPage;


        // ==================================================
        // 每个测试开始前
        // ==================================================

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


        // ==================================================
        // 每个测试结束后
        // 如果失败则自动截图
        // ==================================================

        afterEach(
            async function () {

                try {

                    if (
                        driver &&
                        this.currentTest &&
                        this.currentTest.state === "failed"
                    ) {

                        const image =
                            await driver.takeScreenshot();


                        const testName =
                            this.currentTest.title.replace(
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

                } catch (error) {

                    console.log(
                        "保存失败截图时发生错误：",
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
        // 错误账号 + 错误密码
        // ==================================================

        it(
            "错误账号密码应该提示账号或密码错误",
            async function () {

                await loginPage.login(
                    "test_wrong_user",
                    "wrong_password_123"
                );


                const errorText =
                    await loginPage
                        .getLoginErrorText();


                assert.equal(
                    errorText,
                    "账号或密码错误"
                );


                const currentUrl =
                    await loginPage
                        .getCurrentUrl();


                assert.ok(
                    currentUrl.includes(
                        "/login"
                    )
                );

            }
        );


        // ==================================================
        // 测试 2
        // 用户名为空
        // ==================================================

        it(
            "用户名为空时应该触发浏览器必填校验",
            async function () {

                await loginPage.login(
                    "",
                    "123456789"
                );


                const validation =
                    await loginPage
                        .getUsernameValidation();


                // username 必须是 required
                assert.equal(
                    validation.required,
                    true
                );


                // 当前字段为空
                assert.equal(
                    validation.valueMissing,
                    true
                );


                // 应该属于无效状态
                assert.equal(
                    validation.valid,
                    false
                );


                // 浏览器应该产生提示
                assert.ok(
                    validation.validationMessage.length > 0
                );


                // 页面不能跳走
                const currentUrl =
                    await loginPage
                        .getCurrentUrl();


                assert.ok(
                    currentUrl.includes(
                        "/login"
                    )
                );

            }
        );


        // ==================================================
        // 测试 3
        // 密码为空
        // ==================================================

        it(
            "密码为空时应该触发浏览器必填校验",
            async function () {

                await loginPage.login(
                    "test_wrong_user",
                    ""
                );


                const validation =
                    await loginPage
                        .getPasswordValidation();


                assert.equal(
                    validation.required,
                    true
                );


                assert.equal(
                    validation.valueMissing,
                    true
                );


                assert.equal(
                    validation.valid,
                    false
                );


                assert.ok(
                    validation.validationMessage.length > 0
                );


                const currentUrl =
                    await loginPage
                        .getCurrentUrl();


                assert.ok(
                    currentUrl.includes(
                        "/login"
                    )
                );

            }
        );


        // ==================================================
        // 测试 4
        // 用户名和密码都为空
        // ==================================================

        it(
            "用户名和密码都为空时应该阻止提交",
            async function () {

                await loginPage.login(
                    "",
                    ""
                );


                const usernameValidation =
                    await loginPage
                        .getUsernameValidation();


                const passwordValidation =
                    await loginPage
                        .getPasswordValidation();


                assert.equal(
                    usernameValidation.valueMissing,
                    true
                );


                assert.equal(
                    passwordValidation.valueMissing,
                    true
                );


                assert.equal(
                    usernameValidation.valid,
                    false
                );


                assert.equal(
                    passwordValidation.valid,
                    false
                );


                const currentUrl =
                    await loginPage
                        .getCurrentUrl();


                assert.ok(
                    currentUrl.includes(
                        "/login"
                    )
                );

            }
        );


        // ==================================================
        // 测试 5
        // 正确账号 + 正确密码
        // 从 Windows 环境变量读取
        // ==================================================

        it(
            "正确账号密码应该登录成功",
            async function () {

                const username =
                    process.env.TEST_USERNAME;


                const password =
                    process.env.TEST_PASSWORD;


                // 确保环境变量已经设置
                assert.ok(
                    username,
                    "未设置 TEST_USERNAME 环境变量"
                );


                assert.ok(
                    password,
                    "未设置 TEST_PASSWORD 环境变量"
                );


                // 进行真实登录
                await loginPage.login(
                    username,
                    password
                );


                // 最多等待 10 秒
                // 登录成功以后应该离开 /login
                await driver.wait(

                    async () => {

                        const currentUrl =
                            await driver
                                .getCurrentUrl();


                        return !currentUrl.includes(
                            "/login"
                        );

                    },

                    10000,

                    "登录后仍然停留在 /login 页面"

                );


                const currentUrl =
                    await driver
                        .getCurrentUrl();


                // 最终确认 URL 已离开登录页
                assert.equal(
                    currentUrl.includes(
                        "/login"
                    ),
                    false
                );


                console.log(
                    "\n登录成功，当前页面：",
                    currentUrl
                );

            }
        );

    }
);