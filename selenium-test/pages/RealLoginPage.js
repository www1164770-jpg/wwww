const {
    By,
    until
} = require("selenium-webdriver");


class RealLoginPage {

    constructor(driver) {

        this.driver = driver;

        // ==============================
        // 知航屿真实登录地址
        // ==============================

        this.url =
            "http://127.0.0.1:5173/login";


        // ==============================
        // 页面元素
        // ==============================

        this.usernameInput =
            By.css(
                'input[placeholder="请输入邮箱或用户名"]'
            );


        this.passwordInput =
            By.css(
                'input[placeholder="请输入密码"]'
            );


        this.loginButton =
            By.xpath(
                '//button[contains(normalize-space(.), "登录")]'
            );


        this.loginError =
            By.xpath(
                '//*[normalize-space(.)="账号或密码错误"]'
            );

    }


    // ==================================================
    // 获取真正显示在页面上的元素
    // ==================================================

    async getVisibleElement(
        locator,
        timeout = 10000
    ) {

        return await this.driver.wait(

            async () => {

                const elements =
                    await this.driver.findElements(
                        locator
                    );


                for (const element of elements) {

                    try {

                        if (
                            await element.isDisplayed()
                        ) {
                            return element;
                        }

                    } catch (error) {
                        // 忽略失效元素
                    }

                }


                return false;

            },

            timeout,

            "没有找到可见元素"

        );

    }


    // ==============================
    // 打开登录页面
    // ==============================

    async open() {

        await this.driver.get(
            this.url
        );


        await this.driver.wait(
            until.urlContains(
                "/login"
            ),
            10000
        );


        await this.getVisibleElement(
            this.usernameInput
        );

    }


    // ==============================
    // 用户名框是否可见
    // ==============================

    async isUsernameVisible() {

        try {

            const element =
                await this.getVisibleElement(
                    this.usernameInput
                );

            return await element.isDisplayed();

        } catch (error) {

            return false;
        }

    }


    // ==============================
    // 密码框是否可见
    // ==============================

    async isPasswordVisible() {

        try {

            const element =
                await this.getVisibleElement(
                    this.passwordInput
                );

            return await element.isDisplayed();

        } catch (error) {

            return false;
        }

    }


    // ==============================
    // 登录按钮是否可见
    // ==============================

    async isLoginButtonVisible() {

        try {

            const element =
                await this.getVisibleElement(
                    this.loginButton
                );

            return await element.isDisplayed();

        } catch (error) {

            return false;
        }

    }


    // ==============================
    // 输入用户名
    // ==============================

    async enterUsername(username) {

        const input =
            await this.getVisibleElement(
                this.usernameInput
            );


        await input.clear();


        if (username) {

            await input.sendKeys(
                username
            );
        }

    }


    // ==============================
    // 输入密码
    // ==============================

    async enterPassword(password) {

        const input =
            await this.getVisibleElement(
                this.passwordInput
            );


        await input.clear();


        if (password) {

            await input.sendKeys(
                password
            );
        }

    }


    // ==============================
    // 点击登录
    // ==============================

    async clickLogin() {

        const button =
            await this.getVisibleElement(
                this.loginButton
            );


        await this.driver.wait(
            until.elementIsEnabled(
                button
            ),
            10000
        );


        await button.click();

    }


    // ==============================
    // 完整登录操作
    // ==============================

    async login(
        username,
        password
    ) {

        await this.enterUsername(
            username
        );


        await this.enterPassword(
            password
        );


        await this.clickLogin();

    }


    // ==============================
    // 获取账号密码错误提示
    // ==============================

    async getLoginErrorText() {

        const element =
            await this.getVisibleElement(
                this.loginError,
                10000
            );


        return await element.getText();

    }


    // ==================================================
    // 获取用户名输入框 HTML5 校验状态
    // ==================================================

    async getUsernameValidation() {

        const input =
            await this.getVisibleElement(
                this.usernameInput
            );


        return await this.driver.executeScript(
            `
            return {
                valueMissing:
                    arguments[0].validity.valueMissing,

                valid:
                    arguments[0].validity.valid,

                validationMessage:
                    arguments[0].validationMessage,

                required:
                    arguments[0].required
            };
            `,
            input
        );

    }


    // ==================================================
    // 获取密码输入框 HTML5 校验状态
    // ==================================================

    async getPasswordValidation() {

        const input =
            await this.getVisibleElement(
                this.passwordInput
            );


        return await this.driver.executeScript(
            `
            return {
                valueMissing:
                    arguments[0].validity.valueMissing,

                valid:
                    arguments[0].validity.valid,

                validationMessage:
                    arguments[0].validationMessage,

                required:
                    arguments[0].required
            };
            `,
            input
        );

    }


    // ==============================
    // 获取当前 URL
    // ==============================

    async getCurrentUrl() {

        return await this.driver
            .getCurrentUrl();

    }

}


module.exports = RealLoginPage;